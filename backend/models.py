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
    password_hash = db.Column(db.String(200), nullable=False)
    is_site_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    circles = db.relationship('CircleMember', back_populates='user', cascade='all, delete-orphan')
    swipes = db.relationship('UserSwipe', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'display_name': self.display_name,
            'is_site_admin': self.is_site_admin
        }


class Circle(db.Model):
    """Circle (group) model for multi-tenancy"""
    __tablename__ = 'circles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    members = db.relationship('CircleMember', back_populates='circle', cascade='all, delete-orphan')
    movies = db.relationship('CircleMovie', back_populates='circle', cascade='all, delete-orphan')
    invitations = db.relationship('Invitation', back_populates='circle', cascade='all, delete-orphan')

    def to_dict(self, user_id=None):
        """Convert circle to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'member_count': len(self.members)
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
    added_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    circle = db.relationship('Circle', back_populates='movies')
    movie = db.relationship('Movie', back_populates='circles')

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
