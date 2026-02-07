#!/usr/bin/env python3
"""Migration 011: Backfill full plots from OMDB for all existing movies"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db, Movie
from services.omdb_service import log_omdb_call
import requests
import time
import logging

logger = logging.getLogger(__name__)

OMDB_API_KEY = os.getenv('OMDB_API_KEY')


def migrate():
    app = create_app()
    with app.app_context():
        if not OMDB_API_KEY:
            logger.warning("OMDB_API_KEY not set, skipping full plot backfill")
            return

        movies = Movie.query.all()
        updated = 0
        skipped = 0
        errors = 0

        logger.info(f"Backfilling full plots for {len(movies)} movies...")

        for movie in movies:
            try:
                # Search by title and year for best match
                params = f"t={movie.title}&plot=full"
                if movie.year:
                    params += f"&y={movie.year}"

                response = requests.get(
                    f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&{params}",
                    timeout=10
                )
                log_omdb_call()
                data = response.json()

                if data.get('Response') != 'True':
                    logger.debug(f"Not found on OMDB: {movie.title} ({movie.year})")
                    skipped += 1
                    continue

                full_plot = data.get('Plot', '')
                if full_plot and full_plot != 'N/A' and len(full_plot) > len(movie.description or ''):
                    movie.description = full_plot
                    updated += 1
                else:
                    skipped += 1

                # Rate limit: OMDB free tier is 1000/day
                time.sleep(0.2)

            except Exception as e:
                logger.error(f"Error fetching plot for {movie.title}: {e}")
                errors += 1
                continue

        db.session.commit()
        logger.info(f"Full plot backfill complete: {updated} updated, {skipped} skipped, {errors} errors")


if __name__ == '__main__':
    migrate()
