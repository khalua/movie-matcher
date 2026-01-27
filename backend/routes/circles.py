from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Circle, CircleMember, Invitation, CircleMovie, UserSwipe, PendingInvite
from auth import circle_required, circle_admin_required
from sqlalchemy import func
from datetime import datetime, timedelta
import secrets
import os

circles_bp = Blueprint('circles', __name__)


@circles_bp.route('', methods=['GET'])
@jwt_required()
def get_user_circles():
    """List all circles user is member of. Site admins see all circles."""
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    circles = []

    # Site admins can see all circles
    if user.is_site_admin:
        all_circles = Circle.query.filter_by(is_active=True).all()
        for circle in all_circles:
            # Check if user is a member of this circle
            membership = CircleMember.query.filter_by(
                circle_id=circle.id,
                user_id=user.id
            ).first()

            circle_data = circle.to_dict(user.id)
            circle_data['unseen_count'] = get_unseen_count(user.id, circle.id)
            # Mark circles where admin is not a member
            circle_data['is_member'] = membership is not None
            circle_data['role'] = membership.role if membership else 'site_admin'
            circles.append(circle_data)
    else:
        # Regular users only see their circles
        for membership in user.circles:
            circle = membership.circle
            if not circle.is_active:
                continue

            # Count unseen movies
            unseen_count = get_unseen_count(user.id, circle.id)

            circle_data = circle.to_dict(user.id)
            circle_data['unseen_count'] = unseen_count
            circles.append(circle_data)

    return jsonify(circles), 200


@circles_bp.route('', methods=['POST'])
@jwt_required()
def create_circle():
    """Create new circle and make creator admin"""
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'error': 'Circle name required'}), 400

    # Create circle
    circle = Circle(
        name=name,
        created_by_id=user.id
    )
    db.session.add(circle)
    db.session.flush()

    # Add creator as admin
    member = CircleMember(
        circle_id=circle.id,
        user_id=user.id,
        role='admin'
    )
    db.session.add(member)

    # NOTE: No longer auto-seeding with top movies.
    # Users now choose their own movie packs via the PackSelector UI.
    # To add the classic top 100 movies, users can select the "Top 100 Classics" pack.

    db.session.commit()

    return jsonify(circle.to_dict(user.id)), 201


@circles_bp.route('/<int:circle_id>', methods=['GET'])
@jwt_required()
@circle_required
def get_circle(circle, user, member, circle_id):
    """Get circle details"""
    return jsonify(circle.to_dict(user.id)), 200


@circles_bp.route('/<int:circle_id>', methods=['PUT'])
@jwt_required()
@circle_admin_required
def update_circle(circle, user, member, circle_id):
    """Update circle (admin only)"""
    data = request.get_json()
    name = data.get('name')

    if name:
        circle.name = name
        db.session.commit()

    return jsonify(circle.to_dict(user.id)), 200


@circles_bp.route('/<int:circle_id>', methods=['DELETE'])
@jwt_required()
@circle_admin_required
def delete_circle(circle, user, member, circle_id):
    """Delete circle (admin only)"""
    circle.is_active = False
    db.session.commit()

    return jsonify({'message': 'Circle deleted successfully'}), 200


@circles_bp.route('/<int:circle_id>/members', methods=['GET'])
@jwt_required()
@circle_required
def get_circle_members(circle, user, member, circle_id):
    """Get all members of a circle"""
    members = []
    for membership in circle.members:
        member_user = membership.user
        members.append({
            'id': member_user.id,
            'email': member_user.email,
            'display_name': member_user.display_name,
            'role': membership.role,
            'joined_at': membership.joined_at.isoformat()
        })

    return jsonify(members), 200


@circles_bp.route('/<int:circle_id>/members/<int:user_id>', methods=['DELETE'])
@jwt_required()
@circle_admin_required
def remove_member(circle, user, member, circle_id, user_id):
    """Remove member from circle (admin only)"""
    if user_id == user.id:
        return jsonify({'error': 'Cannot remove yourself'}), 400

    member_to_remove = CircleMember.query.filter_by(
        circle_id=circle_id,
        user_id=user_id
    ).first()

    if not member_to_remove:
        return jsonify({'error': 'User not in circle'}), 404

    db.session.delete(member_to_remove)
    db.session.commit()

    return jsonify({'message': 'Member removed successfully'}), 200


