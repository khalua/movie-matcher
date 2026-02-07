from models import db, Movie
from services.omdb_service import log_omdb_call
from sqlalchemy import func
import os
import requests
import logging

logger = logging.getLogger(__name__)


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
            f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}&plot=full",
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
