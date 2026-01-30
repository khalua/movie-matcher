from models import db, Movie, CircleMovie
from services.omdb_service import log_omdb_call
from sqlalchemy import func
import os
import requests
import logging

logger = logging.getLogger(__name__)


def get_top_movie_titles():
    """Read and parse top_movies.txt"""
    file_path = os.path.join(os.path.dirname(__file__), '../misc/top_movies.txt')
    if not os.path.exists(file_path):
        logger.warning(f"top_movies.txt not found at {file_path}")
        return []

    with open(file_path, 'r') as f:
        content = f.read()
    return [t.strip() for t in content.split(';') if t.strip()]


def find_movie_by_title(title):
    """Find a movie in DB by title (case-insensitive)"""
    return Movie.query.filter(func.lower(Movie.title) == func.lower(title)).first()


def fetch_movie_from_omdb(title, added_by_user_id):
    """Fetch movie from OMDB API and create Movie record"""
    OMDB_API_KEY = os.getenv('OMDB_API_KEY')
    if not OMDB_API_KEY:
        return None

    try:
        response = requests.get(
            f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}",
            timeout=10
        )
        log_omdb_call()  # Track API usage
        data = response.json()

        if data.get('Response') != 'True':
            logger.debug(f"Movie not found on OMDB: {title}")
            return None

        year = int(data['Year'][:4]) if data.get('Year') else None

        # Check again with exact title from OMDB (might differ from search term)
        movie = Movie.query.filter_by(title=data['Title'], year=year).first()
        if movie:
            return movie

        movie = Movie(
            title=data['Title'],
            year=year,
            poster=data.get('Poster', ''),
            description=data.get('Plot', ''),
            genre=data.get('Genre', ''),
            rating=data.get('imdbRating', 'N/A'),
            length=data.get('Runtime', 'N/A'),
            starring=data.get('Actors', ''),
            added_by_id=added_by_user_id
        )
        db.session.add(movie)
        db.session.flush()
        return movie
    except Exception as e:
        logger.error(f'Error fetching {title} from OMDB: {e}')
        return None


def ensure_default_movies_cached(added_by_user_id=None):
    """
    Pre-cache all default movies from top_movies.txt into the database.
    Call this once (e.g., on first startup or via admin endpoint) to populate the cache.
    Returns count of movies fetched from API.
    """
    titles = get_top_movie_titles()
    api_calls = 0

    for title in titles:
        # Check if already cached
        movie = find_movie_by_title(title)
        if movie:
            continue

        # Not cached, fetch from API
        movie = fetch_movie_from_omdb(title, added_by_user_id)
        if movie:
            api_calls += 1

    db.session.commit()
    logger.info(f"Default movies cache: {api_calls} API calls made, {len(titles) - api_calls} already cached")
    return api_calls


def seed_circle_with_top_movies(circle_id, added_by_user_id):
    """
    Seed circle with movies from top_movies.txt.
    Uses cached movies from DB when available, only calls OMDB API for missing movies.
    """
    titles = get_top_movie_titles()
    if not titles:
        return

    movies_added = 0
    api_calls = 0

    for title in titles:
        try:
            # First, try to find movie in database (fast, no API call)
            movie = find_movie_by_title(title)

            # If not found, fetch from OMDB API
            if not movie:
                movie = fetch_movie_from_omdb(title, added_by_user_id)
                if movie:
                    api_calls += 1

            if not movie:
                continue

            # Associate with circle (skip if already associated)
            existing = CircleMovie.query.filter_by(
                circle_id=circle_id,
                movie_id=movie.id
            ).first()

            if not existing:
                circle_movie = CircleMovie(
                    circle_id=circle_id,
                    movie_id=movie.id,
                    added_by_id=added_by_user_id,
                    is_system_seeded=True
                )
                db.session.add(circle_movie)
                movies_added += 1

        except Exception as e:
            logger.error(f'Error seeding {title}: {e}')
            continue

    db.session.commit()
    logger.info(f"Seeded circle {circle_id}: {movies_added} movies added, {api_calls} API calls (rest from cache)")