@circles_bp.route('/<int:circle_id>/invitations', methods=['POST'])
@jwt_required()
@circle_admin_required
def create_invitation(circle, user, member, circle_id):
    """Generate invitation code (admin only)"""
    # Generate unique code
    code = secrets.token_urlsafe(16)

    invitation = Invitation(
        circle_id=circle.id,
        code=code,
        created_by_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        uses_remaining=None  # Unlimited uses
    )
    db.session.add(invitation)
    db.session.commit()

    # Generate invite URL (update for production)
    base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    invite_url = f"{base_url}/invite/{code}"

    # Generate email body for copy/paste
    email_body = f"""You've been invited to join "{circle.name}" on Movie Matcher!

Click here to join: {invite_url}

This invitation expires in 30 days."""

    return jsonify({
        'code': code,
        'invite_url': invite_url,
        'email_body': email_body,
        'expires_at': invitation.expires_at.isoformat()
    }), 201


@circles_bp.route('/<int:circle_id>/invitations', methods=['GET'])
@jwt_required()
@circle_admin_required
def get_invitations(circle, user, member, circle_id):
    """List active invitations for circle (admin only)"""
    invitations = Invitation.query.filter_by(
        circle_id=circle.id,
        is_active=True
    ).filter(Invitation.expires_at > datetime.utcnow()).all()

    result = []
    for inv in invitations:
        result.append({
            'id': inv.id,
            'code': inv.code,
            'created_at': inv.created_at.isoformat(),
            'expires_at': inv.expires_at.isoformat(),
            'uses_remaining': inv.uses_remaining
        })

    return jsonify(result), 200


@circles_bp.route('/<int:circle_id>/invite-by-email', methods=['POST'])
@jwt_required()
@circle_admin_required
def invite_by_email(circle, user, member, circle_id):
    """Invite user by email (admin only). If user exists, add them. If not, create pending invite."""
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email required'}), 400

    email = email.lower().strip()

    # Check if user already exists
    existing_user = User.query.filter(func.lower(User.email) == email).first()

    if existing_user:
        # Check if already a member
        existing_member = CircleMember.query.filter_by(
            circle_id=circle.id,
            user_id=existing_user.id
        ).first()

        if existing_member:
            return jsonify({'error': 'User is already a member of this circle'}), 400

        # Add existing user to circle
        new_member = CircleMember(
            circle_id=circle.id,
            user_id=existing_user.id,
            role='member'
        )
        db.session.add(new_member)
        db.session.commit()

        return jsonify({
            'message': f'{email} has been added to the circle',
            'status': 'added'
        }), 200
    else:
        # Check if pending invite already exists
        existing_invite = PendingInvite.query.filter(
            func.lower(PendingInvite.email) == email,
            PendingInvite.circle_id == circle.id
        ).first()

        if existing_invite:
            return jsonify({'error': 'Invitation already pending for this email'}), 400

        # Create pending invite
        pending = PendingInvite(
            email=email,
            circle_id=circle.id,
            invited_by_id=user.id
        )
        db.session.add(pending)
        db.session.commit()

        return jsonify({
            'message': f'Invitation sent to {email}. They will be added when they register.',
            'status': 'pending'
        }), 201


@circles_bp.route('/<int:circle_id>/pending-invites', methods=['GET'])
@jwt_required()
@circle_admin_required
def get_pending_invites(circle, user, member, circle_id):
    """List pending email invitations for circle (admin only)"""
    pending = PendingInvite.query.filter_by(circle_id=circle.id).all()

    result = []
    for invite in pending:
        result.append({
            'id': invite.id,
            'email': invite.email,
            'created_at': invite.created_at.isoformat(),
            'invited_by': invite.invited_by.display_name or invite.invited_by.email
        })

    return jsonify(result), 200


@circles_bp.route('/<int:circle_id>/pending-invites/<int:invite_id>', methods=['DELETE'])
@jwt_required()
@circle_admin_required
def cancel_pending_invite(circle, user, member, circle_id, invite_id):
    """Cancel a pending email invitation (admin only)"""
    invite = PendingInvite.query.filter_by(id=invite_id, circle_id=circle.id).first()

    if not invite:
        return jsonify({'error': 'Pending invite not found'}), 404

    db.session.delete(invite)
    db.session.commit()

    return jsonify({'message': 'Invitation cancelled'}), 200


@circles_bp.route('/<int:circle_id>/analytics', methods=['GET'])
@jwt_required()
@circle_admin_required
def get_circle_analytics(circle, user, member, circle_id):
    """Get analytics for circle (admin only)"""
    from services.analytics_service import get_circle_analytics_data

    analytics = get_circle_analytics_data(circle.id)
    return jsonify(analytics), 200


def get_unseen_count(user_id, circle_id):
    """Helper to count unseen movies in a circle"""
    circle_movie_ids = [
        cm.movie_id
        for cm in CircleMovie.query.filter_by(circle_id=circle_id).all()
    ]
    swiped_movie_ids = [
        swipe.movie_id
        for swipe in UserSwipe.query.filter_by(
            user_id=user_id,
            circle_id=circle_id
        ).all()
    ]
    return len(set(circle_movie_ids) - set(swiped_movie_ids))
