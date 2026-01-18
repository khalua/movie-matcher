from models import db, Circle, User, CircleMember, UserSwipe, CircleMovie, Movie
from sqlalchemy import func


def get_circle_analytics_data(circle_id):
    """Get analytics for a specific circle"""
    circle = Circle.query.get(circle_id)
    if not circle:
        return None

    # Total users in circle
    total_users = len(circle.members)

    # Total movies in circle
    total_movies = len(circle.movies)

    # Total swipes in circle
    total_swipes = UserSwipe.query.filter_by(circle_id=circle_id).count()

    # Most liked movies
    most_liked = (
        db.session.query(
            Movie,
            func.count(UserSwipe.id).label('like_count')
        )
        .join(UserSwipe, Movie.id == UserSwipe.movie_id)
        .filter(UserSwipe.circle_id == circle_id)
        .filter(UserSwipe.action == 'like')
        .group_by(Movie.id)
        .order_by(func.count(UserSwipe.id).desc())
        .limit(10)
        .all()
    )

    most_liked_movies = [
        {
            **movie.to_dict(),
            'like_count': like_count
        }
        for movie, like_count in most_liked
    ]

    # Members who haven't swiped
    circle_user_ids = [m.user_id for m in circle.members]
    users_who_swiped = (
        db.session.query(UserSwipe.user_id)
        .filter(UserSwipe.circle_id == circle_id)
        .distinct()
        .all()
    )
    users_who_swiped_ids = [uid for (uid,) in users_who_swiped]

    users_who_havent_swiped_ids = set(circle_user_ids) - set(users_who_swiped_ids)
    users_who_havent_swiped = User.query.filter(User.id.in_(users_who_havent_swiped_ids)).all()

    inactive_members = [
        {
            'id': u.id,
            'email': u.email,
            'display_name': u.display_name
        }
        for u in users_who_havent_swiped
    ]

    return {
        'total_users': total_users,
        'total_movies': total_movies,
        'total_swipes': total_swipes,
        'most_liked_movies': most_liked_movies,
        'members_who_havent_swiped': inactive_members
    }


def get_global_analytics_data():
    """Get global analytics (site admin only)"""
    total_circles = Circle.query.filter_by(is_active=True).count()
    total_users = User.query.count()
    total_movies = Movie.query.count()

    # Active circles (circles with recent swipes)
    from datetime import datetime, timedelta
    recent_date = datetime.utcnow() - timedelta(days=7)
    active_circles = (
        db.session.query(UserSwipe.circle_id)
        .filter(UserSwipe.swiped_at > recent_date)
        .distinct()
        .count()
    )

    return {
        'total_circles': total_circles,
        'total_users': total_users,
        'total_movies': total_movies,
        'active_circles_7d': active_circles
    }
