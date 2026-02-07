"""
Tests for pack activation/deactivation logic.

Tests cover:
- Deactivating a pack removes its movies from the circle
- Deactivating a pack preserves swipe history
- Reactivating a pack re-adds movies to the circle
- Reactivating skips movies already in circle from other sources
- Deactivating affects swiping (no movies left = 404)
"""
import pytest
from models import db, MoviePack, MoviePackCache, CircleMovie, CirclePackInstall, UserSwipe


@pytest.fixture
def create_pack(app):
    """Factory fixture to create a movie pack"""
    def _create_pack(name='Test Pack', slug='test-pack', pack_type='static', category='curated'):
        with app.app_context():
            pack = MoviePack(
                name=name,
                slug=slug,
                pack_type=pack_type,
                category=category,
                source_config={'file': 'test.txt'},
                icon='🎬',
                is_active=True
            )
            db.session.add(pack)
            db.session.commit()
            return {'id': pack.id, 'name': pack.name, 'slug': pack.slug}
    return _create_pack


@pytest.fixture
def create_pack_cache(app):
    """Factory fixture to add a movie to a pack's cache"""
    def _create_pack_cache(pack_id, movie_id, position=1):
        with app.app_context():
            cache = MoviePackCache(
                pack_id=pack_id,
                movie_id=movie_id,
                position=position
            )
            db.session.add(cache)
            db.session.commit()
            return {'id': cache.id}
    return _create_pack_cache


@pytest.fixture
def add_movie_to_circle_with_pack(app):
    """Factory fixture to add a movie to a circle with pack attribution"""
    def _add(circle_id, movie_id, added_by_id, pack_id, pack_name):
        with app.app_context():
            cm = CircleMovie(
                circle_id=circle_id,
                movie_id=movie_id,
                added_by_id=added_by_id,
                source_pack_id=pack_id,
                source_pack_name=pack_name
            )
            db.session.add(cm)
            db.session.commit()
            return {'id': cm.id}
    return _add


@pytest.fixture
def install_pack(app):
    """Factory fixture to create a CirclePackInstall record"""
    def _install(circle_id, pack_id, user_id, is_active=True):
        with app.app_context():
            install = CirclePackInstall(
                circle_id=circle_id,
                pack_id=pack_id,
                installed_by_id=user_id,
                is_active=is_active
            )
            db.session.add(install)
            db.session.commit()
            return {'id': install.id}
    return _install


