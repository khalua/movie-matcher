from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from auth import circle_required
from models import db, Movie, CircleMovie, UserSwipe, User
from sqlalchemy import func
import random
import logging
import requests
import os

movies_bp = Blueprint('movies', __name__)

OMDB_API_KEY = os.environ.get('OMDB_API_KEY')
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')

# TMDB provider IDs for streaming services
STREAMING_PROVIDERS = {
    8: 'Netflix',
    9: 'Prime',
    15: 'Hulu',
    337: 'Disney+',
}


@movies_bp.route('/random', methods=['GET'])
@jwt_required()
@circle_required
def get_random_movie(circle, user, member):
    """Get random unseen movie in circle context"""
    logging.info(f"Fetching random movie for user {user.email} in circle {circle.name}")

    # Get all movies in this circle
    circle_movie_ids = [cm.movie_id for cm in circle.movies]

    if not circle_movie_ids:
        return jsonify({'message': 'No movies in this circle'}), 404

    # Get movies user has swiped in this circle
    swiped_movie_ids = [
        swipe.movie_id
        for swipe in UserSwipe.query.filter_by(
            user_id=user.id,
            circle_id=circle.id
        ).all()
    ]

    # Find unseen movies
    unseen_ids = list(set(circle_movie_ids) - set(swiped_movie_ids))

    if not unseen_ids:
        return jsonify({'message': 'No more unseen movies'}), 404

    # Pick random
    movie_id = random.choice(unseen_ids)
    movie = Movie.query.get(movie_id)

    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    # Check if user swiped this movie in OTHER circles
    other_swipes = UserSwipe.query.filter(
        UserSwipe.user_id == user.id,
        UserSwipe.movie_id == movie_id,
        UserSwipe.circle_id != circle.id
    ).all()

    response = movie.to_dict()
    response['swiped_in_other_circles'] = [
        {
            'circle_id': swipe.circle_id,
            'circle_name': swipe.circle.name,
            'action': swipe.action
        }
        for swipe in other_swipes
    ]

    return jsonify(response), 200


@movies_bp.route('/like', methods=['POST'])
@jwt_required()
@circle_required
def like_movie(circle, user, member):
    """Like a movie in circle context"""
    data = request.get_json()
    movie_id = data.get('movieId')

    if not movie_id:
        return jsonify({'error': 'Movie ID required'}), 400

    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    # Check movie is in this circle
    circle_movie = CircleMovie.query.filter_by(
        circle_id=circle.id,
        movie_id=movie_id
    ).first()

    if not circle_movie:
        return jsonify({'error': 'Movie not in this circle'}), 404

    # Create or update swipe
    swipe = UserSwipe.query.filter_by(
        user_id=user.id,
        movie_id=movie_id,
        circle_id=circle.id
    ).first()

    if swipe:
        swipe.action = 'like'
    else:
        swipe = UserSwipe(
            user_id=user.id,
            movie_id=movie_id,
            circle_id=circle.id,
            action='like'
        )
        db.session.add(swipe)

    db.session.commit()
    return jsonify({'message': 'Movie liked successfully'}), 200


@movies_bp.route('/dislike', methods=['POST'])
@jwt_required()
@circle_required
def dislike_movie(circle, user, member):
    """Dislike a movie in circle context"""
    data = request.get_json()
    movie_id = data.get('movieId')

    if not movie_id:
        return jsonify({'error': 'Movie ID required'}), 400

    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    # Check movie is in this circle
    circle_movie = CircleMovie.query.filter_by(
        circle_id=circle.id,
        movie_id=movie_id
    ).first()

    if not circle_movie:
        return jsonify({'error': 'Movie not in this circle'}), 404

    # Create or update swipe
    swipe = UserSwipe.query.filter_by(
        user_id=user.id,
        movie_id=movie_id,
        circle_id=circle.id
    ).first()

    if swipe:
        swipe.action = 'dislike'
    else:
        swipe = UserSwipe(
            user_id=user.id,
            movie_id=movie_id,
            circle_id=circle.id,
            action='dislike'
        )
        db.session.add(swipe)

    db.session.commit()
    return jsonify({'message': 'Movie marked as seen'}), 200


@movies_bp.route('/matches', methods=['POST'])
@jwt_required()
@circle_required
def get_matches(circle, user, member):
    """Get movie matches within circle"""
    data = request.get_json()
    user_ids = data.get('userIds', [])

    if len(user_ids) < 2:
        return jsonify({'error': 'Select at least 2 users'}), 400

    # Validate all users are in this circle
    circle_member_ids = [m.user_id for m in circle.members]
    if not all(uid in circle_member_ids for uid in user_ids):
        return jsonify({'error': 'All users must be in this circle'}), 403

    # Find movies liked by ALL selected users in THIS circle
    matched_movies = (
        db.session.query(Movie)
        .join(UserSwipe)
        .filter(UserSwipe.circle_id == circle.id)
        .filter(UserSwipe.user_id.in_(user_ids))
        .filter(UserSwipe.action == 'like')
        .group_by(Movie.id)
        .having(func.count(func.distinct(UserSwipe.user_id)) == len(user_ids))
        .all()
    )

    result = []
    for movie in matched_movies:
        matched_users = (
            User.query
            .join(UserSwipe)
            .filter(UserSwipe.movie_id == movie.id)
            .filter(UserSwipe.circle_id == circle.id)
            .filter(UserSwipe.action == 'like')
            .filter(User.id.in_(user_ids))
            .all()
        )

        movie_dict = movie.to_dict()
        movie_dict['match_count'] = len(matched_users)
        movie_dict['matched_users'] = [
            {'id': u.id, 'display_name': u.display_name or u.email}
            for u in matched_users
        ]
        result.append(movie_dict)

    return jsonify(result), 200


