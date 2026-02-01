"""
Tests for authentication routes and decorators.

Tests cover:
- User registration (including first user becomes site admin)
- User login
- JWT token validation
- Authorization decorators (@circle_required, @circle_admin_required, @site_admin_required)
- Password reset flow
"""
import pytest
from datetime import datetime, timedelta
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


class TestPasswordReset:
    """Tests for password reset flow"""

    def test_forgot_password_with_valid_email(self, client, create_user, app):
        """Should generate reset token for existing user"""
        user = create_user(email='test@example.com', password='oldpassword')

        response = client.post('/api/auth/forgot-password', json={
            'email': 'test@example.com'
        })

        assert response.status_code == 200
        # Response should be generic to prevent email enumeration
        assert 'reset link has been sent' in response.get_json()['message'].lower()

        # Verify token was created
        with app.app_context():
            db_user = User.query.filter_by(email='test@example.com').first()
            assert db_user.password_reset_token is not None
            assert db_user.password_reset_expires is not None
            assert db_user.password_reset_expires > datetime.utcnow()

    def test_forgot_password_with_invalid_email(self, client):
        """Should return success even for non-existent email (prevent enumeration)"""
        response = client.post('/api/auth/forgot-password', json={
            'email': 'nonexistent@example.com'
        })

        assert response.status_code == 200
        assert 'reset link has been sent' in response.get_json()['message'].lower()

    def test_forgot_password_missing_email(self, client):
        """Should fail without email"""
        response = client.post('/api/auth/forgot-password', json={})

        assert response.status_code == 400
        assert 'email required' in response.get_json()['error'].lower()

    def test_reset_password_with_valid_token(self, client, create_user, app):
        """Should successfully reset password with valid token"""
        user = create_user(email='test@example.com', password='oldpassword')

        # Generate token
        with app.app_context():
            db_user = User.query.filter_by(email='test@example.com').first()
            db_user.password_reset_token = 'valid-test-token'
            db_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

        response = client.post('/api/auth/reset-password', json={
            'token': 'valid-test-token',
            'new_password': 'newpassword123'
        })

        assert response.status_code == 200
        assert 'reset successfully' in response.get_json()['message'].lower()

        # Verify password was changed and token cleared
        with app.app_context():
            db_user = User.query.filter_by(email='test@example.com').first()
            assert db_user.check_password('newpassword123')
            assert db_user.password_reset_token is None
            assert db_user.password_reset_expires is None

    def test_reset_password_with_invalid_token(self, client):
        """Should fail with invalid token"""
        response = client.post('/api/auth/reset-password', json={
            'token': 'invalid-token',
            'new_password': 'newpassword123'
        })

        assert response.status_code == 400
        assert 'invalid' in response.get_json()['error'].lower()

    def test_reset_password_with_expired_token(self, client, create_user, app):
        """Should fail with expired token"""
        user = create_user(email='test@example.com', password='oldpassword')

        # Generate expired token
        with app.app_context():
            db_user = User.query.filter_by(email='test@example.com').first()
            db_user.password_reset_token = 'expired-token'
            db_user.password_reset_expires = datetime.utcnow() - timedelta(hours=1)
            db.session.commit()

        response = client.post('/api/auth/reset-password', json={
            'token': 'expired-token',
            'new_password': 'newpassword123'
        })

        assert response.status_code == 400
        assert 'expired' in response.get_json()['error'].lower()

    def test_reset_password_short_password(self, client, create_user, app):
        """Should fail with password less than 6 characters"""
        user = create_user(email='test@example.com', password='oldpassword')

        with app.app_context():
            db_user = User.query.filter_by(email='test@example.com').first()
            db_user.password_reset_token = 'valid-token'
            db_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

        response = client.post('/api/auth/reset-password', json={
            'token': 'valid-token',
            'new_password': '12345'
        })

        assert response.status_code == 400
        assert '6 characters' in response.get_json()['error']

    def test_verify_reset_token_valid(self, client, create_user, app):
        """Should confirm valid token"""
        user = create_user(email='test@example.com', password='oldpassword')

        with app.app_context():
            db_user = User.query.filter_by(email='test@example.com').first()
            db_user.password_reset_token = 'valid-token'
            db_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

        response = client.get('/api/auth/verify-reset-token/valid-token')

        assert response.status_code == 200
        assert response.get_json()['valid'] is True

    def test_verify_reset_token_invalid(self, client):
        """Should reject invalid token"""
        response = client.get('/api/auth/verify-reset-token/nonexistent-token')

        assert response.status_code == 400
        assert response.get_json()['valid'] is False

    def test_verify_reset_token_expired(self, client, create_user, app):
        """Should reject expired token"""
        user = create_user(email='test@example.com', password='oldpassword')

        with app.app_context():
            db_user = User.query.filter_by(email='test@example.com').first()
            db_user.password_reset_token = 'expired-token'
            db_user.password_reset_expires = datetime.utcnow() - timedelta(hours=1)
            db.session.commit()

        response = client.get('/api/auth/verify-reset-token/expired-token')

        assert response.status_code == 400
        assert response.get_json()['valid'] is False

    def test_login_works_after_password_reset(self, client, create_user, app):
        """Should be able to login with new password after reset"""
        user = create_user(email='test@example.com', password='oldpassword')

        # Set up token and reset password
        with app.app_context():
            db_user = User.query.filter_by(email='test@example.com').first()
            db_user.password_reset_token = 'test-token'
            db_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

        client.post('/api/auth/reset-password', json={
            'token': 'test-token',
            'new_password': 'brandnewpassword'
        })

        # Try to login with new password
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'brandnewpassword'
        })

        assert response.status_code == 200
        assert 'access_token' in response.get_json()

        # Old password should not work
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'oldpassword'
        })

        assert response.status_code == 401


