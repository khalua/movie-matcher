import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from models import db, User, CircleMember, Invitation, Circle, PendingInvite
from sqlalchemy import func
from datetime import datetime, timedelta
import secrets
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new user with email"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    display_name = data.get('display_name')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # Use email prefix as display name if not provided
    if not display_name:
        display_name = email.split('@')[0]

    # Check if first user (becomes site admin)
    is_first_user = User.query.count() == 0

    # Case-insensitive check
    if User.query.filter(func.lower(User.email) == email.lower()).first():
        return jsonify({'error': 'Email already registered'}), 400

    user = User(
        email=email.lower(),
        display_name=display_name,
        is_site_admin=is_first_user
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # Get user ID before committing

    # Check for pending invites and add user to those circles
    pending_invites = PendingInvite.query.filter(
        func.lower(PendingInvite.email) == email.lower()
    ).all()

    circles_joined = []
    for invite in pending_invites:
        member = CircleMember(
            circle_id=invite.circle_id,
            user_id=user.id,
            role='member'
        )
        db.session.add(member)
        circles_joined.append({
            'id': invite.circle.id,
            'name': invite.circle.name,
            'role': 'member'
        })
        db.session.delete(invite)  # Remove pending invite

    db.session.commit()

    # Generate token and return with circles if any
    access_token = create_access_token(identity=user.email)

    return jsonify({
        'message': 'User created successfully',
        'access_token': access_token,
        'user': user.to_dict(),
        'circles': circles_joined,
        'is_site_admin': is_first_user
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login with email and return circles"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter(func.lower(User.email) == email.lower()).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=user.email)

    # Get user's circles
    circles = []
    for membership in user.circles:
        circle = membership.circle
        if circle.is_active:
            circles.append({
                'id': circle.id,
                'name': circle.name,
                'role': membership.role
            })

    return jsonify({
        'access_token': access_token,
        'user': user.to_dict(),
        'circles': circles
    }), 200


@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get current user's profile"""
    from flask_jwt_extended import jwt_required, get_jwt_identity

    @jwt_required()
    def _get_profile():
        email = get_jwt_identity()
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify(user.to_dict()), 200

    return _get_profile()


@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    """Update current user's profile"""
    from flask_jwt_extended import jwt_required, get_jwt_identity

    @jwt_required()
    def _update_profile():
        email = get_jwt_identity()
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        if 'display_name' in data:
            user.display_name = data['display_name']
            db.session.commit()

        return jsonify(user.to_dict()), 200

    return _update_profile()


@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change current user's password (or set initial password for OAuth users)"""
    from flask_jwt_extended import jwt_required, get_jwt_identity

    @jwt_required()
    def _change_password():
        email = get_jwt_identity()
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not new_password:
            return jsonify({'error': 'New password required'}), 400

        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400

        # OAuth-only users can set initial password without current_password
        if not user.password_hash:
            user.set_password(new_password)
            db.session.commit()
            return jsonify({'message': 'Password set successfully'}), 200

        # Regular users need current password
        if not current_password:
            return jsonify({'error': 'Current password required'}), 400

        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 403

        user.set_password(new_password)
        db.session.commit()

        return jsonify({'message': 'Password changed successfully'}), 200

    return _change_password()


@auth_bp.route('/change-email', methods=['POST'])
def change_email():
    """Change current user's email address"""
    from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

    @jwt_required()
    def _change_email():
        current_email = get_jwt_identity()
        user = User.query.filter_by(email=current_email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        new_email = data.get('new_email')
        password = data.get('password')

        if not new_email or not password:
            return jsonify({'error': 'New email and password required'}), 400

        # Verify password
        if not user.check_password(password):
            return jsonify({'error': 'Password is incorrect'}), 403

        # Normalize email
        new_email = new_email.lower().strip()

        # Check if same as current
        if new_email == user.email:
            return jsonify({'error': 'New email is the same as current email'}), 400

        # Check if email already in use
        existing = User.query.filter(func.lower(User.email) == new_email).first()
        if existing:
            return jsonify({'error': 'Email already in use'}), 400

        # Update email
        user.email = new_email
        db.session.commit()

        # Generate new token with updated email
        new_token = create_access_token(identity=user.email)

        return jsonify({
            'message': 'Email changed successfully',
            'access_token': new_token,
            'user': user.to_dict()
        }), 200

    return _change_email()


@auth_bp.route('/invitations/redeem', methods=['POST'])
def redeem_invitation():
    """Redeem invitation code (creates user if new, adds to circle)"""
    data = request.get_json()
    code = data.get('code')
    email = data.get('email')
    password = data.get('password')
    display_name = data.get('display_name')

    if not code:
        return jsonify({'error': 'Invitation code required'}), 400

    invitation = Invitation.query.filter_by(code=code, is_active=True).first()

    if not invitation:
        return jsonify({'error': 'Invalid invitation code'}), 404

    if invitation.expires_at < datetime.utcnow():
        return jsonify({'error': 'Invitation expired'}), 400

    # For existing users, just add to circle
    existing_user = None
    if email:
        existing_user = User.query.filter(func.lower(User.email) == email.lower()).first()

    if existing_user:
        # Existing user joining circle
        user = existing_user
        # Verify password if provided
        if password and not user.check_password(password):
            return jsonify({'error': 'Invalid password'}), 401
    else:
        # New user signing up via invitation
        if not email or not password:
            return jsonify({'error': 'Email and password required for new users'}), 400

        if not display_name:
            display_name = email.split('@')[0]

        user = User(
            email=email.lower(),
            display_name=display_name
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

    # Add to circle if not already a member
    existing_member = CircleMember.query.filter_by(
        circle_id=invitation.circle_id,
        user_id=user.id
    ).first()

    if not existing_member:
        member = CircleMember(
            circle_id=invitation.circle_id,
            user_id=user.id,
            role='member'
        )
        db.session.add(member)

    # Decrement uses if limited
    if invitation.uses_remaining is not None:
        invitation.uses_remaining -= 1
        if invitation.uses_remaining <= 0:
            invitation.is_active = False

    db.session.commit()

    access_token = create_access_token(identity=user.email)

    return jsonify({
        'access_token': access_token,
        'user': user.to_dict(),
        'circle': invitation.circle.to_dict(user.id)
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset email"""
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email required'}), 400

    # Find user (case-insensitive)
    user = User.query.filter(func.lower(User.email) == email.lower()).first()

    # Always return success to prevent email enumeration
    if not user:
        return jsonify({'message': 'If an account exists with that email, a reset link has been sent.'}), 200

    # Generate secure token
    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    # Send email
    from email_service import send_password_reset_email
    send_password_reset_email(user.email, token, user.display_name)

    return jsonify({'message': 'If an account exists with that email, a reset link has been sent.'}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token"""
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({'error': 'Token and new password required'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Find user by token
    user = User.query.filter_by(password_reset_token=token).first()

    if not user:
        return jsonify({'error': 'Invalid or expired reset token'}), 400

    # Check if token is expired
    if user.password_reset_expires < datetime.utcnow():
        # Clear expired token
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()
        return jsonify({'error': 'Reset token has expired. Please request a new one.'}), 400

    # Update password and clear token
    user.set_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.session.commit()

    return jsonify({'message': 'Password has been reset successfully. You can now log in.'}), 200


@auth_bp.route('/verify-reset-token/<token>', methods=['GET'])
def verify_reset_token(token):
    """Verify if a reset token is valid (for frontend validation)"""
    user = User.query.filter_by(password_reset_token=token).first()

    if not user:
        return jsonify({'valid': False, 'error': 'Invalid reset token'}), 400

    if user.password_reset_expires < datetime.utcnow():
        return jsonify({'valid': False, 'error': 'Reset token has expired'}), 400

    return jsonify({'valid': True}), 200


@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Authenticate with Google OAuth token"""
    data = request.get_json()
    token = data.get('credential')

    if not token:
        return jsonify({'error': 'No credential provided'}), 400

    try:
        # Verify the Google token
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            os.environ.get('GOOGLE_CLIENT_ID')
        )

        email = idinfo['email'].lower()
        name = idinfo.get('name', '')
        is_new_user = False

        # Find or create user
        user = User.query.filter(func.lower(User.email) == email).first()

        if not user:
            is_new_user = True
            # Check if first user (becomes site admin)
            is_first_user = User.query.count() == 0

            # Create new user (no password for OAuth users)
            user = User(
                email=email,
                display_name=name if name else email.split('@')[0],
                is_site_admin=is_first_user
            )
            db.session.add(user)
            db.session.flush()  # Get user ID before checking pending invites

            # Check for pending invites and add user to those circles
            pending_invites = PendingInvite.query.filter(
                func.lower(PendingInvite.email) == email
            ).all()

            for invite in pending_invites:
                member = CircleMember(
                    circle_id=invite.circle_id,
                    user_id=user.id,
                    role='member'
                )
                db.session.add(member)
                db.session.delete(invite)  # Remove pending invite

            db.session.commit()

        # Generate JWT token
        access_token = create_access_token(identity=user.email)

        # Get user's circles (only active ones)
        circles = []
        for membership in user.circles:
            circle = membership.circle
            if circle.is_active:
                circles.append({
                    'id': circle.id,
                    'name': circle.name,
                    'role': membership.role
                })

        return jsonify({
            'access_token': access_token,
            'user': user.to_dict(),
            'circles': circles,
            'is_new_user': is_new_user
        }), 200

    except ValueError as e:
        return jsonify({'error': 'Invalid token'}), 401
