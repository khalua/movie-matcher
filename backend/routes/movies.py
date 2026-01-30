from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from auth import circle_required, circle_admin_required
from models import db, Movie, CircleMovie, UserSwipe, User, CircleMember, MatchEvent, SeenMovie, MovieComment, UserBoostStats
from services.omdb_service import log_omdb_call
from sqlalchemy import func
from datetime import date
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
    """Get next unseen movie in circle context, with boosted movie prioritization"""
    sort_order = request.args.get('sort', 'random')
    swipe_count = request.args.get('swipe_count', 0, type=int)
    logging.info(f"Fetching movie for user {user.email} in circle {circle.name} (sort={sort_order}, swipe_count={swipe_count})")

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

    movie = None
    is_boosted = False

    # Check if this should be a boosted movie (every 3rd card)
    if swipe_count > 0 and swipe_count % 3 == 0:
        # Get today's boost stats for this user/circle
        today = date.today()
        boost_stats = UserBoostStats.query.filter_by(
            user_id=user.id,
            circle_id=circle.id,
            date=today
        ).first()

        boosted_today = boost_stats.boosted_count if boost_stats else 0

        # Only try boosted if under daily cap of 10
        if boosted_today < 10:
            # Find unseen movies that other circle members have liked
            # Order by like count (most likes first), then by most recent like
            boosted_query = (
                db.session.query(
                    Movie,
                    func.count(UserSwipe.id).label('like_count'),
                    func.max(UserSwipe.swiped_at).label('latest_like')
                )
                .join(UserSwipe, UserSwipe.movie_id == Movie.id)
                .filter(Movie.id.in_(unseen_ids))
                .filter(UserSwipe.circle_id == circle.id)
                .filter(UserSwipe.user_id != user.id)
                .filter(UserSwipe.action == 'like')
                .group_by(Movie.id)
                .order_by(func.count(UserSwipe.id).desc(), func.max(UserSwipe.swiped_at).desc())
                .first()
            )

            if boosted_query:
                movie = boosted_query[0]
                is_boosted = True

                # Update boost stats
                if boost_stats:
                    boost_stats.boosted_count += 1
                else:
                    boost_stats = UserBoostStats(
                        user_id=user.id,
                        circle_id=circle.id,
                        date=today,
                        boosted_count=1
                    )
                    db.session.add(boost_stats)
                db.session.commit()

    # Fall back to normal selection if no boosted movie
    if not movie:
        if sort_order == 'alphabetical':
            # Get all unseen movies and sort by title
            unseen_movies = Movie.query.filter(Movie.id.in_(unseen_ids)).order_by(Movie.title).all()
            movie = unseen_movies[0] if unseen_movies else None
        else:
            # Default: random
            movie_id = random.choice(unseen_ids)
            movie = Movie.query.get(movie_id)

    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    # Check if user swiped this movie in OTHER circles
    other_swipes = UserSwipe.query.filter(
        UserSwipe.user_id == user.id,
        UserSwipe.movie_id == movie.id,
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
    response['is_boosted'] = is_boosted

    return jsonify(response), 200


def detect_match(circle_id, movie_id, current_user_id):
    """
    Detect if liking a movie creates a match.
    Returns: dict with match info or None
    """
    # Get total circle members
    member_count = CircleMember.query.filter_by(circle_id=circle_id).count()

    # Get count of likes for this movie in this circle
    like_count = UserSwipe.query.filter_by(
        circle_id=circle_id,
        movie_id=movie_id,
        action='like'
    ).count()

    # Need at least 2 likes for a match
    if like_count < 2:
        return None

    # Get users who liked this movie
    liking_users = (
        db.session.query(User)
        .join(UserSwipe)
        .filter(UserSwipe.circle_id == circle_id)
        .filter(UserSwipe.movie_id == movie_id)
        .filter(UserSwipe.action == 'like')
        .all()
    )

    # Determine match type
    if like_count == member_count:
        match_type = 'full'
    else:
        match_type = 'partial'

    # Check if this exact match type already exists (avoid duplicates)
    existing_event = MatchEvent.query.filter_by(
        circle_id=circle_id,
        movie_id=movie_id,
        match_type=match_type
    ).first()

    if not existing_event:
        # Record new match event
        match_event = MatchEvent(
            circle_id=circle_id,
            movie_id=movie_id,
            match_type=match_type,
            triggered_by_user_id=current_user_id,
            member_count_at_time=member_count,
            like_count=like_count
        )
        db.session.add(match_event)

    return {
        'match_type': match_type,
        'like_count': like_count,
        'member_count': member_count,
        'matched_users': [{'id': u.id, 'display_name': u.display_name or u.email} for u in liking_users]
    }


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

    db.session.flush()  # Ensure swipe is recorded before match detection

    # Detect if this creates a match
    match_info = detect_match(circle.id, movie_id, user.id)

    db.session.commit()

    response = {'message': 'Movie liked successfully'}
    if match_info:
        response['match'] = match_info
        response['match']['movie'] = movie.to_dict()

    return jsonify(response), 200


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
    """Get movie matches within circle (excludes seen movies)"""
    data = request.get_json()
    user_ids = data.get('userIds', [])

    if len(user_ids) < 2:
        return jsonify({'error': 'Select at least 2 users'}), 400

    # Validate all users are in this circle
    circle_member_ids = [m.user_id for m in circle.members]
    if not all(uid in circle_member_ids for uid in user_ids):
        return jsonify({'error': 'All users must be in this circle'}), 403

    # Get seen movie IDs to exclude
    seen_movie_ids = [
        s.movie_id for s in SeenMovie.query.filter_by(circle_id=circle.id).all()
    ]

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

    # Filter out seen movies
    matched_movies = [m for m in matched_movies if m.id not in seen_movie_ids]

    result = []
    for movie in matched_movies:
        matched_users = (
            User.query
            .join(UserSwipe)
            .filter(UserSwipe.movie_id == movie.id)
            .filter(UserSwipe.circle_id == circle.id)
            .filter(UserSwipe.action == 'like')
            .all()
        )

        movie_dict = movie.to_dict()
        movie_dict['match_count'] = len(matched_users)
        movie_dict['matched_users'] = [
            {'id': u.id, 'display_name': u.display_name or u.email}
            for u in matched_users
        ]
        movie_dict['comment_count'] = MovieComment.query.filter_by(
            movie_id=movie.id,
            circle_id=circle.id
        ).count()

        # Count unread comments for this movie
        unread_query = MovieComment.query.filter(
            MovieComment.movie_id == movie.id,
            MovieComment.circle_id == circle.id,
            MovieComment.user_id != user.id
        )
        last_seen = member.last_seen_comments_at if member else None
        if last_seen:
            unread_query = unread_query.filter(
                MovieComment.created_at > last_seen
            )
        movie_dict['unread_comment_count'] = unread_query.count()

        result.append(movie_dict)

    return jsonify(result), 200


@movies_bp.route('/matches/unread', methods=['GET'])
@jwt_required()
@circle_required
def get_unread_matches(circle, user, member):
    """Get full matches the user hasn't seen since last login"""
    from models import UserMatchSeen
    from datetime import datetime

    # Get user's last seen match for this circle
    user_seen = UserMatchSeen.query.filter_by(
        user_id=user.id,
        circle_id=circle.id
    ).first()

    last_seen_id = user_seen.last_seen_match_id if user_seen else 0

    # Get all FULL matches in this circle that occurred after last seen
    # Don't show matches the user triggered themselves
    unread_matches = (
        MatchEvent.query
        .filter(MatchEvent.circle_id == circle.id)
        .filter(MatchEvent.match_type == 'full')
        .filter(MatchEvent.id > (last_seen_id or 0))
        .filter(MatchEvent.triggered_by_user_id != user.id)
        .order_by(MatchEvent.created_at.desc())
        .all()
    )

    result = []
    for match_event in unread_matches:
        movie = Movie.query.get(match_event.movie_id)
        result.append({
            'id': match_event.id,
            'match_type': match_event.match_type,
            'movie': movie.to_dict(),
            'like_count': match_event.like_count,
            'member_count': match_event.member_count_at_time,
            'created_at': match_event.created_at.isoformat()
        })

    return jsonify(result), 200


@movies_bp.route('/matches/mark-seen', methods=['POST'])
@jwt_required()
@circle_required
def mark_matches_seen(circle, user, member):
    """Mark all matches as seen up to a given match_id"""
    from models import UserMatchSeen
    from datetime import datetime

    data = request.get_json()
    last_match_id = data.get('last_match_id')

    if not last_match_id:
        return jsonify({'error': 'last_match_id required'}), 400

    user_seen = UserMatchSeen.query.filter_by(
        user_id=user.id,
        circle_id=circle.id
    ).first()

    if user_seen:
        user_seen.last_seen_match_id = last_match_id
        user_seen.last_seen_at = datetime.utcnow()
    else:
        user_seen = UserMatchSeen(
            user_id=user.id,
            circle_id=circle.id,
            last_seen_match_id=last_match_id
        )
        db.session.add(user_seen)

    db.session.commit()
    return jsonify({'message': 'Matches marked as seen'}), 200


@movies_bp.route('/search', methods=['GET'])
@jwt_required()
@circle_required
def search_movie(circle, user, member):
    """Search for movies via OMDB API - returns multiple results for user selection"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'No search query provided'}), 400

    if not OMDB_API_KEY:
        return jsonify({'error': 'OMDB API key not configured'}), 500

    # Use OMDB search API (s=) to get multiple results instead of single title match (t=)
    response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&s={query}&type=movie")
    log_omdb_call()  # Track API usage
    if response.status_code != 200:
        return jsonify({'error': 'Failed to search movies'}), 500

    data = response.json()
    if data.get('Response') != 'True':
        return jsonify({'error': data.get('Error', 'No movies found')}), 404

    results = []
    for movie in data.get('Search', []):
        year = int(movie['Year'][:4]) if movie.get('Year') and movie['Year'][:4].isdigit() else None
        existing = Movie.query.filter_by(title=movie['Title'], year=year).first()
        # Check if movie is in the current circle, not just if it exists globally
        in_circle = False
        if existing:
            in_circle = CircleMovie.query.filter_by(
                circle_id=circle.id,
                movie_id=existing.id
            ).first() is not None
        results.append({
            'imdbID': movie.get('imdbID'),
            'Title': movie.get('Title'),
            'Year': movie.get('Year'),
            'Poster': movie.get('Poster'),
            'Type': movie.get('Type'),
            'alreadyInDatabase': in_circle
        })

    return jsonify(results), 200


@movies_bp.route('/details/<imdb_id>', methods=['GET'])
@jwt_required()
@circle_required
def get_movie_details(imdb_id, circle, user, member):
    """Get full movie details from OMDB by IMDB ID"""
    if not OMDB_API_KEY:
        return jsonify({'error': 'OMDB API key not configured'}), 500

    response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}")
    log_omdb_call()  # Track API usage
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch movie details'}), 500

    movie_data = response.json()
    if movie_data.get('Response') != 'True':
        return jsonify({'error': movie_data.get('Error', 'Movie not found')}), 404

    # Check if movie already exists in the current circle
    year = int(movie_data['Year'][:4]) if movie_data.get('Year') and movie_data['Year'][:4].isdigit() else None
    existing = Movie.query.filter_by(title=movie_data['Title'], year=year).first()
    in_circle = False
    if existing:
        in_circle = CircleMovie.query.filter_by(
            circle_id=circle.id,
            movie_id=existing.id
        ).first() is not None
    movie_data['alreadyInDatabase'] = in_circle

    # Get streaming availability if TMDB key available
    if TMDB_API_KEY:
        movie_data['streaming'] = get_streaming_for_movie(movie_data['Title'], year)

    return jsonify(movie_data), 200


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
    """Get all movies in current circle with metadata (circle admin or site admin only)"""
    # Only circle admins and site admins can view all movies
    is_circle_admin = member and member.role == 'admin'
    if not is_circle_admin and not user.is_site_admin:
        return jsonify({'error': 'Admin access required'}), 403

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

            # Show pack name if from a pack, "Movie Matcher" for system-seeded, else the user
            if getattr(circle_movie, 'source_pack_name', None):
                movie_dict['added_by'] = {
                    'id': None,
                    'display_name': circle_movie.source_pack_name
                }
                movie_dict['source_pack'] = circle_movie.source_pack_name
            elif getattr(circle_movie, 'is_system_seeded', False):
                movie_dict['added_by'] = {
                    'id': None,
                    'display_name': 'Movie Matcher'
                }
            else:
                added_by_user = User.query.get(circle_movie.added_by_id)
                movie_dict['added_by'] = {
                    'id': circle_movie.added_by_id,
                    'display_name': added_by_user.display_name or added_by_user.email if added_by_user else 'Unknown'
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


# ============== Seen Movies Endpoints ==============

@movies_bp.route('/<int:movie_id>/mark-seen', methods=['POST'])
@jwt_required()
@circle_required
def mark_movie_seen(movie_id, circle, user, member):
    """Mark a matched movie as seen (watched)"""
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

    # Check if already marked as seen
    existing = SeenMovie.query.filter_by(
        movie_id=movie_id,
        circle_id=circle.id
    ).first()

    if existing:
        return jsonify({'error': 'Movie already marked as seen'}), 400

    seen_movie = SeenMovie(
        movie_id=movie_id,
        circle_id=circle.id,
        marked_by_user_id=user.id
    )
    db.session.add(seen_movie)
    db.session.commit()

    return jsonify({
        'message': 'Movie marked as seen',
        'seen_movie': seen_movie.to_dict()
    }), 201


@movies_bp.route('/<int:movie_id>/mark-seen', methods=['DELETE'])
@jwt_required()
@circle_required
def unmark_movie_seen(movie_id, circle, user, member):
    """Remove seen marking from a movie (keeps comments but hidden)"""
    seen_movie = SeenMovie.query.filter_by(
        movie_id=movie_id,
        circle_id=circle.id
    ).first()

    if not seen_movie:
        return jsonify({'error': 'Movie not marked as seen'}), 404

    db.session.delete(seen_movie)
    db.session.commit()

    return jsonify({'message': 'Seen marking removed'}), 200


@movies_bp.route('/seen', methods=['GET'])
@jwt_required()
@circle_required
def get_seen_movies(circle, user, member):
    """Get all seen movies for the circle, ordered by when marked seen (newest first)"""
    seen_movies = (
        SeenMovie.query
        .filter_by(circle_id=circle.id)
        .order_by(SeenMovie.marked_at.desc())
        .all()
    )

    result = []
    for seen in seen_movies:
        movie = seen.movie
        movie_dict = movie.to_dict()
        movie_dict['seen_info'] = seen.to_dict()

        # Get comment count
        comment_count = MovieComment.query.filter_by(
            movie_id=movie.id,
            circle_id=circle.id
        ).count()
        movie_dict['comment_count'] = comment_count

        # Get users who liked this movie in this circle
        liking_users = (
            User.query
            .join(UserSwipe)
            .filter(UserSwipe.movie_id == movie.id)
            .filter(UserSwipe.circle_id == circle.id)
            .filter(UserSwipe.action == 'like')
            .all()
        )
        movie_dict['matched_users'] = [
            {'id': u.id, 'display_name': u.display_name or u.email}
            for u in liking_users
        ]

        result.append(movie_dict)

    return jsonify(result), 200


# ============== Comments Endpoints ==============

@movies_bp.route('/<int:movie_id>/comments', methods=['POST'])
@jwt_required()
@circle_required
def add_comment(movie_id, circle, user, member):
    """Add a comment to a movie in this circle"""
    data = request.get_json()
    content = data.get('content', '').strip() if data else ''

    if not content:
        return jsonify({'error': 'Comment content required'}), 400

    if len(content) > 1000:
        return jsonify({'error': 'Comment too long (max 1000 characters)'}), 400

    # Verify movie exists
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

    comment = MovieComment(
        movie_id=movie_id,
        circle_id=circle.id,
        user_id=user.id,
        content=content
    )
    db.session.add(comment)
    db.session.commit()

    comment_dict = comment.to_dict(current_user_id=user.id)

    return jsonify(comment_dict), 201


@movies_bp.route('/<int:movie_id>/comments', methods=['GET'])
@jwt_required()
@circle_required
def get_comments(movie_id, circle, user, member):
    """Get comments for a movie in this circle"""
    comments = (
        MovieComment.query
        .filter_by(movie_id=movie_id, circle_id=circle.id)
        .order_by(MovieComment.created_at.desc())
        .all()
    )

    return jsonify([c.to_dict(current_user_id=user.id) for c in comments]), 200


@movies_bp.route('/<int:movie_id>/comments/<int:comment_id>', methods=['DELETE'])
@jwt_required()
@circle_required
def delete_comment(movie_id, comment_id, circle, user, member):
    """Delete own comment (or any comment if site admin)"""
    comment = MovieComment.query.filter_by(
        id=comment_id,
        movie_id=movie_id,
        circle_id=circle.id
    ).first()

    if not comment:
        return jsonify({'error': 'Comment not found'}), 404

    # Only author or site admin can delete
    if comment.user_id != user.id and not user.is_site_admin:
        return jsonify({'error': 'Cannot delete another user\'s comment'}), 403

    db.session.delete(comment)
    db.session.commit()

    return jsonify({'message': 'Comment deleted'}), 200


@movies_bp.route('/comments/unread-count', methods=['GET'])
@jwt_required()
@circle_required
def get_unread_comments_count(circle, user, member):
    """Get count of comments created since user last viewed comments"""
    from datetime import datetime

    # Site admins viewing circles they're not members of won't have a member record
    last_seen = member.last_seen_comments_at if member else None

    # Count comments in this circle that are newer than last_seen and not by this user
    query = MovieComment.query.filter(
        MovieComment.circle_id == circle.id,
        MovieComment.user_id != user.id  # Don't count own comments
    )

    if last_seen:
        query = query.filter(MovieComment.created_at > last_seen)

    count = query.count()

    return jsonify({'unread_count': count}), 200


@movies_bp.route('/comments/mark-read', methods=['POST'])
@jwt_required()
@circle_required
def mark_comments_read(circle, user, member):
    """Mark all comments as read by updating last_seen_comments_at"""
    from datetime import datetime

    # Site admins viewing circles they're not members of won't have a member record
    if member:
        member.last_seen_comments_at = datetime.utcnow()
        db.session.commit()

    return jsonify({'message': 'Comments marked as read'}), 200


# ============== Circle Admin Movie Management ==============

@movies_bp.route('/manage', methods=['GET'])
@jwt_required()
@circle_admin_required
def list_circle_movies_for_management(circle, user, member):
    """List movies in this circle for management (circle admin only)"""
    search = request.args.get('search', '').strip()

    query = (
        db.session.query(Movie, CircleMovie)
        .join(CircleMovie, CircleMovie.movie_id == Movie.id)
        .filter(CircleMovie.circle_id == circle.id)
    )

    if search:
        query = query.filter(Movie.title.ilike(f'%{search}%'))

    results = query.order_by(Movie.title).limit(100).all()

    movies_data = []
    for movie, circle_movie in results:
        movie_dict = movie.to_dict()
        movie_dict['is_system_seeded'] = circle_movie.is_system_seeded
        movies_data.append(movie_dict)

    return jsonify(movies_data), 200


@movies_bp.route('/manage/<int:movie_id>', methods=['GET'])
@jwt_required()
@circle_admin_required
def get_movie_for_management(movie_id, circle, user, member):
    """Get movie details for management (circle admin only)"""
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

    movie_dict = movie.to_dict()
    movie_dict['is_system_seeded'] = circle_movie.is_system_seeded

    return jsonify(movie_dict), 200


@movies_bp.route('/manage/<int:movie_id>', methods=['PUT'])
@jwt_required()
@circle_admin_required
def edit_circle_movie(movie_id, circle, user, member):
    """
    Edit a movie's metadata (circle admin only).
    Note: This edits the global movie record, affecting all circles.
    """
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

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
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


@movies_bp.route('/manage/<int:movie_id>/replace', methods=['POST'])
@jwt_required()
@circle_admin_required
def replace_circle_movie(movie_id, circle, user, member):
    """
    Replace a movie with a different one in this circle (circle admin only).
    This creates/gets the new movie and swaps the circle association.
    Swipes in this circle are cleared so users can re-vote.

    Requires new movie data in OMDB format (Title, Year, Plot, etc.)
    """
    old_movie = Movie.query.get(movie_id)
    if not old_movie:
        return jsonify({'error': 'Movie not found'}), 404

    # Check movie is in this circle
    old_circle_movie = CircleMovie.query.filter_by(
        circle_id=circle.id,
        movie_id=movie_id
    ).first()
    if not old_circle_movie:
        return jsonify({'error': 'Movie not in this circle'}), 404

    data = request.get_json()
    if not data or not data.get('Title'):
        return jsonify({'error': 'New movie data required (Title, Year, Plot, etc.)'}), 400

    try:
        new_year = int(data['Year'][:4]) if data.get('Year') else None

        # Check if the new movie already exists
        new_movie = Movie.query.filter_by(title=data['Title'], year=new_year).first()

        if not new_movie:
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

        # Check if new movie is already in this circle
        existing_new = CircleMovie.query.filter_by(
            circle_id=circle.id,
            movie_id=new_movie.id
        ).first()

        if existing_new:
            # New movie already in circle, just remove the old one
            db.session.delete(old_circle_movie)
        else:
            # Update the circle movie to point to the new movie
            old_circle_movie.movie_id = new_movie.id

        # Clear swipes for old movie in THIS circle only
        swipes_deleted = UserSwipe.query.filter_by(
            movie_id=old_movie.id,
            circle_id=circle.id
        ).delete()

        # Clear match events for old movie in this circle
        MatchEvent.query.filter_by(
            movie_id=old_movie.id,
            circle_id=circle.id
        ).delete()

        # Clear seen records for old movie in this circle
        SeenMovie.query.filter_by(
            movie_id=old_movie.id,
            circle_id=circle.id
        ).delete()

        # Clear comments for old movie in this circle
        MovieComment.query.filter_by(
            movie_id=old_movie.id,
            circle_id=circle.id
        ).delete()

        db.session.commit()

        old_title = old_movie.title
        old_year = old_movie.year

        return jsonify({
            'message': 'Movie replaced successfully',
            'old_movie': f'{old_title} ({old_year})',
            'new_movie': new_movie.to_dict(),
            'swipes_cleared': swipes_deleted
        }), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error replacing movie: {str(e)}")
        return jsonify({'error': 'Failed to replace movie'}), 500


@movies_bp.route('/manage/<int:movie_id>', methods=['DELETE'])
@jwt_required()
@circle_admin_required
def remove_movie_from_circle(movie_id, circle, user, member):
    """
    Remove a movie from this circle (circle admin only).
    This only removes the movie from this circle, not from the database.
    """
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    circle_movie = CircleMovie.query.filter_by(
        circle_id=circle.id,
        movie_id=movie_id
    ).first()
    if not circle_movie:
        return jsonify({'error': 'Movie not in this circle'}), 404

    try:
        title = movie.title
        year = movie.year

        # Delete swipes for this movie in this circle
        swipe_count = UserSwipe.query.filter_by(
            movie_id=movie_id,
            circle_id=circle.id
        ).delete()

        # Delete match events
        MatchEvent.query.filter_by(
            movie_id=movie_id,
            circle_id=circle.id
        ).delete()

        # Delete seen records
        SeenMovie.query.filter_by(
            movie_id=movie_id,
            circle_id=circle.id
        ).delete()

        # Delete comments
        MovieComment.query.filter_by(
            movie_id=movie_id,
            circle_id=circle.id
        ).delete()

        # Remove from circle
        db.session.delete(circle_movie)
        db.session.commit()

        return jsonify({
            'message': 'Movie removed from circle',
            'removed_movie': f'{title} ({year})',
            'swipes_deleted': swipe_count
        }), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error removing movie from circle: {str(e)}")
        return jsonify({'error': 'Failed to remove movie'}), 500
