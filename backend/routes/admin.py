from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from auth import site_admin_required
from models import db, Circle, User, CircleMember, Movie, CircleMovie
from services.analytics_service import get_global_analytics_data
from services.seed_service import seed_circle_with_top_movies, ensure_default_movies_cached
import logging
import requests
import os

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


@admin_bp.route('/cache-default-movies', methods=['POST'])
@jwt_required()
@site_admin_required
def cache_default_movies(user):
    """
    Pre-cache all default movies from top_movies.txt (site admin only).
    Call this once to populate the movie cache, making subsequent circle creations instant.
    """
    try:
        # Count existing cached movies
        from services.seed_service import get_top_movie_titles
        titles = get_top_movie_titles()
        cached_before = Movie.query.count()

        # Cache missing movies
        api_calls = ensure_default_movies_cached(user.id)

        cached_after = Movie.query.count()

        return jsonify({
            'message': 'Default movies cache updated',
            'total_titles': len(titles),
            'api_calls_made': api_calls,
            'movies_in_db_before': cached_before,
            'movies_in_db_after': cached_after
        }), 200
    except Exception as e:
        logging.error(f"Error caching default movies: {str(e)}")
        return jsonify({'error': 'Failed to cache movies'}), 500


@admin_bp.route('/add-movie-all-circles', methods=['POST'])
@jwt_required()
@site_admin_required
def add_movie_to_all_circles(user):
    """
    Add a movie to all active circles (site admin only).
    Movies added this way are marked as system-seeded and show as "Movie Matcher".
    """
    data = request.get_json()

    if not data or not data.get('Title'):
        return jsonify({'error': 'Movie title required'}), 400

    try:
        # Create or get movie from database
        year = int(data['Year'][:4]) if data.get('Year') else None
        movie = Movie.query.filter_by(title=data['Title'], year=year).first()

        if not movie:
            movie = Movie(
                title=data['Title'],
                year=year,
                poster=data.get('Poster', ''),
                description=data.get('Plot', ''),
                genre=data.get('Genre', ''),
                rating=data.get('imdbRating', 'N/A'),
                length=data.get('Runtime', 'N/A'),
                starring=data.get('Actors', ''),
                added_by_id=user.id
            )
            db.session.add(movie)
            db.session.flush()

        # Add to all active circles
        circles = Circle.query.filter_by(is_active=True).all()
        circles_added = 0

        for circle in circles:
            existing = CircleMovie.query.filter_by(
                circle_id=circle.id,
                movie_id=movie.id
            ).first()

            if not existing:
                circle_movie = CircleMovie(
                    circle_id=circle.id,
                    movie_id=movie.id,
                    added_by_id=user.id,
                    is_system_seeded=True  # Mark as system-seeded so it shows as "Movie Matcher"
                )
                db.session.add(circle_movie)
                circles_added += 1

        db.session.commit()

        return jsonify({
            'message': f'Movie added to {circles_added} circles',
            'movie_id': movie.id,
            'circles_added': circles_added,
            'total_circles': len(circles)
        }), 201
    except Exception as e:
        logging.error(f"Error adding movie to all circles: {str(e)}")
        return jsonify({'error': 'Failed to add movie'}), 500
