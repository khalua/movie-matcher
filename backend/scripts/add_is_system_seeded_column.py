#!/usr/bin/env python3
"""
Migration script to add is_system_seeded column to circle_movies table.
Run this once to update existing database.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from sqlalchemy import text, inspect

def migrate():
    app = create_app()
    with app.app_context():
        # Check if column already exists
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('circle_movies')]

        if 'is_system_seeded' in columns:
            print("Column 'is_system_seeded' already exists. Nothing to do.")
            return

        # Add the column
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE circle_movies ADD COLUMN is_system_seeded BOOLEAN DEFAULT FALSE'))
            conn.commit()
        print("Successfully added 'is_system_seeded' column to circle_movies table.")

        # Mark existing movies as system seeded (they were all from initial seeding)
        with db.engine.connect() as conn:
            conn.execute(text('UPDATE circle_movies SET is_system_seeded = TRUE'))
            conn.commit()
        print("Marked all existing circle_movies as system seeded.")

if __name__ == '__main__':
    migrate()
