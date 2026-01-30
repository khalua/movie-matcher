from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()


class User(db.Model):
    """User model with email-based authentication"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(80))
    password_hash = db.Column(db.String(200), nullable=True)  # Nullable for OAuth users
    is_site_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    password_reset_token = db.Column(db.String(100), unique=True, nullable=True, index=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)

    # Relationships
    circles = db.relationship('CircleMember', back_populates='user', cascade='all, delete-orphan')
    swipes = db.relationship('UserSwipe', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash. Returns False for OAuth-only users."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'display_name': self.display_name,
            'is_site_admin': self.is_site_admin,
            'has_password': self.password_hash is not None
        }


class Circle(db.Model):
    """Circle (group) model for multi-tenancy"""
    __tablename__ = 'circles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    members = db.relationship('CircleMember', back_populates='circle', cascade='all, delete-orphan')
    movies = db.relationship('CircleMovie', back_populates='circle', cascade='all, delete-orphan')
    invitations = db.relationship('Invitation', back_populates='circle', cascade='all, delete-orphan')

    def to_dict(self, user_id=None):
        """Convert circle to dictionary"""
        # Find the admin of this circle
        admin_member = next((m for m in self.members if m.role == 'admin'), None)
        admin_name = None
        if admin_member and admin_member.user:
            admin_name = admin_member.user.display_name or admin_member.user.email.split('@')[0]

        data = {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'member_count': len(self.members),
            'admin_name': admin_name
        }
        if user_id:
            member = next((m for m in self.members if m.user_id == user_id), None)
            data['role'] = member.role if member else None
        return data


class CircleMember(db.Model):
    """Circle membership with role (admin or member)"""
    __tablename__ = 'circle_members'

    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # 'admin' or 'member'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen_comments_at = db.Column(db.DateTime, nullable=True)  # Track when user last viewed comments

    # Relationships
    circle = db.relationship('Circle', back_populates='members')
    user = db.relationship('User', back_populates='circles')

    __table_args__ = (
        UniqueConstraint('circle_id', 'user_id', name='_circle_user_uc'),
        db.Index('idx_circle_members_user', 'user_id'),
        db.Index('idx_circle_members_circle', 'circle_id'),
    )


class Movie(db.Model):
    """Movie model - global pool shared across circles"""
    __tablename__ = 'movies'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    poster = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.String(10), nullable=False)
    length = db.Column(db.String(20), nullable=False)
    starring = db.Column(db.String(200), nullable=False)
    added_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for seeded movies

    # Relationships
    circles = db.relationship('CircleMovie', back_populates='movie', cascade='all, delete-orphan')
    swipes = db.relationship('UserSwipe', back_populates='movie', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('title', 'year', name='_title_year_uc'),
    )

    def to_dict(self):
        """Convert movie to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'year': self.year,
            'poster': self.poster,
            'description': self.description,
            'genre': self.genre,
            'rating': self.rating,
            'length': self.length,
            'starring': self.starring
        }


class CircleMovie(db.Model):
    """Association between circles and movies"""
    __tablename__ = 'circle_movies'

    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_system_seeded = db.Column(db.Boolean, default=False)  # True for movies added via top_movies.txt seeding
    source_pack_id = db.Column(db.Integer, db.ForeignKey('movie_packs.id'), nullable=True)
    source_pack_name = db.Column(db.String(100), nullable=True)  # Denormalized for display

    # Relationships
    circle = db.relationship('Circle', back_populates='movies')
    movie = db.relationship('Movie', back_populates='circles')
    source_pack = db.relationship('MoviePack')

    __table_args__ = (
        UniqueConstraint('circle_id', 'movie_id', name='_circle_movie_uc'),
        db.Index('idx_circle_movies_circle', 'circle_id'),
        db.Index('idx_circle_movies_movie', 'movie_id'),
    )


class UserSwipe(db.Model):
    """User swipe actions (like/dislike) scoped to circles"""
    __tablename__ = 'user_swipes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    action = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'
    swiped_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='swipes')
    movie = db.relationship('Movie', back_populates='swipes')
    circle = db.relationship('Circle')

    __table_args__ = (
        UniqueConstraint('user_id', 'movie_id', 'circle_id', name='_user_movie_circle_uc'),
        db.Index('idx_user_swipes_user_circle', 'user_id', 'circle_id'),
        db.Index('idx_user_swipes_movie_circle', 'movie_id', 'circle_id'),
    )


class Invitation(db.Model):
    """Invitation codes for joining circles"""
    __tablename__ = 'invitations'

    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uses_remaining = db.Column(db.Integer, nullable=True)  # NULL = unlimited
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    circle = db.relationship('Circle', back_populates='invitations')

    __table_args__ = (
        db.Index('idx_invitations_expires', 'expires_at', 'is_active'),
    )


