from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Circle, CircleMember, Invitation, CircleMovie, UserSwipe
from auth import circle_required, circle_admin_required
from datetime import datetime, timedelta
import secrets
import os

circles_bp = Blueprint('circles', __name__)


@circles_bp.route('', methods=['GET'])
@jwt_required()
def get_user_circles():
    """List all circles user is member of"""
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    circles = []
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

    # Seed with top_movies.txt
    from services.seed_service import seed_circle_with_top_movies
    try:
        seed_circle_with_top_movies(circle.id, user.id)
    except Exception as e:
        import logging
        logging.warning(f"Could not seed circle with top movies: {str(e)}")

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

Or enter this code: {code}

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
