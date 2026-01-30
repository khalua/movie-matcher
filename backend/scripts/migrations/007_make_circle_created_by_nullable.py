#!/usr/bin/env python3
"""
Migration 007: Make user foreign keys nullable for user deletion

Allows circles and circle_movies to exist after their creator is deleted.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import text


def migrate():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            print("Making circles.created_by_id nullable...")
            conn.execute(text('ALTER TABLE circles ALTER COLUMN created_by_id DROP NOT NULL'))

            print("Making circle_movies.added_by_id nullable...")
            conn.execute(text('ALTER TABLE circle_movies ALTER COLUMN added_by_id DROP NOT NULL'))

            conn.commit()
        print("Migration 007 complete!")


if __name__ == '__main__':
    migrate()