class PendingInvite(db.Model):
    """Email-based pending invitations to circles"""
    __tablename__ = 'pending_invites'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    invited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    circle = db.relationship('Circle')
    invited_by = db.relationship('User')

    __table_args__ = (
        UniqueConstraint('email', 'circle_id', name='_email_circle_uc'),
    )


class MatchEvent(db.Model):
    """Track match events for notification purposes"""
    __tablename__ = 'match_events'

    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    match_type = db.Column(db.String(20), nullable=False)  # 'partial' or 'full'
    triggered_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    member_count_at_time = db.Column(db.Integer, nullable=False)
    like_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    circle = db.relationship('Circle')
    movie = db.relationship('Movie')
    triggered_by = db.relationship('User')

    __table_args__ = (
        db.Index('idx_match_events_circle_created', 'circle_id', 'created_at'),
    )


class UserMatchSeen(db.Model):
    """Track which match events a user has seen"""
    __tablename__ = 'user_match_seen'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    last_seen_match_id = db.Column(db.Integer, db.ForeignKey('match_events.id'), nullable=True)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'circle_id', name='_user_circle_seen_uc'),
        db.Index('idx_user_match_seen_user', 'user_id'),
    )


class MoviePack(db.Model):
    """Movie pack definitions - curated collections of movies"""
    __tablename__ = 'movie_packs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    pack_type = db.Column(db.String(20), nullable=False)  # 'static' or 'dynamic'
    category = db.Column(db.String(30), nullable=False)  # 'streaming', 'genre', 'curated'
    source_config = db.Column(db.JSON)  # {"provider_id": 8} or {"file": "80s_bangers.txt"}
    icon = db.Column(db.String(10))  # emoji
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cached_movies = db.relationship('MoviePackCache', back_populates='pack', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'pack_type': self.pack_type,
            'category': self.category,
            'icon': self.icon,
            'is_active': self.is_active
        }


class MoviePackCache(db.Model):
    """Cache of movies in each pack - refreshed periodically for dynamic packs"""
    __tablename__ = 'movie_pack_cache'

    id = db.Column(db.Integer, primary_key=True)
    pack_id = db.Column(db.Integer, db.ForeignKey('movie_packs.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    position = db.Column(db.Integer)  # Order in pack (1-100)
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    pack = db.relationship('MoviePack', back_populates='cached_movies')
    movie = db.relationship('Movie')

    __table_args__ = (
        UniqueConstraint('pack_id', 'movie_id', name='_pack_movie_uc'),
        db.Index('idx_pack_cache_pack', 'pack_id'),
    )


class TMDBApiUsage(db.Model):
    """Track TMDB API usage for rate limiting"""
    __tablename__ = 'tmdb_api_usage'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    call_count = db.Column(db.Integer, default=0)
    last_call_at = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('idx_tmdb_usage_date', 'date'),
    )


class OMDBApiUsage(db.Model):
    """Track OMDB API usage for rate limiting"""
    __tablename__ = 'omdb_api_usage'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    call_count = db.Column(db.Integer, default=0)
    last_call_at = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('idx_omdb_usage_date', 'date'),
    )


class SeenMovie(db.Model):
    """Track movies marked as seen (watched) by circle"""
    __tablename__ = 'seen_movies'

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    marked_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    movie = db.relationship('Movie')
    circle = db.relationship('Circle')
    marked_by = db.relationship('User')

    __table_args__ = (
        UniqueConstraint('movie_id', 'circle_id', name='_movie_circle_seen_uc'),
        db.Index('idx_seen_movies_circle', 'circle_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'movie_id': self.movie_id,
            'circle_id': self.circle_id,
            'marked_by': {
                'id': self.marked_by.id,
                'display_name': self.marked_by.display_name or self.marked_by.email
            },
            'marked_at': self.marked_at.isoformat()
        }


class MovieComment(db.Model):
    """Comments on movies within a circle"""
    __tablename__ = 'movie_comments'

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    movie = db.relationship('Movie')
    circle = db.relationship('Circle')
    user = db.relationship('User')

    __table_args__ = (
        db.Index('idx_movie_comments_movie_circle', 'movie_id', 'circle_id'),
    )

    def to_dict(self, current_user_id=None):
        return {
            'id': self.id,
            'movie_id': self.movie_id,
            'content': self.content,
            'author': {
                'id': self.user.id,
                'display_name': self.user.display_name or self.user.email
            },
            'created_at': self.created_at.isoformat(),
            'can_delete': current_user_id == self.user_id
        }


class UserBoostStats(db.Model):
    """Track daily boosted movie counts per user per circle"""
    __tablename__ = 'user_boost_stats'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    boosted_count = db.Column(db.Integer, default=0)

    # Relationships
    user = db.relationship('User')
    circle = db.relationship('Circle')

    __table_args__ = (
        UniqueConstraint('user_id', 'circle_id', 'date', name='_user_circle_date_boost_uc'),
        db.Index('idx_user_boost_stats_user_circle_date', 'user_id', 'circle_id', 'date'),
    )
