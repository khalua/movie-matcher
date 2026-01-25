import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    # Database
    # Fix for Heroku/Dokku postgres:// URLs (SQLAlchemy requires postgresql://)
    _database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/movie_matcher')
    if _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable must be set")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # API Keys
    OMDB_API_KEY = os.getenv('OMDB_API_KEY')
    TMDB_API_KEY = os.getenv('TMDB_API_KEY')

    # CORS - set via environment variable in production
    # Use "*" for development to allow any origin (localhost, IP addresses, etc.)
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',') if os.getenv('CORS_ORIGINS') else ['*']

    # App
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # In production, require API keys
    # Note: CORS wildcards are OK when frontend is served from same origin
    def __init__(self):
        super().__init__()
        if not self.OMDB_API_KEY:
            raise ValueError("OMDB_API_KEY must be set in production")


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
