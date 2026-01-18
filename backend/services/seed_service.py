from models import db, Movie, CircleMovie
import os
import requests
import logging

logger = logging.getLogger(__name__)


def seed_circle_with_top_movies(circle_id, added_by_user_id):
    """Seed circle with movies from top_movies.txt"""
    file_path = os.path.join(os.path.dirname(__file__), '../misc/top_movies.txt')

    if not os.path.exists(file_path):
        logger.warning(f"top_movies.txt not found at {file_path}")
        return

    with open(file_path, 'r') as f:
        content = f.read()

    # Parse semicolon-separated titles
    titles = [t.strip() for t in content.split(';') if t.strip()]

    OMDB_API_KEY = os.getenv('OMDB_API_KEY')
    if not OMDB_API_KEY:
        logger.warning('No OMDB_API_KEY, skipping seed')
        return

    movies_added = 0
    for title in titles:
        try:
            # Fetch from OMDB
            response = requests.get(
                f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}",
                timeout=10
            )
            data = response.json()

            if data.get('Response') != 'True':
                logger.debug(f"Movie not found on OMDB: {title}")
                continue

            year = int(data['Year'][:4]) if data.get('Year') else None

            # Check if movie exists globally
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
                    added_by_id=added_by_user_id
                )
                db.session.add(movie)
                db.session.flush()

            # Associate with circle
            circle_movie = CircleMovie.query.filter_by(
                circle_id=circle_id,
                movie_id=movie.id
            ).first()

            if not circle_movie:
                circle_movie = CircleMovie(
                    circle_id=circle_id,
                    movie_id=movie.id,
                    added_by_id=added_by_user_id
                )
                db.session.add(circle_movie)
                movies_added += 1

        except Exception as e:
            logger.error(f'Error seeding {title}: {e}')
            continue

    db.session.commit()
    logger.info(f"Seeded circle {circle_id} with {movies_added} movies")
