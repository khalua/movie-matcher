"""
Tests for circle management routes.

Tests cover:
- Circle creation
- Circle membership
- Invitations
"""
import pytest
from models import db, Circle, CircleMember, Invitation


class TestCircleCreation:
    """Tests for circle creation"""

    def test_create_circle_success(self, client, create_user, auth_headers):
        """Should create a circle and make user admin"""
        user = create_user(email='creator@example.com')
        headers = auth_headers(user['email'])

        response = client.post(
            '/api/circles',
            headers=headers,
            json={'name': 'My New Circle'}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['name'] == 'My New Circle'
        assert data['role'] == 'admin'

    def test_create_circle_missing_name(self, client, create_user, auth_headers):
        """Should fail without circle name"""
        user = create_user(email='creator@example.com')
        headers = auth_headers(user['email'])

        response = client.post(
            '/api/circles',
            headers=headers,
            json={}
        )

        assert response.status_code == 400


class TestCircleListing:
    """Tests for listing user's circles"""

    def test_list_circles_returns_user_circles(self, client, authenticated_user):
        """Should return circles user is member of"""
        setup = authenticated_user(circle_name='Circle One')

        response = client.get(
            '/api/circles',
            headers=setup['headers']
        )

        assert response.status_code == 200
        circles = response.get_json()
        assert len(circles) == 1
        assert circles[0]['name'] == 'Circle One'

    def test_list_circles_excludes_other_circles(
        self, client, create_user, create_circle, create_circle_member, auth_headers
    ):
        """Should not return circles user is not in"""
        user = create_user(email='user@example.com')
        other_user = create_user(email='other@example.com')

        # User's circle
        my_circle = create_circle(name='My Circle', created_by_id=user['id'])
        create_circle_member(my_circle['id'], user['id'], role='admin')

        # Other user's circle
        other_circle = create_circle(name='Other Circle', created_by_id=other_user['id'])
        create_circle_member(other_circle['id'], other_user['id'], role='admin')

        headers = auth_headers(user['email'])
        response = client.get('/api/circles', headers=headers)

        circles = response.get_json()
        circle_names = [c['name'] for c in circles]
        assert 'My Circle' in circle_names
        assert 'Other Circle' not in circle_names


class TestCircleInvitations:
    """Tests for circle invitation system"""

    def test_create_invitation_as_admin(self, client, authenticated_user):
        """Circle admin should be able to create invitations"""
        setup = authenticated_user(is_admin=True)

        response = client.post(
            f'/api/circles/{setup["circle"]["id"]}/invitations',
            headers=setup['headers'],
            json={'uses': 5}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'code' in data
        assert 'invite_url' in data
        assert 'expires_at' in data

    def test_create_invitation_as_member_fails(self, client, authenticated_user):
        """Regular member should not create invitations"""
        setup = authenticated_user(is_admin=False)

        response = client.post(
            f'/api/circles/{setup["circle"]["id"]}/invitations',
            headers=setup['headers'],
            json={'uses': 5}
        )

        assert response.status_code == 403

    def test_list_invitations(self, client, authenticated_user, app):
        """Should list active invitations for circle"""
        setup = authenticated_user(is_admin=True)

        # Create an invitation
        client.post(
            f'/api/circles/{setup["circle"]["id"]}/invitations',
            headers=setup['headers'],
            json={'uses': 10}
        )

        response = client.get(
            f'/api/circles/{setup["circle"]["id"]}/invitations',
            headers=setup['headers']
        )

        assert response.status_code == 200
        invitations = response.get_json()
        assert len(invitations) == 1

    def test_create_invitation_for_different_circle_than_header(
        self, client, create_user, create_circle, create_circle_member, auth_headers
    ):
        """Should generate invite for URL circle, not header circle.

        Bug fix test: When user is admin of Circle A and B, viewing Circle A,
        but generating invite for Circle B via dropdown, the invite message
        should reference Circle B, not Circle A.
        """
        user = create_user(email='admin@example.com')

        # Create two circles where user is admin
        circle_a = create_circle(name='Circle Alpha', created_by_id=user['id'])
        circle_b = create_circle(name='Circle Beta', created_by_id=user['id'])
        create_circle_member(circle_a['id'], user['id'], role='admin')
        create_circle_member(circle_b['id'], user['id'], role='admin')

        # Headers point to Circle A (the "current" circle in UI)
        headers = auth_headers(user['email'])
        headers['X-Circle-Id'] = str(circle_a['id'])

        # But we're generating invite for Circle B via URL path
        response = client.post(
            f'/api/circles/{circle_b["id"]}/invitations',
            headers=headers,
            json={}
        )

        assert response.status_code == 201
        data = response.get_json()

        # The email_body should reference Circle B, not Circle A
        assert 'Circle Beta' in data['email_body']
        assert 'Circle Alpha' not in data['email_body']

        # Verify the invitation was created for Circle B
        invitation = Invitation.query.filter_by(code=data['code']).first()
        assert invitation.circle_id == circle_b['id']


class TestCircleMembers:
    """Tests for circle member management"""

    def test_list_circle_members(self, client, authenticated_user):
        """Should list all members in circle"""
        setup = authenticated_user(is_admin=True)

        response = client.get(
            f'/api/circles/{setup["circle"]["id"]}/members',
            headers=setup['headers']
        )

        assert response.status_code == 200
        members = response.get_json()
        assert len(members) == 1
        assert members[0]['email'] == setup['user']['email']

    def test_member_count_in_circle_info(
        self, client, create_user, create_circle, create_circle_member, auth_headers
    ):
        """Circle info should include accurate member count"""
        user1 = create_user(email='user1@example.com')
        user2 = create_user(email='user2@example.com')

        circle = create_circle(name='Two Members', created_by_id=user1['id'])
        create_circle_member(circle['id'], user1['id'], role='admin')
        create_circle_member(circle['id'], user2['id'], role='member')

        headers = auth_headers(user1['email'])
        response = client.get('/api/circles', headers=headers)

        circles = response.get_json()
        assert circles[0]['member_count'] == 2