@movies_bp.route('/search', methods=['GET'])
@jwt_required()
def search_movie():
    """Search for movies via OMDB API"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'No search query provided'}), 400

    if not OMDB_API_KEY:
        return jsonify({'error': 'OMDB API key not configured'}), 500

    # Split by semicolon for multiple movies
    movie_titles = [title.strip() for title in query.split(';') if title.strip()]

    results = []
    for title in movie_titles:
        response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}")
        if response.status_code == 200:
            movie_data = response.json()
            if movie_data.get('Response') == 'True':
                # Check if movie already exists in database
                year = int(movie_data['Year'][:4]) if movie_data.get('Year') else None
                existing = Movie.query.filter_by(title=movie_data['Title'], year=year).first()
                movie_data['alreadyInDatabase'] = existing is not None

                # Get streaming availability if TMDB key available
                if TMDB_API_KEY:
                    movie_data['streaming'] = get_streaming_for_movie(movie_data['Title'], year)

                results.append(movie_data)

    if not results:
        return jsonify({'error': 'No movies found'}), 404

    return jsonify(results), 200


@movies_bp.route('/add', methods=['POST'])
@jwt_required()
@circle_required
def add_movie(circle, user, member):
    """Add movie to one or more circles"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Get all circles user belongs to
    user_circle_ids = [m.circle_id for m in user.circles]

    # Get circle_ids from request (defaults to current circle only)
    circle_ids = data.get('circle_ids', [circle.id])

    # Validate user is member of all specified circles
    for cid in circle_ids:
        if cid not in user_circle_ids:
            return jsonify({'error': f'Not a member of circle {cid}'}), 403

    # Create or get movie
    year = int(data['Year']) if data.get('Year') else None
    movie = Movie.query.filter_by(
        title=data['Title'],
        year=year
    ).first()

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
        db.session.flush()  # Get movie.id

    # Associate with circles
    for cid in circle_ids:
        circle_movie = CircleMovie.query.filter_by(
            circle_id=cid,
            movie_id=movie.id
        ).first()

        if not circle_movie:
            circle_movie = CircleMovie(
                circle_id=cid,
                movie_id=movie.id,
                added_by_id=user.id
            )
            db.session.add(circle_movie)

    db.session.commit()
    return jsonify({'message': 'Movie added successfully', 'id': movie.id}), 201


@movies_bp.route('/all', methods=['GET'])
@jwt_required()
@circle_required
def get_all_movies(circle, user, member):
    """Get all movies in current circle with metadata"""
    try:
        # Get all users in this circle
        circle_user_ids = [m.user_id for m in circle.members]

        # Get all movies in this circle
        movies_data = []
        for circle_movie in circle.movies:
            movie = circle_movie.movie

            # Count likes in this circle
            likes_count = UserSwipe.query.filter_by(
                movie_id=movie.id,
                circle_id=circle.id,
                action='like'
            ).count()

            # Get users who have seen this movie in this circle
            seen_user_ids = [
                swipe.user_id
                for swipe in UserSwipe.query.filter_by(
                    movie_id=movie.id,
                    circle_id=circle.id
                ).all()
            ]

            # Find users who haven't seen it
            unseen_user_ids = set(circle_user_ids) - set(seen_user_ids)
            unseen_users = User.query.filter(User.id.in_(unseen_user_ids)).all()

            movie_dict = movie.to_dict()
            movie_dict['likes_count'] = likes_count
            movie_dict['unseen_by'] = [
                {'id': u.id, 'display_name': u.display_name or u.email}
                for u in unseen_users
            ]
            movie_dict['added_by'] = {
                'id': circle_movie.added_by_id,
                'display_name': User.query.get(circle_movie.added_by_id).display_name
            }
            movies_data.append(movie_dict)

        return jsonify(movies_data), 200
    except Exception as e:
        logging.error(f"Error fetching all movies: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching movies'}), 500


@movies_bp.route('/<int:movie_id>/streaming', methods=['GET'])
@jwt_required()
def get_streaming_availability(movie_id):
    """Get streaming availability for a movie from TMDB"""
    if not TMDB_API_KEY:
        return jsonify({'error': 'TMDB API key not configured'}), 500

    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    streaming = get_streaming_for_movie(movie.title, movie.year)
    return jsonify({'streaming': streaming}), 200


def get_streaming_for_movie(title, year):
    """Helper function to get streaming availability from TMDB"""
    if not TMDB_API_KEY:
        return []

    try:
        # Search for the movie on TMDB
        search_url = "https://api.themoviedb.org/3/search/movie"
        search_params = {
            'api_key': TMDB_API_KEY,
            'query': title,
            'year': year
        }
        search_response = requests.get(search_url, params=search_params)
        search_data = search_response.json()

        if not search_data.get('results'):
            return []

        tmdb_id = search_data['results'][0]['id']

        # Get watch providers
        providers_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/watch/providers"
        providers_params = {'api_key': TMDB_API_KEY}
        providers_response = requests.get(providers_url, params=providers_params)
        providers_data = providers_response.json()

        us_data = providers_data.get('results', {}).get('US', {})
        flatrate = us_data.get('flatrate', [])

        available_on = []
        for provider in flatrate:
            provider_id = provider.get('provider_id')
            if provider_id in STREAMING_PROVIDERS:
                available_on.append(STREAMING_PROVIDERS[provider_id])

        return available_on
    except Exception as e:
        logging.error(f"Error fetching streaming for {title}: {str(e)}")
        return []
