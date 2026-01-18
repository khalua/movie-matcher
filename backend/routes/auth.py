from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from models import db, User, CircleMember, Invitation, Circle
from sqlalchemy import func
from datetime import datetime

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
    db.session.commit()

    return jsonify({
        'message': 'User created successfully',
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
