import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://localhost/movie_matcher'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable must be set")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # API Keys
    OMDB_API_KEY = os.getenv('OMDB_API_KEY')
    TMDB_API_KEY = os.getenv('TMDB_API_KEY')

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

    # App
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # In production, require all API keys
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