class TestDeactivatePack:
    """Tests for pack deactivation"""

    def test_deactivate_removes_movies_from_circle(
        self, client, authenticated_user, create_movie, create_pack,
        create_pack_cache, add_movie_to_circle_with_pack, install_pack, app
    ):
        """Deactivating a pack should remove its movies from the circle"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Action Pack', slug='action-pack')
        movie1 = create_movie(title='Action Movie 1', year=2020)
        movie2 = create_movie(title='Action Movie 2', year=2021)

        create_pack_cache(pack['id'], movie1['id'], position=1)
        create_pack_cache(pack['id'], movie2['id'], position=2)
        add_movie_to_circle_with_pack(circle_id, movie1['id'], user_id, pack['id'], pack['name'])
        add_movie_to_circle_with_pack(circle_id, movie2['id'], user_id, pack['id'], pack['name'])
        install_pack(circle_id, pack['id'], user_id)

        response = client.post(
            f'/api/packs/{pack["id"]}/deactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        assert response.status_code == 200
        assert response.get_json()['removed_count'] == 2

        with app.app_context():
            remaining = CircleMovie.query.filter_by(circle_id=circle_id).count()
            assert remaining == 0

    def test_deactivate_preserves_swipe_history(
        self, client, authenticated_user, create_movie, create_pack,
        create_pack_cache, add_movie_to_circle_with_pack, install_pack,
        create_swipe, app
    ):
        """Deactivating a pack should preserve existing swipe data"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Swipe Pack', slug='swipe-pack')
        movie = create_movie(title='Swiped Movie', year=2022)

        create_pack_cache(pack['id'], movie['id'], position=1)
        add_movie_to_circle_with_pack(circle_id, movie['id'], user_id, pack['id'], pack['name'])
        install_pack(circle_id, pack['id'], user_id)
        create_swipe(user_id, movie['id'], circle_id, action='like')

        client.post(
            f'/api/packs/{pack["id"]}/deactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        with app.app_context():
            swipes = UserSwipe.query.filter_by(
                user_id=user_id, movie_id=movie['id'], circle_id=circle_id
            ).all()
            assert len(swipes) == 1
            assert swipes[0].action == 'like'

    def test_deactivate_only_removes_pack_movies(
        self, client, authenticated_user, create_movie, create_pack,
        create_pack_cache, add_movie_to_circle_with_pack, add_movie_to_circle,
        install_pack, app
    ):
        """Deactivating should only remove movies from that pack, not manually added ones"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Partial Pack', slug='partial-pack')
        pack_movie = create_movie(title='Pack Movie', year=2020)
        manual_movie = create_movie(title='Manual Movie', year=2021)

        create_pack_cache(pack['id'], pack_movie['id'], position=1)
        add_movie_to_circle_with_pack(circle_id, pack_movie['id'], user_id, pack['id'], pack['name'])
        add_movie_to_circle(circle_id, manual_movie['id'], user_id)
        install_pack(circle_id, pack['id'], user_id)

        client.post(
            f'/api/packs/{pack["id"]}/deactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        with app.app_context():
            remaining = CircleMovie.query.filter_by(circle_id=circle_id).all()
            assert len(remaining) == 1
            assert remaining[0].movie_id == manual_movie['id']

    def test_deactivate_makes_swiping_return_no_movies(
        self, client, authenticated_user, create_movie, create_pack,
        create_pack_cache, add_movie_to_circle_with_pack, install_pack
    ):
        """After deactivating the only pack, swiping should return 'No movies in this circle'"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Only Pack', slug='only-pack')
        movie = create_movie(title='Only Movie', year=2020)

        create_pack_cache(pack['id'], movie['id'], position=1)
        add_movie_to_circle_with_pack(circle_id, movie['id'], user_id, pack['id'], pack['name'])
        install_pack(circle_id, pack['id'], user_id)

        # Verify swiping works before deactivation
        response = client.get('/api/movies/random', headers=setup['headers'])
        assert response.status_code == 200

        # Deactivate
        client.post(
            f'/api/packs/{pack["id"]}/deactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        # Swiping should now return 404 with "no movies" message
        response = client.get('/api/movies/random', headers=setup['headers'])
        assert response.status_code == 404
        assert response.get_json()['message'] == 'No movies in this circle'


class TestReactivatePack:
    """Tests for pack reactivation"""

    def test_reactivate_readds_movies_to_circle(
        self, client, authenticated_user, create_movie, create_pack,
        create_pack_cache, install_pack, app
    ):
        """Reactivating a pack should re-add its cached movies to the circle"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Reactivate Pack', slug='reactivate-pack')
        movie1 = create_movie(title='Reactivate Movie 1', year=2020)
        movie2 = create_movie(title='Reactivate Movie 2', year=2021)

        create_pack_cache(pack['id'], movie1['id'], position=1)
        create_pack_cache(pack['id'], movie2['id'], position=2)

        # Install as deactivated (no movies in circle)
        with app.app_context():
            inst = CirclePackInstall(
                circle_id=circle_id,
                pack_id=pack['id'],
                installed_by_id=user_id,
                is_active=False
            )
            db.session.add(inst)
            db.session.commit()

        response = client.post(
            f'/api/packs/{pack["id"]}/reactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        assert response.status_code == 200
        assert response.get_json()['added_count'] == 2

        with app.app_context():
            circle_movies = CircleMovie.query.filter_by(circle_id=circle_id).all()
            assert len(circle_movies) == 2
            movie_ids = {cm.movie_id for cm in circle_movies}
            assert movie1['id'] in movie_ids
            assert movie2['id'] in movie_ids
            for cm in circle_movies:
                assert cm.source_pack_id == pack['id']

    def test_reactivate_skips_movies_already_in_circle(
        self, client, authenticated_user, create_movie, create_pack,
        create_pack_cache, add_movie_to_circle, install_pack, app
    ):
        """Reactivating should skip movies that already exist in the circle from another source"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Overlap Pack', slug='overlap-pack')
        shared_movie = create_movie(title='Shared Movie', year=2020)
        pack_only_movie = create_movie(title='Pack Only Movie', year=2021)

        create_pack_cache(pack['id'], shared_movie['id'], position=1)
        create_pack_cache(pack['id'], pack_only_movie['id'], position=2)

        # shared_movie already in circle manually
        add_movie_to_circle(circle_id, shared_movie['id'], user_id)

        # Install as deactivated
        with app.app_context():
            inst = CirclePackInstall(
                circle_id=circle_id,
                pack_id=pack['id'],
                installed_by_id=user_id,
                is_active=False
            )
            db.session.add(inst)
            db.session.commit()

        response = client.post(
            f'/api/packs/{pack["id"]}/reactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        assert response.status_code == 200
        assert response.get_json()['added_count'] == 1

        with app.app_context():
            circle_movies = CircleMovie.query.filter_by(circle_id=circle_id).all()
            assert len(circle_movies) == 2

    def test_reactivate_preserves_prior_swipe_history(
        self, client, authenticated_user, create_movie, create_pack,
        create_pack_cache, add_movie_to_circle_with_pack, install_pack,
        create_swipe, app
    ):
        """After deactivate then reactivate, swipe history should still exist"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Round Trip Pack', slug='round-trip-pack')
        movie = create_movie(title='Round Trip Movie', year=2020)

        create_pack_cache(pack['id'], movie['id'], position=1)
        add_movie_to_circle_with_pack(circle_id, movie['id'], user_id, pack['id'], pack['name'])
        install_pack(circle_id, pack['id'], user_id)
        create_swipe(user_id, movie['id'], circle_id, action='like')

        # Deactivate
        client.post(
            f'/api/packs/{pack["id"]}/deactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        # Reactivate
        client.post(
            f'/api/packs/{pack["id"]}/reactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        # Swipe history should still be there
        with app.app_context():
            swipes = UserSwipe.query.filter_by(
                user_id=user_id, movie_id=movie['id'], circle_id=circle_id
            ).all()
            assert len(swipes) == 1
            assert swipes[0].action == 'like'

    def test_reactivate_restores_swiping(
        self, client, authenticated_user, create_movie, create_pack,
        create_pack_cache, add_movie_to_circle_with_pack, install_pack
    ):
        """After deactivate then reactivate, swiping should work again"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Restore Pack', slug='restore-pack')
        movie = create_movie(title='Restore Movie', year=2020)

        create_pack_cache(pack['id'], movie['id'], position=1)
        add_movie_to_circle_with_pack(circle_id, movie['id'], user_id, pack['id'], pack['name'])
        install_pack(circle_id, pack['id'], user_id)

        # Deactivate
        client.post(
            f'/api/packs/{pack["id"]}/deactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        # Swiping should fail
        response = client.get('/api/movies/random', headers=setup['headers'])
        assert response.status_code == 404

        # Reactivate
        client.post(
            f'/api/packs/{pack["id"]}/reactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        # Swiping should work again
        response = client.get('/api/movies/random', headers=setup['headers'])
        assert response.status_code == 200
        assert response.get_json()['title'] == 'Restore Movie'


class TestDeactivatePermissions:
    """Tests for pack deactivation authorization"""

    def test_non_admin_cannot_deactivate(
        self, client, authenticated_user, create_pack, install_pack
    ):
        """Non-admin members should not be able to deactivate packs"""
        setup = authenticated_user(is_admin=False)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Admin Only Pack', slug='admin-only-pack')
        install_pack(circle_id, pack['id'], user_id)

        response = client.post(
            f'/api/packs/{pack["id"]}/deactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        assert response.status_code == 403

    def test_non_admin_cannot_reactivate(
        self, client, authenticated_user, create_pack, app
    ):
        """Non-admin members should not be able to reactivate packs"""
        setup = authenticated_user(is_admin=False)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Admin Reactivate Pack', slug='admin-reactivate-pack')

        with app.app_context():
            inst = CirclePackInstall(
                circle_id=circle_id,
                pack_id=pack['id'],
                installed_by_id=user_id,
                is_active=False
            )
            db.session.add(inst)
            db.session.commit()

        response = client.post(
            f'/api/packs/{pack["id"]}/reactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        assert response.status_code == 403


class TestGetPacksCircleMovieCount:
    """Tests for circle_movie_count in the GET /api/packs response"""

    def test_returns_circle_movie_count(
        self, client, authenticated_user, create_movie, add_movie_to_circle
    ):
        """GET /api/packs?circle_id=X should include circle_movie_count"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        movie1 = create_movie(title='Count Movie 1', year=2020)
        movie2 = create_movie(title='Count Movie 2', year=2021)
        movie3 = create_movie(title='Count Movie 3', year=2022)
        add_movie_to_circle(circle_id, movie1['id'], user_id)
        add_movie_to_circle(circle_id, movie2['id'], user_id)
        add_movie_to_circle(circle_id, movie3['id'], user_id)

        response = client.get(
            f'/api/packs?circle_id={circle_id}',
            headers=setup['headers']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['circle_movie_count'] == 3

    def test_returns_zero_for_empty_circle(self, client, authenticated_user):
        """circle_movie_count should be 0 for a new circle with no movies"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']

        response = client.get(
            f'/api/packs?circle_id={circle_id}',
            headers=setup['headers']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['circle_movie_count'] == 0

    def test_no_circle_movie_count_without_circle_id(self, client, authenticated_user):
        """circle_movie_count should not be present when no circle_id is passed"""
        setup = authenticated_user(is_admin=True)

        response = client.get(
            '/api/packs',
            headers=setup['headers']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'circle_movie_count' not in data

    def test_count_updates_after_pack_deactivation(
        self, client, authenticated_user, create_movie, create_pack,
        create_pack_cache, add_movie_to_circle_with_pack, add_movie_to_circle,
        install_pack
    ):
        """circle_movie_count should decrease after deactivating a pack"""
        setup = authenticated_user(is_admin=True)
        circle_id = setup['circle']['id']
        user_id = setup['user']['id']

        pack = create_pack(name='Count Pack', slug='count-pack')
        pack_movie = create_movie(title='Pack Count Movie', year=2020)
        manual_movie = create_movie(title='Manual Count Movie', year=2021)

        create_pack_cache(pack['id'], pack_movie['id'], position=1)
        add_movie_to_circle_with_pack(circle_id, pack_movie['id'], user_id, pack['id'], pack['name'])
        add_movie_to_circle(circle_id, manual_movie['id'], user_id)
        install_pack(circle_id, pack['id'], user_id)

        # Before deactivation: 2 movies
        response = client.get(
            f'/api/packs?circle_id={circle_id}',
            headers=setup['headers']
        )
        assert response.get_json()['circle_movie_count'] == 2

        # Deactivate pack
        client.post(
            f'/api/packs/{pack["id"]}/deactivate',
            headers=setup['headers'],
            json={'circle_id': circle_id}
        )

        # After deactivation: 1 movie (only manual)
        response = client.get(
            f'/api/packs?circle_id={circle_id}',
            headers=setup['headers']
        )
        assert response.get_json()['circle_movie_count'] == 1
