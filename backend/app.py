from flask import Flask, render_template_string, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config
from models import db
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# File handler (rotates at 1MB, keeps 5 backups)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])


def create_app(config_name=None):
    """Application factory pattern"""
    # Path to React build folder
    frontend_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'build')

    app = Flask(__name__, static_folder=frontend_folder, static_url_path='')

    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)

    # CORS - allow preflight requests and handle all origins
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Circle-Id"]
        }
    })

    # Register blueprints
    from routes.auth import auth_bp
    from routes.movies import movies_bp
    from routes.circles import circles_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(movies_bp, url_prefix='/api/movies')
    app.register_blueprint(circles_bp, url_prefix='/api/circles')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # Serve React app
    @app.route('/')
    def serve():
        return send_from_directory(app.static_folder, 'index.html')

    # Catch-all route for React Router (client-side routing)
    @app.errorhandler(404)
    def not_found(e):
        # If it's an API route, return JSON error
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify(error='Not found'), 404
        # Otherwise serve React app for client-side routing
        return send_from_directory(app.static_folder, 'index.html')

    # Add users endpoint (circle-scoped)
    @app.route('/api/users', methods=['GET'])
    def get_users():
        """Get users in current circle - moved from old routes"""
        from flask_jwt_extended import jwt_required, get_jwt_identity
        from auth import circle_required
        from models import User

        @jwt_required()
        @circle_required
        def _get_users(circle, user, member):
            """Get all users in current circle"""
            users = []
            for membership in circle.members:
                u = membership.user
                users.append({
                    'id': u.id,
                    'display_name': u.display_name or u.email,
                    'email': u.email
                })
            return jsonify(users), 200

        return _get_users()

    # Verify database connection on startup
    with app.app_context():
        try:
            db.engine.connect()
            logging.info("Database connection verified")
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            raise RuntimeError(
                "Could not connect to database. Is PostgreSQL running?"
            ) from e

    return app


# For running directly
if __name__ == '__main__':
    app = create_app()

    # Create tables if they don't exist (for development)
    with app.app_context():
        db.create_all()

    app.run(debug=True, host='0.0.0.0', port=5000)
