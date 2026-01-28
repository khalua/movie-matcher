#!/usr/bin/env python3
"""
Migration 002: Add Seen Movies feature

New tables:
- seen_movies: Track when movies are marked as seen (watched)
- movie_comments: Comments on movies within a circle
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import inspect


def check_table_exists(inspector, table_name):
    """Check if a table exists in the database"""
    return table_name in inspector.get_table_names()


def migrate():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # Create new tables (db.create_all handles this safely)
        print("Creating any missing tables...")
        db.create_all()
        print("Tables created/verified.")

        # Verify tables were created
        if check_table_exists(inspector, 'seen_movies'):
            print("Table 'seen_movies' exists.")
        else:
            # Re-check after create_all
            inspector = inspect(db.engine)
            if check_table_exists(inspector, 'seen_movies'):
                print("Table 'seen_movies' created successfully.")
            else:
                print("Warning: 'seen_movies' table was not created.")

        if check_table_exists(inspector, 'movie_comments'):
            print("Table 'movie_comments' exists.")
        else:
            # Re-check after create_all
            inspector = inspect(db.engine)
            if check_table_exists(inspector, 'movie_comments'):
                print("Table 'movie_comments' created successfully.")
            else:
                print("Warning: 'movie_comments' table was not created.")

        print("Migration 002 complete!")


if __name__ == '__main__':
    migrate()
