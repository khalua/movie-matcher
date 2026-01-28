"""
Tests for movie routes and match detection logic.

Tests cover:
- Getting random movies
- Like/dislike actions
- Match detection algorithm
- Match queries
"""
import pytest
from datetime import date
from models import db, UserSwipe, MatchEvent, UserBoostStats


class TestGetRandomMovie:
    """Tests for /api/movies/random endpoint"""

    def test_get_random_movie_success(
        self, client, authenticated_user, create_movie, add_movie_to_circle
    ):
        """Should return a random unseen movie"""
        setup = authenticated_user()
        movie = create_movie(title='Test Movie', year=2024)
        add_movie_to_circle(
            setup['circle']['id'],
            movie['id'],
            setup['user']['id']
        )

        response = client.get(
            '/api/movies/random',
            headers=setup['headers']
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Test Movie'
        assert data['year'] == 2024

    def test_get_random_movie_empty_circle(self, client, authenticated_user):
        """Should return 404 when circle has no movies"""
        setup = authenticated_user()

        response = client.get(
            '/api/movies/random',
            headers=setup['headers']
        )

        assert response.status_code == 404
        assert 'No movies' in response.get_json()['message']

    def test_get_random_movie_all_swiped(
        self, client, authenticated_user, create_movie,
        add_movie_to_circle, create_swipe
    ):
        """Should return 404 when user has swiped all movies"""
        setup = authenticated_user()
        movie = create_movie(title='Seen Movie')
        add_movie_to_circle(
            setup['circle']['id'],
            movie['id'],
            setup['user']['id']
        )
        create_swipe(
            setup['user']['id'],
            movie['id'],
            setup['circle']['id'],
            action='like'
        )

        response = client.get(
            '/api/movies/random',
            headers=setup['headers']
        )

        assert response.status_code == 404
        assert 'No more unseen' in response.get_json()['message']

    def test_alphabetical_sort_order(
        self, client, authenticated_user, create_movie, add_movie_to_circle
    ):
        """Alphabetical sort should return first movie alphabetically"""
        setup = authenticated_user()

        # Create movies out of alphabetical order
        movie_z = create_movie(title='Zebra Movie', year=2024)
        movie_a = create_movie(title='Alpha Movie', year=2024)

        add_movie_to_circle(setup['circle']['id'], movie_z['id'], setup['user']['id'])
        add_movie_to_circle(setup['circle']['id'], movie_a['id'], setup['user']['id'])

        response = client.get(
            '/api/movies/random?sort=alphabetical',
            headers=setup['headers']
        )

        assert response.status_code == 200
        assert response.get_json()['title'] == 'Alpha Movie'


class TestLikeMovie:
    """Tests for /api/movies/like endpoint"""

    def test_like_movie_success(
        self, client, authenticated_user, create_movie, add_movie_to_circle, app
    ):
        """Should create a like swipe"""
        setup = authenticated_user()
        movie = create_movie(title='Likeable Movie')
        add_movie_to_circle(
            setup['circle']['id'],
            movie['id'],
            setup['user']['id']
        )

        response = client.post(
            '/api/movies/like',
            headers=setup['headers'],
            json={'movieId': movie['id']}
        )

        assert response.status_code == 200

        # Verify swipe was created
        with app.app_context():
            swipe = UserSwipe.query.filter_by(
                user_id=setup['user']['id'],
                movie_id=movie['id'],
                circle_id=setup['circle']['id']
            ).first()
            assert swipe is not None
            assert swipe.action == 'like'

    def test_like_movie_not_in_circle(
        self, client, authenticated_user, create_movie
    ):
        """Should fail when movie is not in user's circle"""
        setup = authenticated_user()
        movie = create_movie(title='Other Circle Movie')
        # Movie not added to this circle

        response = client.post(
            '/api/movies/like',
            headers=setup['headers'],
            json={'movieId': movie['id']}
        )

        assert response.status_code == 404

    def test_like_movie_missing_id(self, client, authenticated_user):
        """Should fail when movieId is not provided"""
        setup = authenticated_user()

        response = client.post(
            '/api/movies/like',
            headers=setup['headers'],
            json={}
        )

        assert response.status_code == 400


class TestDislikeMovie:
    """Tests for /api/movies/dislike endpoint"""

    def test_dislike_movie_success(
        self, client, authenticated_user, create_movie, add_movie_to_circle, app
    ):
        """Should create a dislike swipe"""
        setup = authenticated_user()
        movie = create_movie(title='Not My Type')
        add_movie_to_circle(
            setup['circle']['id'],
            movie['id'],
            setup['user']['id']
        )

        response = client.post(
            '/api/movies/dislike',
            headers=setup['headers'],
            json={'movieId': movie['id']}
        )

        assert response.status_code == 200

        with app.app_context():
            swipe = UserSwipe.query.filter_by(
                user_id=setup['user']['id'],
                movie_id=movie['id']
            ).first()
            assert swipe.action == 'dislike'


class TestMatchDetection:
    """Tests for match detection logic"""

    def test_no_match_with_single_like(
        self, client, setup_match_scenario, auth_headers
    ):
        """Single like should not create a match"""
        data = setup_match_scenario()
        user1 = data['users'][0]
        circle = data['circle']
        movie = data['movies'][0]

        headers = auth_headers(user1['email'], circle['id'])

        response = client.post(
            '/api/movies/like',
            headers=headers,
            json={'movieId': movie['id']}
        )

        assert response.status_code == 200
        assert 'match' not in response.get_json()

    def test_partial_match_with_two_likes(
        self, client, setup_match_scenario, auth_headers, app
    ):
        """Two likes in a 3-person circle creates partial match"""
        data = setup_match_scenario()
        user1, user2 = data['users'][0], data['users'][1]
        circle = data['circle']
        movie = data['movies'][0]

        # First user likes
        headers1 = auth_headers(user1['email'], circle['id'])
        client.post(
            '/api/movies/like',
            headers=headers1,
            json={'movieId': movie['id']}
        )

        # Second user likes - should create partial match
        headers2 = auth_headers(user2['email'], circle['id'])
        response = client.post(
            '/api/movies/like',
            headers=headers2,
            json={'movieId': movie['id']}
        )

        assert response.status_code == 200
        result = response.get_json()
        assert 'match' in result
        assert result['match']['match_type'] == 'partial'
        assert result['match']['like_count'] == 2
        assert result['match']['member_count'] == 3

    def test_full_match_when_all_members_like(
        self, client, setup_match_scenario, auth_headers, app
    ):
        """All members liking creates full match"""
        data = setup_match_scenario()
        users = data['users']
        circle = data['circle']
        movie = data['movies'][0]

        # All three users like the movie
        for i, user in enumerate(users):
            headers = auth_headers(user['email'], circle['id'])
            response = client.post(
                '/api/movies/like',
                headers=headers,
                json={'movieId': movie['id']}
            )

            if i == len(users) - 1:  # Last user
                result = response.get_json()
                assert 'match' in result
                assert result['match']['match_type'] == 'full'
                assert result['match']['like_count'] == 3

    def test_match_event_is_recorded(
        self, client, setup_match_scenario, auth_headers, app
    ):
        """Match event should be recorded in database"""
        data = setup_match_scenario()
        user1, user2 = data['users'][0], data['users'][1]
        circle = data['circle']
        movie = data['movies'][0]

        # Create partial match
        headers1 = auth_headers(user1['email'], circle['id'])
        client.post(
            '/api/movies/like',
            headers=headers1,
            json={'movieId': movie['id']}
        )

        headers2 = auth_headers(user2['email'], circle['id'])
        client.post(
            '/api/movies/like',
            headers=headers2,
            json={'movieId': movie['id']}
        )

        # Verify match event in database
        with app.app_context():
            match_event = MatchEvent.query.filter_by(
                circle_id=circle['id'],
                movie_id=movie['id']
            ).first()
            assert match_event is not None
            assert match_event.match_type == 'partial'
            assert match_event.triggered_by_user_id == user2['id']


class TestGetMatches:
    """Tests for /api/movies/matches endpoint"""

    def test_get_matches_requires_two_users(self, client, authenticated_user):
        """Should fail with less than 2 users selected"""
        setup = authenticated_user()

        response = client.post(
            '/api/movies/matches',
            headers=setup['headers'],
            json={'userIds': [setup['user']['id']]}
        )

        assert response.status_code == 400
        assert 'at least 2' in response.get_json()['error'].lower()

    def test_get_matches_finds_shared_likes(
        self, client, setup_match_scenario, auth_headers, create_swipe
    ):
        """Should return movies liked by all selected users"""
        data = setup_match_scenario()
        user1, user2 = data['users'][0], data['users'][1]
        circle = data['circle']
        movie = data['movies'][0]

        # Both users like the movie
        create_swipe(user1['id'], movie['id'], circle['id'], 'like')
        create_swipe(user2['id'], movie['id'], circle['id'], 'like')

        headers = auth_headers(user1['email'], circle['id'])
        response = client.post(
            '/api/movies/matches',
            headers=headers,
            json={'userIds': [user1['id'], user2['id']]}
        )

        assert response.status_code == 200
        matches = response.get_json()
        assert len(matches) == 1
        assert matches[0]['title'] == 'Movie One'

    def test_get_matches_excludes_partial_likes(
        self, client, setup_match_scenario, auth_headers, create_swipe
    ):
        """Should not return movies only liked by some selected users"""
        data = setup_match_scenario()
        user1, user2 = data['users'][0], data['users'][1]
        circle = data['circle']
        movie = data['movies'][0]

        # Only user1 likes the movie
        create_swipe(user1['id'], movie['id'], circle['id'], 'like')
        # user2 dislikes
        create_swipe(user2['id'], movie['id'], circle['id'], 'dislike')

        headers = auth_headers(user1['email'], circle['id'])
        response = client.post(
            '/api/movies/matches',
            headers=headers,
            json={'userIds': [user1['id'], user2['id']]}
        )

        assert response.status_code == 200
        matches = response.get_json()
        assert len(matches) == 0

    def test_get_matches_validates_circle_membership(
        self, client, setup_match_scenario, auth_headers, create_user
    ):
        """Should reject users not in the circle"""
        data = setup_match_scenario()
        user1 = data['users'][0]
        circle = data['circle']

        outsider = create_user(email='outsider@example.com')

        headers = auth_headers(user1['email'], circle['id'])
        response = client.post(
            '/api/movies/matches',
            headers=headers,
            json={'userIds': [user1['id'], outsider['id']]}
        )

        assert response.status_code == 403

    def test_get_matches_shows_all_users_who_liked(
        self, client, setup_match_scenario, auth_headers, create_swipe
    ):
        """Should show all users who liked a movie, not just selected users"""
        data = setup_match_scenario()
        user1, user2, user3 = data['users'][0], data['users'][1], data['users'][2]
        circle = data['circle']
        movie = data['movies'][0]

        # All three users like the movie
        create_swipe(user1['id'], movie['id'], circle['id'], 'like')
        create_swipe(user2['id'], movie['id'], circle['id'], 'like')
        create_swipe(user3['id'], movie['id'], circle['id'], 'like')

        # Query matches for only user2 and user3
        headers = auth_headers(user2['email'], circle['id'])
        response = client.post(
            '/api/movies/matches',
            headers=headers,
            json={'userIds': [user2['id'], user3['id']]}
        )

        assert response.status_code == 200
        matches = response.get_json()
        assert len(matches) == 1

        # matched_users should include ALL users who liked, including user1
        matched_user_ids = [u['id'] for u in matches[0]['matched_users']]
        assert user1['id'] in matched_user_ids
        assert user2['id'] in matched_user_ids
        assert user3['id'] in matched_user_ids
        assert len(matched_user_ids) == 3


class TestBoostedMovies:
    """Tests for boosted movie prioritization"""

    def test_boosted_movie_on_third_swipe(
        self, client, setup_match_scenario, auth_headers, create_swipe
    ):
        """Should return boosted movie on 3rd swipe when others have liked"""
        data = setup_match_scenario()
        user1, user2 = data['users'][0], data['users'][1]
        circle = data['circle']
        movies = data['movies']

        # user2 likes movie[0]
        create_swipe(user2['id'], movies[0]['id'], circle['id'], 'like')

        headers = auth_headers(user1['email'], circle['id'])

        # 3rd swipe should return boosted movie
        response = client.get(
            '/api/movies/random?swipe_count=3',
            headers=headers
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['is_boosted'] is True
        assert result['id'] == movies[0]['id']

    def test_no_boost_when_no_likes_from_others(
        self, client, authenticated_user, create_movie, add_movie_to_circle
    ):
        """Should not boost when no other users have liked movies"""
        setup = authenticated_user()
        movie = create_movie(title='Unloved Movie')
        add_movie_to_circle(
            setup['circle']['id'],
            movie['id'],
            setup['user']['id']
        )

        response = client.get(
            '/api/movies/random?swipe_count=3',
            headers=setup['headers']
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['is_boosted'] is False

    def test_boost_cap_at_10_per_day(
        self, client, setup_match_scenario, auth_headers, create_swipe, app
    ):
        """Should stop boosting after 10 boosted movies per day"""
        data = setup_match_scenario()
        user1, user2 = data['users'][0], data['users'][1]
        circle = data['circle']
        movie = data['movies'][0]

        # user2 likes the movie
        create_swipe(user2['id'], movie['id'], circle['id'], 'like')

        # Pre-set user1's boost count to 10
        with app.app_context():
            boost_stats = UserBoostStats(
                user_id=user1['id'],
                circle_id=circle['id'],
                date=date.today(),
                boosted_count=10
            )
            db.session.add(boost_stats)
            db.session.commit()

        headers = auth_headers(user1['email'], circle['id'])

        response = client.get(
            '/api/movies/random?swipe_count=3',
            headers=headers
        )

        assert response.status_code == 200
        result = response.get_json()
        # Should not be boosted because cap reached
        assert result['is_boosted'] is False

    def test_boost_prioritizes_most_liked(
        self, client, setup_match_scenario, auth_headers, create_swipe
    ):
        """Should prioritize movies with more likes"""
        data = setup_match_scenario()
        users = data['users']
        user1, user2, user3 = users[0], users[1], users[2]
        circle = data['circle']
        movies = data['movies']

        # movie[0] gets 1 like from user2
        create_swipe(user2['id'], movies[0]['id'], circle['id'], 'like')

        # movie[1] gets 2 likes from user2 and user3
        create_swipe(user2['id'], movies[1]['id'], circle['id'], 'like')
        create_swipe(user3['id'], movies[1]['id'], circle['id'], 'like')

        headers = auth_headers(user1['email'], circle['id'])

        response = client.get(
            '/api/movies/random?swipe_count=3',
            headers=headers
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['is_boosted'] is True
        # Should return movie[1] because it has more likes
        assert result['id'] == movies[1]['id']

    def test_no_boost_on_non_third_swipe(
        self, client, setup_match_scenario, auth_headers, create_swipe
    ):
        """Should not boost on swipes that aren't multiples of 3"""
        data = setup_match_scenario()
        user1, user2 = data['users'][0], data['users'][1]
        circle = data['circle']
        movie = data['movies'][0]

        create_swipe(user2['id'], movie['id'], circle['id'], 'like')

        headers = auth_headers(user1['email'], circle['id'])

        # Swipe count 1 - not a boost position
        response = client.get(
            '/api/movies/random?swipe_count=1',
            headers=headers
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['is_boosted'] is False
