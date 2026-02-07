"""
Create test seed data with multiple users and circles
Run this after setting up PostgreSQL database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, Circle, CircleMember


def create_test_data():
    """Create test users and circles"""
    app = create_app()

    with app.app_context():
        print("Creating test data...")

        # Create test users
        users_data = [
            ('tony@example.com', 'Tony', 'password', True),
            ('alice@example.com', 'Alice', 'password', False),
            ('bob@example.com', 'Bob', 'password', False),
            ('charlie@example.com', 'Charlie', 'password', False),
        ]

        users = {}
        for email, display_name, password, is_admin in users_data:
            # Check if user already exists
            existing = User.query.filter_by(email=email).first()
            if existing:
                users[display_name] = existing
                print(f"User {email} already exists, skipping")
                continue

            user = User(
                email=email,
                display_name=display_name,
                is_site_admin=is_admin
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            users[display_name] = user
            print(f"Created user: {email}")

        db.session.commit()
        print(f"Total users: {len(users)}")

        # Create test circles
        circles_data = [
            ('Family Movie Night', users['Tony'], ['Tony', 'Alice']),
            ('Work Friends', users['Tony'], ['Tony', 'Bob', 'Charlie']),
            ('Classic Films Club', users['Alice'], ['Alice', 'Bob']),
        ]

        for circle_name, creator, member_names in circles_data:
            # Check if circle already exists
            existing = Circle.query.filter_by(name=circle_name).first()
            if existing:
                print(f"Circle '{circle_name}' already exists, skipping")
                continue

            circle = Circle(
                name=circle_name,
                created_by_id=creator.id
            )
            db.session.add(circle)
            db.session.flush()

            # Add members
            for name in member_names:
                member = CircleMember(
                    circle_id=circle.id,
                    user_id=users[name].id,
                    role='admin' if users[name].id == creator.id else 'member'
                )
                db.session.add(member)

            print(f"Created circle: {circle_name}")

        db.session.commit()
        print("\n✓ Test data created successfully!")
        print("\nTest Accounts:")
        print("  tony@example.com / password (Site Admin)")
        print("  alice@example.com / password")
        print("  bob@example.com / password")
        print("  charlie@example.com / password")


if __name__ == '__main__':
    create_test_data()
