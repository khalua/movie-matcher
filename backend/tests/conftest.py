"""
Pytest configuration and fixtures for backend tests.

This module provides:
- Test Flask app with SQLite in-memory database
- Database session management with automatic rollback
- Authentication helpers for testing protected endpoints
- Factory fixtures for creating test data
"""
import pytest
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Circle, CircleMember, Movie, CircleMovie, UserSwipe, Invitation
from flask_jwt_extended import create_access_token
from datetime import datetime, timedelta


class TestConfig:
    """Test configuration using SQLite in-memory database"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'test-secret-key-for-testing-only'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    OMDB_API_KEY = 'test-api-key'
    TMDB_API_KEY = 'test-tmdb-key'
    CORS_ORIGINS = ['*']


@pytest.fixture(scope='function')
def app():
    """Create test Flask application"""
    # Override config loading to use test config
    test_app = create_app('testing')
    test_app.config.from_object(TestConfig)

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Provide database session for tests"""
    with app.app_context():
        yield db.session


# =============================================================================
# Factory Fixtures - Create test data
# =============================================================================

@pytest.fixture
def create_user(app):
    """Factory fixture to create test users"""
    def _create_user(
        email='test@example.com',
        password='testpassword123',
        display_name='Test User',
        is_site_admin=False
    ):
        with app.app_context():
            user = User(
                email=email,
                display_name=display_name,
                is_site_admin=is_site_admin
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            # Return a dict with user data since the session will close
            return {
                'id': user.id,
                'email': user.email,
                'display_name': user.display_name,
                'is_site_admin': user.is_site_admin,
                'password': password  # Keep plain password for login tests
            }
    return _create_user


@pytest.fixture
def create_circle(app):
    """Factory fixture to create test circles"""
    def _create_circle(name='Test Circle', created_by_id=None):
        with app.app_context():
            circle = Circle(
                name=name,
                created_by_id=created_by_id,
                is_active=True
            )
            db.session.add(circle)
            db.session.commit()
            return {
                'id': circle.id,
                'name': circle.name,
                'created_by_id': circle.created_by_id
            }
    return _create_circle


@pytest.fixture
def create_circle_member(app):
    """Factory fixture to add users to circles"""
    def _create_circle_member(circle_id, user_id, role='member'):
        with app.app_context():
            member = CircleMember(
                circle_id=circle_id,
                user_id=user_id,
                role=role
            )
            db.session.add(member)
            db.session.commit()
            return {
                'id': member.id,
                'circle_id': circle_id,
                'user_id': user_id,
                'role': role
            }
    return _create_circle_member


@pytest.fixture
def create_movie(app):
    """Factory fixture to create test movies"""
    def _create_movie(
        title='Test Movie',
        year=2024,
        poster='http://example.com/poster.jpg',
        description='A test movie description',
        genre='Action',
        rating='8.5',
        length='120 min',
        starring='Test Actor',
        added_by_id=None
    ):
        with app.app_context():
            movie = Movie(
                title=title,
                year=year,
                poster=poster,
                description=description,
                genre=genre,
                rating=rating,
                length=length,
                starring=starring,
                added_by_id=added_by_id
            )
            db.session.add(movie)
            db.session.commit()
            return {
                'id': movie.id,
                'title': movie.title,
                'year': movie.year
            }
    return _create_movie


@pytest.fixture
def add_movie_to_circle(app):
    """Factory fixture to associate movies with circles"""
    def _add_movie_to_circle(circle_id, movie_id, added_by_id):
        with app.app_context():
            circle_movie = CircleMovie(
                circle_id=circle_id,
                movie_id=movie_id,
                added_by_id=added_by_id
            )
            db.session.add(circle_movie)
            db.session.commit()
            return {
                'id': circle_movie.id,
                'circle_id': circle_id,
                'movie_id': movie_id
            }
    return _add_movie_to_circle


@pytest.fixture
def create_swipe(app):
    """Factory fixture to create user swipes"""
    def _create_swipe(user_id, movie_id, circle_id, action='like'):
        with app.app_context():
            swipe = UserSwipe(
                user_id=user_id,
                movie_id=movie_id,
                circle_id=circle_id,
                action=action
            )
            db.session.add(swipe)
            db.session.commit()
            return {
                'id': swipe.id,
                'user_id': user_id,
                'movie_id': movie_id,
                'action': action
            }
    return _create_swipe


# =============================================================================
# Authentication Helpers
# =============================================================================

@pytest.fixture
def auth_headers(app):
    """Generate JWT auth headers for a user"""
    def _auth_headers(user_email, circle_id=None):
        with app.app_context():
            token = create_access_token(identity=user_email)
            headers = {'Authorization': f'Bearer {token}'}
            if circle_id:
                headers['X-Circle-Id'] = str(circle_id)
            return headers
    return _auth_headers


@pytest.fixture
def authenticated_user(create_user, create_circle, create_circle_member, auth_headers):
    """
    Create a complete authenticated user setup with circle membership.
    Returns dict with user data, circle data, and auth headers.
    """
    def _authenticated_user(
        email='user@example.com',
        is_admin=False,
        is_site_admin=False,
        circle_name='Test Circle'
    ):
        user = create_user(
            email=email,
            display_name='Test User',
            is_site_admin=is_site_admin
        )
        circle = create_circle(name=circle_name, created_by_id=user['id'])
        create_circle_member(
            circle_id=circle['id'],
            user_id=user['id'],
            role='admin' if is_admin else 'member'
        )
        headers = auth_headers(user['email'], circle['id'])

        return {
            'user': user,
            'circle': circle,
            'headers': headers
        }
    return _authenticated_user


# =============================================================================
# Common Test Data Setups
# =============================================================================

@pytest.fixture
def setup_match_scenario(
    create_user, create_circle, create_circle_member,
    create_movie, add_movie_to_circle, create_swipe
):
    """
    Create a scenario for testing match detection:
    - 3 users in a circle
    - 2 movies in the circle
    - Returns data dict with all IDs
    """
    def _setup():
        # Create users
        user1 = create_user(email='user1@example.com', display_name='User One')
        user2 = create_user(email='user2@example.com', display_name='User Two')
        user3 = create_user(email='user3@example.com', display_name='User Three')

        # Create circle
        circle = create_circle(name='Match Test Circle', created_by_id=user1['id'])

        # Add all users to circle
        create_circle_member(circle['id'], user1['id'], role='admin')
        create_circle_member(circle['id'], user2['id'], role='member')
        create_circle_member(circle['id'], user3['id'], role='member')

        # Create movies
        movie1 = create_movie(title='Movie One', year=2024)
        movie2 = create_movie(title='Movie Two', year=2023)

        # Add movies to circle
        add_movie_to_circle(circle['id'], movie1['id'], user1['id'])
        add_movie_to_circle(circle['id'], movie2['id'], user1['id'])

        return {
            'users': [user1, user2, user3],
            'circle': circle,
            'movies': [movie1, movie2]
        }
    return _setup
