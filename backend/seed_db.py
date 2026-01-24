#!/usr/bin/env python3
"""
Database seed script for Movie Matcher.
Resets the database and creates initial users, circles, and movies.

Usage:
    cd backend
    source ./venv/bin/activate
    python seed_db.py              # Seed database (uses snapshot if available)
    python seed_db.py --snapshot   # Create snapshot of current movies first
"""

import json
import os
import sys
from app import create_app
from models import db, User, Circle, CircleMember, Movie, CircleMovie, UserSwipe, MatchEvent, UserMatchSeen

SNAPSHOT_FILE = os.path.join(os.path.dirname(__file__), 'misc/movie_snapshot.json')


def create_movie_snapshot():
    """Create a snapshot of all movies currently in the database."""
    app = create_app()

    with app.app_context():
        movies = Movie.query.all()

        if not movies:
            print("No movies in database to snapshot!")
            return False

        snapshot = []
        for movie in movies:
            snapshot.append({
                'title': movie.title,
                'year': movie.year,
                'poster': movie.poster,
                'description': movie.description,
                'genre': movie.genre,
                'rating': movie.rating,
                'length': movie.length,
                'starring': movie.starring
            })

        with open(SNAPSHOT_FILE, 'w') as f:
            json.dump(snapshot, f, indent=2)

        print(f"Created snapshot with {len(snapshot)} movies at {SNAPSHOT_FILE}")
        return True


def load_movie_snapshot():
    """Load movies from snapshot file."""
    if not os.path.exists(SNAPSHOT_FILE):
        return None

    with open(SNAPSHOT_FILE, 'r') as f:
        return json.load(f)


def seed_database():
    app = create_app()

    with app.app_context():
        # Load movie snapshot before dropping tables
        movie_snapshot = load_movie_snapshot()

        if not movie_snapshot:
            print("WARNING: No movie snapshot found at", SNAPSHOT_FILE)
            print("Run 'python seed_db.py --snapshot' first to save current movies,")
            print("or seed will continue without movies.")
            response = input("Continue without movies? (y/n): ")
            if response.lower() != 'y':
                print("Aborted.")
                return

        print("Dropping all tables...")
        db.drop_all()

        print("Creating all tables...")
        db.create_all()

        # Default password for all users
        DEFAULT_PASSWORD = 'abc123'

        # --- Create Users ---
        print("\nCreating users...")

        # Super admin
        admin = User(
            email='admin@test.com',
            display_name='Admin',
            is_site_admin=True
        )
        admin.set_password(DEFAULT_PASSWORD)
        db.session.add(admin)

        # Tony (circle admin for both circles)
        tony = User(
            email='tony@test.com',
            display_name='Tony'
        )
        tony.set_password(DEFAULT_PASSWORD)
        db.session.add(tony)

        # Circle 1 members (Gabagool Party Boys)
        nick = User(
            email='nick@test.com',
            display_name='Nick'
        )
        nick.set_password(DEFAULT_PASSWORD)
        db.session.add(nick)

        tal = User(
            email='tal@test.com',
            display_name='Tal'
        )
        tal.set_password(DEFAULT_PASSWORD)
        db.session.add(tal)

        # Circle 2 members (Family Circle)
        lulu = User(
            email='lulu@test.com',
            display_name='Lulu'
        )
        lulu.set_password(DEFAULT_PASSWORD)
        db.session.add(lulu)

        olivia = User(
            email='olivia@test.com',
            display_name='Olivia'
        )
        olivia.set_password(DEFAULT_PASSWORD)
        db.session.add(olivia)

        # Commit users first to get IDs
        db.session.commit()
        print(f"  Created {User.query.count()} users")

        # --- Create Circles ---
        print("\nCreating circles...")

        # Circle 1: Gabagool Party Boys
        gabagool = Circle(
            name='Gabagool Party Boys',
            created_by_id=tony.id
        )
        db.session.add(gabagool)

        # Circle 2: Family Circle
        family = Circle(
            name='Family Circle',
            created_by_id=tony.id
        )
        db.session.add(family)

        # Commit circles to get IDs
        db.session.commit()
        print(f"  Created {Circle.query.count()} circles")

        # --- Add Members to Circles ---
        print("\nAdding members to circles...")

        # Gabagool Party Boys members
        db.session.add(CircleMember(circle_id=gabagool.id, user_id=tony.id, role='admin'))
        db.session.add(CircleMember(circle_id=gabagool.id, user_id=nick.id, role='member'))
        db.session.add(CircleMember(circle_id=gabagool.id, user_id=tal.id, role='member'))

        # Family Circle members
        db.session.add(CircleMember(circle_id=family.id, user_id=tony.id, role='admin'))
        db.session.add(CircleMember(circle_id=family.id, user_id=lulu.id, role='member'))
        db.session.add(CircleMember(circle_id=family.id, user_id=olivia.id, role='member'))

        db.session.commit()
        print(f"  Added {CircleMember.query.count()} memberships")

        # --- Add Movies from Snapshot ---
        if movie_snapshot:
            print(f"\nLoading {len(movie_snapshot)} movies from snapshot...")

            for movie_data in movie_snapshot:
                movie = Movie(
                    title=movie_data['title'],
                    year=movie_data['year'],
                    poster=movie_data['poster'],
                    description=movie_data['description'],
                    genre=movie_data['genre'],
                    rating=movie_data['rating'],
                    length=movie_data['length'],
                    starring=movie_data['starring'],
                    added_by_id=admin.id
                )
                db.session.add(movie)

            db.session.commit()
            print(f"  Created {Movie.query.count()} movies")

            # --- Add All Movies to Both Circles ---
            print("\nAdding movies to circles...")

            all_movies = Movie.query.all()
            for circle in [gabagool, family]:
                for movie in all_movies:
                    circle_movie = CircleMovie(
                        circle_id=circle.id,
                        movie_id=movie.id,
                        added_by_id=admin.id
                    )
                    db.session.add(circle_movie)

            db.session.commit()
            print(f"  Added {CircleMovie.query.count()} circle-movie associations")
        else:
            print("\nNo movies loaded (no snapshot available)")

        # --- Summary ---
        print("\n" + "="*50)
        print("DATABASE SEEDED SUCCESSFULLY")
        print("="*50)
        print(f"\nAll passwords: {DEFAULT_PASSWORD}")
        print("\nUsers:")
        for user in User.query.all():
            admin_flag = " (SITE ADMIN)" if user.is_site_admin else ""
            print(f"  - {user.email}{admin_flag}")

        print("\nCircles:")
        for circle in Circle.query.all():
            movie_count = CircleMovie.query.filter_by(circle_id=circle.id).count()
            print(f"\n  {circle.name} ({movie_count} movies):")
            for member in circle.members:
                role_flag = f" ({member.role})" if member.role == 'admin' else ""
                print(f"    - {member.user.email}{role_flag}")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--snapshot':
        create_movie_snapshot()
    else:
        seed_database()
