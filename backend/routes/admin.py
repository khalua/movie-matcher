from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from auth import site_admin_required
from models import db, Circle, User, CircleMember, Movie, CircleMovie, UserSwipe, MatchEvent, SeenMovie, MovieComment
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


@admin_bp.route('/movies', methods=['GET'])
@jwt_required()
@site_admin_required
def list_all_movies(user):
    """List all movies in the database (site admin only)"""
    search = request.args.get('search', '').strip()

    query = Movie.query
    if search:
        query = query.filter(Movie.title.ilike(f'%{search}%'))

    movies = query.order_by(Movie.title).limit(100).all()

    result = []
    for movie in movies:
        circle_count = CircleMovie.query.filter_by(movie_id=movie.id).count()
        result.append({
            **movie.to_dict(),
            'circle_count': circle_count
        })

    return jsonify(result), 200


@admin_bp.route('/movies/<int:movie_id>', methods=['GET'])
@jwt_required()
@site_admin_required
def get_movie_details(user, movie_id):
    """Get detailed movie info including which circles it's in (site admin only)"""
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    # Get circles this movie is in
    circle_movies = CircleMovie.query.filter_by(movie_id=movie_id).all()
    circles = []
    for cm in circle_movies:
        circle = Circle.query.get(cm.circle_id)
        if circle:
            circles.append({
                'id': circle.id,
                'name': circle.name,
                'is_system_seeded': cm.is_system_seeded
            })

    return jsonify({
        **movie.to_dict(),
        'circles': circles,
        'circle_count': len(circles)
    }), 200


@admin_bp.route('/movies/<int:movie_id>', methods=['PUT'])
@jwt_required()
@site_admin_required
def edit_movie(user, movie_id):
    """
    Edit a movie's metadata (site admin only).
    Use this to fix incorrect movie entries.
    """
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        # Update fields if provided
        if 'title' in data:
            movie.title = data['title']
        if 'year' in data:
            movie.year = int(data['year'])
        if 'poster' in data:
            movie.poster = data['poster']
        if 'description' in data:
            movie.description = data['description']
        if 'genre' in data:
            movie.genre = data['genre']
        if 'rating' in data:
            movie.rating = data['rating']
        if 'length' in data:
            movie.length = data['length']
        if 'starring' in data:
            movie.starring = data['starring']

        db.session.commit()

        return jsonify({
            'message': 'Movie updated successfully',
            'movie': movie.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating movie: {str(e)}")
        return jsonify({'error': 'Failed to update movie'}), 500


@admin_bp.route('/movies/<int:movie_id>/replace', methods=['POST'])
@jwt_required()
@site_admin_required
def replace_movie(user, movie_id):
    """
    Replace a movie with a different one across all circles (site admin only).
    This transfers all circle associations from the old movie to the new one,
    then deletes the old movie. Use this when the wrong movie was fetched from OMDB.

    Requires new movie data in OMDB format (Title, Year, Plot, etc.)
    """
    old_movie = Movie.query.get(movie_id)
    if not old_movie:
        return jsonify({'error': 'Movie not found'}), 404

    data = request.get_json()
    if not data or not data.get('Title'):
        return jsonify({'error': 'New movie data required (Title, Year, Plot, etc.)'}), 400

    try:
        new_year = int(data['Year'][:4]) if data.get('Year') else None

        # Check if the new movie already exists
        new_movie = Movie.query.filter_by(title=data['Title'], year=new_year).first()

        if not new_movie:
            # Create the new movie
            new_movie = Movie(
                title=data['Title'],
                year=new_year,
                poster=data.get('Poster', ''),
                description=data.get('Plot', ''),
                genre=data.get('Genre', ''),
                rating=data.get('imdbRating', 'N/A'),
                length=data.get('Runtime', 'N/A'),
                starring=data.get('Actors', ''),
                added_by_id=user.id
            )
            db.session.add(new_movie)
            db.session.flush()

        # Transfer circle associations from old movie to new movie
        circle_movies = CircleMovie.query.filter_by(movie_id=old_movie.id).all()
        transferred = 0
        skipped = 0

        for cm in circle_movies:
            # Check if new movie is already in this circle
            existing = CircleMovie.query.filter_by(
                circle_id=cm.circle_id,
                movie_id=new_movie.id
            ).first()

            if existing:
                # New movie already in circle, just delete old association
                db.session.delete(cm)
                skipped += 1
            else:
                # Update association to point to new movie
                cm.movie_id = new_movie.id
                transferred += 1

        # Delete swipes for the old movie (users will need to re-swipe)
        swipes_deleted = UserSwipe.query.filter_by(movie_id=old_movie.id).delete()

        # Delete match events for old movie
        MatchEvent.query.filter_by(movie_id=old_movie.id).delete()

        # Delete seen movie records for old movie
        SeenMovie.query.filter_by(movie_id=old_movie.id).delete()

        # Delete comments on old movie
        MovieComment.query.filter_by(movie_id=old_movie.id).delete()

        # Now delete the old movie
        old_title = old_movie.title
        old_year = old_movie.year
        db.session.delete(old_movie)

        db.session.commit()

        return jsonify({
            'message': f'Movie replaced successfully',
            'old_movie': f'{old_title} ({old_year})',
            'new_movie': new_movie.to_dict(),
            'circles_transferred': transferred,
            'circles_skipped': skipped,
            'swipes_cleared': swipes_deleted
        }), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error replacing movie: {str(e)}")
        return jsonify({'error': 'Failed to replace movie'}), 500


@admin_bp.route('/movies/<int:movie_id>', methods=['DELETE'])
@jwt_required()
@site_admin_required
def delete_movie(user, movie_id):
    """
    Delete a movie from the database entirely (site admin only).
    This removes it from all circles and deletes all associated swipes/comments.
    """
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    try:
        title = movie.title
        year = movie.year

        # Count what we're deleting
        circle_count = CircleMovie.query.filter_by(movie_id=movie_id).count()
        swipe_count = UserSwipe.query.filter_by(movie_id=movie_id).count()

        # Delete all related records (cascades handle most, but be explicit)
        CircleMovie.query.filter_by(movie_id=movie_id).delete()
        UserSwipe.query.filter_by(movie_id=movie_id).delete()
        MatchEvent.query.filter_by(movie_id=movie_id).delete()
        SeenMovie.query.filter_by(movie_id=movie_id).delete()
        MovieComment.query.filter_by(movie_id=movie_id).delete()

        db.session.delete(movie)
        db.session.commit()

        return jsonify({
            'message': f'Movie deleted successfully',
            'deleted_movie': f'{title} ({year})',
            'circles_removed_from': circle_count,
            'swipes_deleted': swipe_count
        }), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting movie: {str(e)}")
        return jsonify({'error': 'Failed to delete movie'}), 500