class TestChangeEmail:
    """Tests for email change functionality"""

    def test_change_email_success(self, client, create_user, auth_headers, app):
        """Should successfully change email with correct password"""
        user = create_user(email='old@example.com', password='mypassword')
        headers = auth_headers(user['email'])

        response = client.post('/api/auth/change-email',
            headers=headers,
            json={
                'new_email': 'new@example.com',
                'password': 'mypassword'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['user']['email'] == 'new@example.com'

        # Verify in database
        with app.app_context():
            db_user = User.query.filter_by(email='new@example.com').first()
            assert db_user is not None
            old_user = User.query.filter_by(email='old@example.com').first()
            assert old_user is None

    def test_change_email_wrong_password(self, client, create_user, auth_headers):
        """Should fail with incorrect password"""
        user = create_user(email='test@example.com', password='correctpassword')
        headers = auth_headers(user['email'])

        response = client.post('/api/auth/change-email',
            headers=headers,
            json={
                'new_email': 'new@example.com',
                'password': 'wrongpassword'
            }
        )

        assert response.status_code == 403
        assert 'incorrect' in response.get_json()['error'].lower()

    def test_change_email_already_in_use(self, client, create_user, auth_headers):
        """Should fail if email is already taken"""
        create_user(email='existing@example.com', password='password1')
        user = create_user(email='test@example.com', password='password2')
        headers = auth_headers(user['email'])

        response = client.post('/api/auth/change-email',
            headers=headers,
            json={
                'new_email': 'existing@example.com',
                'password': 'password2'
            }
        )

        assert response.status_code == 400
        assert 'already in use' in response.get_json()['error'].lower()

    def test_change_email_same_email(self, client, create_user, auth_headers):
        """Should fail if new email is same as current"""
        user = create_user(email='test@example.com', password='mypassword')
        headers = auth_headers(user['email'])

        response = client.post('/api/auth/change-email',
            headers=headers,
            json={
                'new_email': 'test@example.com',
                'password': 'mypassword'
            }
        )

        assert response.status_code == 400
        assert 'same as current' in response.get_json()['error'].lower()

    def test_change_email_missing_fields(self, client, create_user, auth_headers):
        """Should fail without required fields"""
        user = create_user(email='test@example.com', password='mypassword')
        headers = auth_headers(user['email'])

        # Missing password
        response = client.post('/api/auth/change-email',
            headers=headers,
            json={'new_email': 'new@example.com'}
        )
        assert response.status_code == 400

        # Missing email
        response = client.post('/api/auth/change-email',
            headers=headers,
            json={'password': 'mypassword'}
        )
        assert response.status_code == 400

    def test_change_email_case_insensitive(self, client, create_user, auth_headers, app):
        """Should handle case-insensitive email check"""
        create_user(email='existing@example.com', password='password1')
        user = create_user(email='test@example.com', password='password2')
        headers = auth_headers(user['email'])

        response = client.post('/api/auth/change-email',
            headers=headers,
            json={
                'new_email': 'EXISTING@example.com',
                'password': 'password2'
            }
        )

        assert response.status_code == 400
        assert 'already in use' in response.get_json()['error'].lower()

    def test_login_works_with_new_email(self, client, create_user, auth_headers):
        """Should be able to login with new email after change"""
        user = create_user(email='old@example.com', password='mypassword')
        headers = auth_headers(user['email'])

        # Change email
        client.post('/api/auth/change-email',
            headers=headers,
            json={
                'new_email': 'new@example.com',
                'password': 'mypassword'
            }
        )

        # Login with new email
        response = client.post('/api/auth/login', json={
            'email': 'new@example.com',
            'password': 'mypassword'
        })
        assert response.status_code == 200

        # Old email should not work
        response = client.post('/api/auth/login', json={
            'email': 'old@example.com',
            'password': 'mypassword'
        })
        assert response.status_code == 401


class TestInvitationRedemption:
    """Tests for invitation redemption (/api/auth/invitations/redeem)"""

    def test_authenticated_user_redeems_invite_with_just_code(
        self, client, create_user, create_circle, create_circle_member, auth_headers, app
    ):
        """Logged-in user clicking invite link should join circle with just the code.

        Bug fix test: User 1 is logged in with their own circle A.
        User 2 sends them an invite to circle B.
        When User 1 clicks the invite link, they should join circle B
        even though they only send the code (no email/password).
        """
        from models import Invitation, CircleMember
        from datetime import datetime, timedelta

        # User 1 has their own circle
        user1 = create_user(email='user1@example.com', password='password1')
        circle_a = create_circle(name='Circle A', created_by_id=user1['id'])
        create_circle_member(circle_a['id'], user1['id'], role='admin')

        # User 2 has Circle B and creates an invite
        user2 = create_user(email='user2@example.com', password='password2')
        circle_b = create_circle(name='Circle B', created_by_id=user2['id'])
        create_circle_member(circle_b['id'], user2['id'], role='admin')

        # Create invitation for Circle B
        with app.app_context():
            invitation = Invitation(
                circle_id=circle_b['id'],
                code='TESTCODE',
                created_by_id=user2['id'],
                expires_at=datetime.utcnow() + timedelta(days=30),
                is_active=True
            )
            from models import db
            db.session.add(invitation)
            db.session.commit()

        # User 1 is authenticated and redeems invite with ONLY the code
        headers = auth_headers(user1['email'])
        response = client.post(
            '/api/auth/invitations/redeem',
            headers=headers,
            json={'code': 'TESTCODE'}  # No email or password!
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['circle']['name'] == 'Circle B'
        assert data['user']['email'] == 'user1@example.com'

        # Verify user1 is now a member of Circle B
        with app.app_context():
            membership = CircleMember.query.filter_by(
                circle_id=circle_b['id'],
                user_id=user1['id']
            ).first()
            assert membership is not None
            assert membership.role == 'member'

    def test_existing_user_redeems_invite_with_email_password(
        self, client, create_user, create_circle, create_circle_member, app
    ):
        """Existing user not logged in can redeem invite with email/password.

        User logs out, then clicks invite link and enters email/password.
        """
        from models import Invitation, CircleMember
        from datetime import datetime, timedelta

        # Existing user
        user = create_user(email='existing@example.com', password='mypassword')

        # Another user's circle with invite
        other_user = create_user(email='other@example.com', password='password2')
        circle = create_circle(name='Other Circle', created_by_id=other_user['id'])
        create_circle_member(circle['id'], other_user['id'], role='admin')

        with app.app_context():
            invitation = Invitation(
                circle_id=circle['id'],
                code='INVITE123',
                created_by_id=other_user['id'],
                expires_at=datetime.utcnow() + timedelta(days=30),
                is_active=True
            )
            from models import db
            db.session.add(invitation)
            db.session.commit()

        # User redeems invite with email and password (not logged in)
        response = client.post(
            '/api/auth/invitations/redeem',
            json={
                'code': 'INVITE123',
                'email': 'existing@example.com',
                'password': 'mypassword'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['circle']['name'] == 'Other Circle'
        assert 'access_token' in data

        # Verify membership
        with app.app_context():
            membership = CircleMember.query.filter_by(
                circle_id=circle['id'],
                user_id=user['id']
            ).first()
            assert membership is not None
