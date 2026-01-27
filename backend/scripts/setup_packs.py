#!/usr/bin/env python3
"""
Setup script for Movie Packs feature.
Run this once to:
1. Create new database tables (movie_packs, movie_pack_cache, tmdb_api_usage)
2. Add new columns to circle_movies table
3. Seed pack definitions

Usage:
    cd backend
    source ./venv/bin/activate
    python scripts/setup_packs.py
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from models import db
from services.pack_service import seed_pack_definitions

def main():
    app = create_app()

    with app.app_context():
        print("Creating new database tables...")
        db.create_all()
        print("Tables created successfully!")

        print("\nSeeding pack definitions...")
        seed_pack_definitions()
        print("Pack definitions seeded!")

        # Show summary
        from models import MoviePack
        packs = MoviePack.query.all()
        print(f"\n{len(packs)} packs available:")
        for pack in packs:
            print(f"  - {pack.icon} {pack.name} ({pack.pack_type}/{pack.category})")

        print("\nSetup complete! You can now use the Movie Packs feature.")
        print("To populate pack caches, either:")
        print("  1. Access a pack via the API (auto-refreshes if stale)")
        print("  2. Call POST /api/packs/<pack_id>/refresh as site admin")

if __name__ == '__main__':
    main()
