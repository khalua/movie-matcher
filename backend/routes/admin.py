from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from auth import site_admin_required
from models import db, Circle, User, CircleMember
from services.analytics_service import get_global_analytics_data
from services.seed_service import seed_circle_with_top_movies
import logging

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/analytics', methods=['GET'])
@jwt_required()
@site_admin_required
def get_global_analytics(user):
    """Get global analytics (site admin only)"""
    analytics = get_global_analytics_data()
    return jsonify(analytics), 200


@admin_bp.route('/circles', methods=['GET'])
@jwt_required()
@site_admin_required
def get_all_circles(user):
    """List all circles (site admin only)"""
    circles = Circle.query.filter_by(is_active=True).all()

    result = []
    for circle in circles:
        result.append({
            'id': circle.id,
            'name': circle.name,
            'created_at': circle.created_at.isoformat(),
            'member_count': len(circle.members),
            'movie_count': len(circle.movies)
        })

    return jsonify(result), 200


@admin_bp.route('/circles/<int:circle_id>/members', methods=['GET'])
@jwt_required()
@site_admin_required
def get_circle_members_admin(user, circle_id):
    """Get members of any circle (site admin only)"""
    circle = Circle.query.get(circle_id)
    if not circle:
        return jsonify({'error': 'Circle not found'}), 404

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


@admin_bp.route('/seed-circles', methods=['POST'])
@jwt_required()
@site_admin_required
def seed_all_circles(user):
    """Seed all circles with top_movies.txt (site admin only)"""
    try:
        circles = Circle.query.filter_by(is_active=True).all()

        for circle in circles:
            seed_circle_with_top_movies(circle.id, user.id)

        db.session.commit()

        return jsonify({
            'message': f'Successfully seeded {len(circles)} circles',
            'circles_seeded': len(circles)
        }), 200
    except Exception as e:
        logging.error(f"Error seeding circles: {str(e)}")
        return jsonify({'error': 'Failed to seed circles'}), 500
