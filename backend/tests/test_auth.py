"""
Tests for authentication routes and decorators.

Tests cover:
- User registration (including first user becomes site admin)
- User login
- JWT token validation
- Authorization decorators (@circle_required, @circle_admin_required, @site_admin_required)
"""
import pytest
from models import db, User, Circle, CircleMember


class TestRegistration:
    """Tests for /api/auth/register endpoint"""

    def test_register_first_user_becomes_site_admin(self, client, app):
        """First user to register should become site admin"""
        response = client.post('/api/auth/register', json={
            'email': 'first@example.com',
            'password': 'password123',
            'display_name': 'First User'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert 'access_token' in data
        assert data['user']['is_site_admin'] is True

    def test_register_second_user_not_site_admin(self, client, create_user):
        """Subsequent users should not be site admins"""
        # Create first user
        create_user(email='first@example.com', is_site_admin=True)

        response = client.post('/api/auth/register', json={
            'email': 'second@example.com',
            'password': 'password123',
            'display_name': 'Second User'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['user']['is_site_admin'] is False

    def test_register_duplicate_email_fails(self, client, create_user):
        """Registration with existing email should fail"""
        create_user(email='existing@example.com')

        response = client.post('/api/auth/register', json={
            'email': 'existing@example.com',
            'password': 'password123',
            'display_name': 'Duplicate'
        })

        assert response.status_code == 400
        assert 'already registered' in response.get_json()['error'].lower()

    def test_register_missing_email(self, client):
        """Registration without email should fail"""
        response = client.post('/api/auth/register', json={
            'password': 'password123',
            'display_name': 'No Email'
        })

        assert response.status_code == 400

    def test_register_missing_password(self, client):
        """Registration without password should fail"""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'display_name': 'No Password'
        })

        assert response.status_code == 400


class TestLogin:
    """Tests for /api/auth/login endpoint"""

    def test_login_success(self, client, create_user):
        """Valid credentials should return JWT token"""
        user = create_user(email='test@example.com', password='mypassword')

        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'mypassword'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['user']['email'] == 'test@example.com'

    def test_login_wrong_password(self, client, create_user):
        """Wrong password should fail"""
        create_user(email='test@example.com', password='correctpassword')

        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Login with nonexistent email should fail"""
        response = client.post('/api/auth/login', json={
            'email': 'nobody@example.com',
            'password': 'anypassword'
        })

        assert response.status_code == 401

    def test_login_returns_user_circles(self, client, authenticated_user):
        """Login should return user's circles"""
        setup = authenticated_user(email='test@example.com', is_admin=True)

        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'testpassword123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'circles' in data
        assert len(data['circles']) == 1


class TestCircleRequiredDecorator:
    """Tests for @circle_required decorator"""

    def test_missing_circle_header_returns_400(self, client, create_user, auth_headers):
        """Request without X-Circle-Id header should fail"""
        user = create_user(email='test@example.com')
        headers = auth_headers(user['email'])  # No circle_id

        response = client.get('/api/movies/random', headers=headers)

        assert response.status_code == 400
        assert 'X-Circle-Id' in response.get_json()['error']

    def test_invalid_circle_id_returns_400(self, client, create_user, auth_headers):
        """Non-numeric circle ID should fail"""
        user = create_user(email='test@example.com')
        headers = auth_headers(user['email'])
        headers['X-Circle-Id'] = 'not-a-number'

        response = client.get('/api/movies/random', headers=headers)

        assert response.status_code == 400

    def test_nonexistent_circle_returns_404(self, client, create_user, auth_headers):
        """Request with nonexistent circle ID should fail"""
        user = create_user(email='test@example.com')
        headers = auth_headers(user['email'])
        headers['X-Circle-Id'] = '99999'

        response = client.get('/api/movies/random', headers=headers)

        assert response.status_code == 404

    def test_non_member_returns_403(self, client, create_user, create_circle, auth_headers):
        """User not in circle should be forbidden"""
        user = create_user(email='outsider@example.com')
        other_user = create_user(email='owner@example.com')
        circle = create_circle(name='Private Circle', created_by_id=other_user['id'])

        headers = auth_headers(user['email'], circle['id'])

        response = client.get('/api/movies/random', headers=headers)

        assert response.status_code == 403
        assert 'Not a member' in response.get_json()['error']

    def test_site_admin_can_access_any_circle(
        self, client, create_user, create_circle, create_circle_member,
        create_movie, add_movie_to_circle, auth_headers
    ):
        """Site admin should access circles they're not members of"""
        site_admin = create_user(
            email='admin@example.com',
            is_site_admin=True
        )
        regular_user = create_user(email='regular@example.com')
        circle = create_circle(name='User Circle', created_by_id=regular_user['id'])
        create_circle_member(circle['id'], regular_user['id'], role='admin')

        # Add a movie so /random has something to return
        movie = create_movie(title='Test Movie')
        add_movie_to_circle(circle['id'], movie['id'], regular_user['id'])

        headers = auth_headers(site_admin['email'], circle['id'])

        response = client.get('/api/movies/random', headers=headers)

        # Site admin can access even though not a member
        assert response.status_code == 200


class TestCircleAdminRequiredDecorator:
    """Tests for @circle_admin_required decorator"""

    def test_circle_member_cannot_access_admin_routes(
        self, client, authenticated_user
    ):
        """Regular member should not access admin-only circle routes"""
        setup = authenticated_user(email='member@example.com', is_admin=False)

        # Try to create an invitation (admin only)
        response = client.post(
            f'/api/circles/{setup["circle"]["id"]}/invitations',
            headers=setup['headers'],
            json={'uses': 5}
        )

        assert response.status_code == 403

    def test_circle_admin_can_access_admin_routes(
        self, client, authenticated_user
    ):
        """Circle admin should access admin routes"""
        setup = authenticated_user(email='admin@example.com', is_admin=True)

        response = client.post(
            f'/api/circles/{setup["circle"]["id"]}/invitations',
            headers=setup['headers'],
            json={'uses': 5}
        )

        assert response.status_code == 201


class TestSiteAdminRequiredDecorator:
    """Tests for @site_admin_required decorator"""

    def test_regular_user_cannot_access_site_admin_routes(
        self, client, authenticated_user
    ):
        """Regular user should not access site admin routes"""
        setup = authenticated_user(email='user@example.com', is_site_admin=False)

        response = client.get(
            '/api/admin/analytics',
            headers=setup['headers']
        )

        assert response.status_code == 403

    def test_site_admin_can_access_site_admin_routes(
        self, client, authenticated_user
    ):
        """Site admin should access site admin routes"""
        setup = authenticated_user(
            email='siteadmin@example.com',
            is_site_admin=True
        )

        response = client.get(
            '/api/admin/analytics',
            headers=setup['headers']
        )

        assert response.status_code == 200
