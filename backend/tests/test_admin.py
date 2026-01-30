"""
Tests for admin endpoints (site admin only).

Tests cover:
- User management (list, delete)
- Circle management (delete)
- Authorization checks
"""
import pytest
from models import db, User, Circle, CircleMember, UserSwipe, MovieComment


class TestAdminUserManagement:
    """Tests for admin user management endpoints"""

    def test_list_users_requires_site_admin(self, client, authenticated_user):
        """Non-site-admin cannot list users"""
        setup = authenticated_user(email='regular@example.com', is_site_admin=False)
        response = client.get('/api/admin/users', headers=setup['headers'])
        assert response.status_code == 403

    def test_list_users_as_site_admin(self, client, authenticated_user):
        """Site admin can list users"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)
        response = client.get('/api/admin/users', headers=setup['headers'])
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the admin user

    def test_list_users_with_search(self, client, authenticated_user, create_user):
        """Site admin can search users by email"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)
        create_user(email='searchable@example.com', display_name='Searchable User')

        response = client.get('/api/admin/users?search=searchable', headers=setup['headers'])
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['email'] == 'searchable@example.com'

    def test_delete_user_requires_site_admin(self, client, authenticated_user, create_user):
        """Non-site-admin cannot delete users"""
        setup = authenticated_user(email='regular@example.com', is_site_admin=False)
        target = create_user(email='target@example.com')

        response = client.delete(f'/api/admin/users/{target["id"]}', headers=setup['headers'])
        assert response.status_code == 403

    def test_delete_user_as_site_admin(self, client, app, authenticated_user, create_user):
        """Site admin can delete a regular user"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)
        target = create_user(email='target@example.com')

        response = client.delete(f'/api/admin/users/{target["id"]}', headers=setup['headers'])
        assert response.status_code == 200
        data = response.get_json()
        assert 'deleted_user' in data
        assert data['deleted_user'] == 'target@example.com'

        # Verify user is actually deleted
        with app.app_context():
            assert User.query.get(target['id']) is None

    def test_cannot_delete_self(self, client, authenticated_user):
        """Site admin cannot delete themselves"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)

        response = client.delete(f'/api/admin/users/{setup["user"]["id"]}', headers=setup['headers'])
        assert response.status_code == 400
        assert 'Cannot delete yourself' in response.get_json()['error']

    def test_cannot_delete_other_site_admin(self, client, authenticated_user, create_user):
        """Site admin cannot delete other site admins"""
        setup = authenticated_user(email='admin1@example.com', is_site_admin=True)
        other_admin = create_user(email='admin2@example.com', is_site_admin=True)

        response = client.delete(f'/api/admin/users/{other_admin["id"]}', headers=setup['headers'])
        assert response.status_code == 400
        assert 'Cannot delete site admins' in response.get_json()['error']

    def test_delete_nonexistent_user(self, client, authenticated_user):
        """Deleting nonexistent user returns 404"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)

        response = client.delete('/api/admin/users/99999', headers=setup['headers'])
        assert response.status_code == 404

    def test_delete_user_removes_circle_memberships(
        self, client, app, authenticated_user, create_user, create_circle, create_circle_member
    ):
        """Deleting user removes their circle memberships"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)
        target = create_user(email='target@example.com')
        circle = create_circle(name='Test Circle', created_by_id=setup['user']['id'])
        create_circle_member(circle['id'], target['id'], role='member')

        response = client.delete(f'/api/admin/users/{target["id"]}', headers=setup['headers'])
        assert response.status_code == 200
        assert response.get_json()['circles_removed_from'] >= 1

        # Verify membership is deleted
        with app.app_context():
            assert CircleMember.query.filter_by(user_id=target['id']).count() == 0

    def test_delete_user_removes_swipes(
        self, client, app, authenticated_user, create_user, create_circle,
        create_circle_member, create_movie, add_movie_to_circle, create_swipe
    ):
        """Deleting user removes their swipes"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)
        target = create_user(email='target@example.com')
        circle = create_circle(name='Test Circle', created_by_id=setup['user']['id'])
        create_circle_member(circle['id'], target['id'], role='member')
        movie = create_movie(title='Test Movie')
        add_movie_to_circle(circle['id'], movie['id'], setup['user']['id'])
        create_swipe(target['id'], movie['id'], circle['id'], 'like')

        response = client.delete(f'/api/admin/users/{target["id"]}', headers=setup['headers'])
        assert response.status_code == 200
        assert response.get_json()['swipes_deleted'] >= 1

        # Verify swipes are deleted
        with app.app_context():
            assert UserSwipe.query.filter_by(user_id=target['id']).count() == 0


class TestAdminCircleManagement:
    """Tests for admin circle management endpoints"""

    def test_delete_circle_requires_site_admin(self, client, authenticated_user):
        """Non-site-admin cannot delete circles via admin endpoint"""
        setup = authenticated_user(email='regular@example.com', is_site_admin=False, is_admin=True)

        response = client.delete(f'/api/admin/circles/{setup["circle"]["id"]}', headers=setup['headers'])
        assert response.status_code == 403

    def test_delete_circle_as_site_admin(self, client, app, authenticated_user, create_circle):
        """Site admin can delete any circle"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)
        circle = create_circle(name='Circle To Delete', created_by_id=setup['user']['id'])

        response = client.delete(f'/api/admin/circles/{circle["id"]}', headers=setup['headers'])
        assert response.status_code == 200
        data = response.get_json()
        assert data['deleted_circle'] == 'Circle To Delete'

        # Verify circle is actually deleted
        with app.app_context():
            assert Circle.query.get(circle['id']) is None

    def test_delete_nonexistent_circle(self, client, authenticated_user):
        """Deleting nonexistent circle returns 404"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)

        response = client.delete('/api/admin/circles/99999', headers=setup['headers'])
        assert response.status_code == 404

    def test_delete_circle_removes_members(
        self, client, app, authenticated_user, create_user, create_circle, create_circle_member
    ):
        """Deleting circle removes all memberships"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)
        circle = create_circle(name='Circle With Members', created_by_id=setup['user']['id'])
        user2 = create_user(email='user2@example.com')
        create_circle_member(circle['id'], setup['user']['id'], role='admin')
        create_circle_member(circle['id'], user2['id'], role='member')

        response = client.delete(f'/api/admin/circles/{circle["id"]}', headers=setup['headers'])
        assert response.status_code == 200
        assert response.get_json()['members_removed'] == 2

        # Verify memberships are deleted
        with app.app_context():
            assert CircleMember.query.filter_by(circle_id=circle['id']).count() == 0

    def test_delete_circle_removes_swipes(
        self, client, app, authenticated_user, create_circle, create_circle_member,
        create_movie, add_movie_to_circle, create_swipe
    ):
        """Deleting circle removes all swipes in that circle"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)
        circle = create_circle(name='Circle With Swipes', created_by_id=setup['user']['id'])
        create_circle_member(circle['id'], setup['user']['id'], role='admin')
        movie = create_movie(title='Test Movie')
        add_movie_to_circle(circle['id'], movie['id'], setup['user']['id'])
        create_swipe(setup['user']['id'], movie['id'], circle['id'], 'like')

        response = client.delete(f'/api/admin/circles/{circle["id"]}', headers=setup['headers'])
        assert response.status_code == 200
        assert response.get_json()['swipes_deleted'] >= 1

        # Verify swipes are deleted
        with app.app_context():
            assert UserSwipe.query.filter_by(circle_id=circle['id']).count() == 0


class TestAdminApiUtilization:
    """Tests for API utilization endpoint"""

    def test_api_utilization_requires_site_admin(self, client, authenticated_user):
        """Non-site-admin cannot access API utilization"""
        setup = authenticated_user(email='regular@example.com', is_site_admin=False)
        response = client.get('/api/admin/api-utilization', headers=setup['headers'])
        assert response.status_code == 403

    def test_api_utilization_as_site_admin(self, client, authenticated_user):
        """Site admin can access API utilization"""
        setup = authenticated_user(email='admin@example.com', is_site_admin=True)
        response = client.get('/api/admin/api-utilization', headers=setup['headers'])
        assert response.status_code == 200
        data = response.get_json()

        # Check OMDB stats are present
        assert 'omdb' in data
        assert 'today' in data['omdb']
        assert 'calls' in data['omdb']['today']
        assert 'limit' in data['omdb']['today']
        assert 'limit_info' in data['omdb']

        # Check TMDB stats are present
        assert 'tmdb' in data
        assert 'today' in data['tmdb']
        assert 'calls' in data['tmdb']['today']
        assert 'limit' in data['tmdb']['today']
        assert 'limit_info' in data['tmdb']

        # Check timestamp is present
        assert 'fetched_at' in data
