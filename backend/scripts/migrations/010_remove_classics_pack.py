#!/usr/bin/env python3
"""Migration 010: Remove 'Top 100 Classics' pack (duplicative with AFI Top 100).

Movies already added to circles are preserved — only the pack attribution is cleared.
Swipe data, matches, and comments are unaffected.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import text, inspect


def migrate():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Find the pack ID
            row = conn.execute(text(
                "SELECT id FROM movie_packs WHERE slug = 'classics'"
            )).fetchone()

            if not row:
                print("Classics pack not found, nothing to do")
                return

            pack_id = row[0]
            print(f"Found classics pack with id={pack_id}")

            # 1. Clear pack attribution on circle_movies (movies stay in circles)
            updated = conn.execute(text("""
                UPDATE circle_movies
                SET source_pack_id = NULL, source_pack_name = NULL
                WHERE source_pack_id = :pack_id
            """), {'pack_id': pack_id}).rowcount
            print(f"Cleared pack attribution on {updated} circle_movies")

            # 2. Delete circle_pack_installs for this pack
            deleted_installs = conn.execute(text(
                "DELETE FROM circle_pack_installs WHERE pack_id = :pack_id"
            ), {'pack_id': pack_id}).rowcount
            print(f"Deleted {deleted_installs} circle_pack_installs")

            # 3. Delete movie_pack_cache entries
            deleted_cache = conn.execute(text(
                "DELETE FROM movie_pack_cache WHERE pack_id = :pack_id"
            ), {'pack_id': pack_id}).rowcount
            print(f"Deleted {deleted_cache} movie_pack_cache entries")

            # 4. Delete the pack itself
            conn.execute(text(
                "DELETE FROM movie_packs WHERE id = :pack_id"
            ), {'pack_id': pack_id})
            print("Deleted classics pack")

            conn.commit()
            print("Migration 010 complete")


if __name__ == '__main__':
    migrate()
