"""API routes for Movie Packs"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import db, User, Circle, CircleMember
from services import pack_service, tmdb_service

packs_bp = Blueprint('packs', __name__)


@packs_bp.route('', methods=['GET'])
@jwt_required()
def get_packs():
    """Get all available movie packs"""
    packs = pack_service.get_all_packs()
    return jsonify({'packs': packs}), 200


@packs_bp.route('/<int:pack_id>', methods=['GET'])
@jwt_required()
def get_pack(pack_id):
    """Get a single pack by ID"""
    pack = pack_service.get_pack_by_id(pack_id)
    if not pack:
        return jsonify({'error': 'Pack not found'}), 404
    return jsonify({'pack': pack.to_dict()}), 200


@packs_bp.route('/<int:pack_id>/preview', methods=['GET'])
@jwt_required()
def preview_pack(pack_id):
    """
    Preview movies in a pack before adding.
    Optional query params: circle_id (to show which are already in circle)
    """
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    circle_id = request.args.get('circle_id', type=int)

    result, error = pack_service.get_pack_movies(pack_id, circle_id, user.id)
    if error:
        return jsonify({'error': error}), 404

    return jsonify(result), 200


@packs_bp.route('/<int:pack_id>/add-to-circle', methods=['POST'])
@jwt_required()
def add_pack_to_circle(pack_id):
    """
    Add a pack to a circle. Circle admin only.
    Request body: { "circle_id": 123 }
    """
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    circle_id = data.get('circle_id')
    if not circle_id:
        return jsonify({'error': 'circle_id is required'}), 400

    # Verify user is admin of this circle (or site admin)
    member = CircleMember.query.filter_by(
        circle_id=circle_id,
        user_id=user.id
    ).first()

    is_circle_admin = member and member.role == 'admin'

    if not is_circle_admin and not user.is_site_admin:
        return jsonify({'error': 'Only circle admins can add packs'}), 403

    # Add pack to circle
    result, error = pack_service.add_pack_to_circle(pack_id, circle_id, user.id)
    if error:
        return jsonify({'error': error}), 400

    return jsonify(result), 200


@packs_bp.route('/<int:pack_id>/refresh', methods=['POST'])
@jwt_required()
def refresh_pack(pack_id):
    """
    Manually refresh a pack's cache. Site admin only.
    """
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    if not user or not user.is_site_admin:
        return jsonify({'error': 'Site admin access required'}), 403

    result, error = pack_service.refresh_pack(pack_id)
    if error:
        return jsonify({'error': error}), 400

    return jsonify(result), 200


@packs_bp.route('/seed', methods=['POST'])
@jwt_required()
def seed_packs():
    """
    Seed pack definitions. Site admin only.
    This creates the pack records, not the movie cache.
    """
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    if not user or not user.is_site_admin:
        return jsonify({'error': 'Site admin access required'}), 403

    pack_service.seed_pack_definitions()
    return jsonify({'message': 'Pack definitions seeded'}), 200


@packs_bp.route('/tmdb-usage', methods=['GET'])
@jwt_required()
def get_tmdb_usage():
    """
    Get TMDB API usage statistics. Site admin only.
    """
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    if not user or not user.is_site_admin:
        return jsonify({'error': 'Site admin access required'}), 403

    usage = tmdb_service.get_tmdb_usage()
    return jsonify(usage), 200
