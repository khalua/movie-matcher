#!/usr/bin/env python3
"""
Migration 001: Add Movie Packs feature

New tables:
- movie_packs: Pack definitions (curated collections)
- movie_pack_cache: Cached movies in each pack
- tmdb_api_usage: Track TMDB API usage for rate limiting

New columns on circle_movies:
- source_pack_id: FK to movie_packs
- source_pack_name: Denormalized pack name for display
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import text, inspect


def check_table_exists(inspector, table_name):
    """Check if a table exists in the database"""
    return table_name in inspector.get_table_names()


def check_column_exists(inspector, table_name, column_name):
    """Check if a column exists in a table"""
    if not check_table_exists(inspector, table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # 1. Create new tables (db.create_all handles this safely)
        print("Creating any missing tables...")
        db.create_all()
        print("Tables created/verified.")

        # 2. Add display_order column to movie_packs if missing
        if check_table_exists(inspector, 'movie_packs') and not check_column_exists(inspector, 'movie_packs', 'display_order'):
            print("Adding 'display_order' column to movie_packs...")
            with db.engine.connect() as conn:
                conn.execute(text(
                    'ALTER TABLE movie_packs ADD COLUMN display_order INTEGER DEFAULT 100'
                ))
                conn.commit()
            print("Added 'display_order' column.")

        # 3. Add source_pack_id column to circle_movies if missing
        if not check_column_exists(inspector, 'circle_movies', 'source_pack_id'):
            print("Adding 'source_pack_id' column to circle_movies...")
            with db.engine.connect() as conn:
                conn.execute(text(
                    'ALTER TABLE circle_movies ADD COLUMN source_pack_id INTEGER REFERENCES movie_packs(id)'
                ))
                conn.commit()
            print("Added 'source_pack_id' column.")
        else:
            print("Column 'source_pack_id' already exists.")

        # 4. Add source_pack_name column to circle_movies if missing
        if not check_column_exists(inspector, 'circle_movies', 'source_pack_name'):
            print("Adding 'source_pack_name' column to circle_movies...")
            with db.engine.connect() as conn:
                conn.execute(text(
                    'ALTER TABLE circle_movies ADD COLUMN source_pack_name VARCHAR(100)'
                ))
                conn.commit()
            print("Added 'source_pack_name' column.")
        else:
            print("Column 'source_pack_name' already exists.")

        # 5. Seed pack definitions if table is empty
        from models import MoviePack
        if MoviePack.query.count() == 0:
            print("Seeding pack definitions...")
            from services.pack_service import seed_pack_definitions
            seed_pack_definitions()
            print("Pack definitions seeded.")
        else:
            print("Pack definitions already exist.")

        print("Migration 001 complete!")


if __name__ == '__main__':
    migrate()
