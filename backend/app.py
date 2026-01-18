from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config
from models import db
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)


def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)

    # CORS
    CORS(app, resources={
        r"/api/*": {"origins": app.config['CORS_ORIGINS']}
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

    # Home route
    @app.route('/')
    def home():
        api_info = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Movie Matcher API</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }
                h1 { color: #333; }
                h2 { color: #666; margin-top: 30px; }
                code { background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: monospace; }
                ul { line-height: 2; }
                .section { margin-bottom: 30px; }
            </style>
        </head>
        <body>
            <h1>🎬 Movie Matcher API</h1>
            <p>Multi-tenant movie matching application with circle-based isolation.</p>

            <div class="section">
                <h2>Authentication Endpoints</h2>
                <ul>
                    <li><code>POST /api/auth/register</code> - Register a new user (email-based)</li>
                    <li><code>POST /api/auth/login</code> - Log in and get JWT token + circles</li>
                    <li><code>POST /api/auth/invitations/redeem</code> - Redeem invitation code</li>
                </ul>
            </div>

            <div class="section">
                <h2>Circle Management</h2>
                <ul>
                    <li><code>GET /api/circles</code> - List user's circles</li>
                    <li><code>POST /api/circles</code> - Create new circle</li>
                    <li><code>GET /api/circles/:id</code> - Get circle details</li>
                    <li><code>PUT /api/circles/:id</code> - Update circle (admin only)</li>
                    <li><code>DELETE /api/circles/:id</code> - Delete circle (admin only)</li>
                    <li><code>GET /api/circles/:id/members</code> - List circle members</li>
                    <li><code>DELETE /api/circles/:id/members/:uid</code> - Remove member (admin)</li>
                    <li><code>POST /api/circles/:id/invitations</code> - Generate invite code (admin)</li>
                    <li><code>GET /api/circles/:id/analytics</code> - Circle analytics (admin)</li>
                </ul>
            </div>

            <div class="section">
                <h2>Movie Endpoints</h2>
                <p><em>Note: All movie endpoints require <code>X-Circle-Id</code> header</em></p>
                <ul>
                    <li><code>GET /api/movies/random</code> - Get random unseen movie</li>
                    <li><code>POST /api/movies/like</code> - Like a movie</li>
                    <li><code>POST /api/movies/dislike</code> - Dislike a movie</li>
                    <li><code>POST /api/movies/matches</code> - Find matches with selected users</li>
                    <li><code>GET /api/movies/search</code> - Search OMDB for movies</li>
                    <li><code>POST /api/movies/add</code> - Add movie to circle(s)</li>
                    <li><code>GET /api/movies/all</code> - List all movies in circle</li>
                    <li><code>GET /api/movies/:id/streaming</code> - Get streaming availability</li>
                </ul>
            </div>

            <div class="section">
                <h2>Admin Endpoints</h2>
                <p><em>Site admin only</em></p>
                <ul>
                    <li><code>GET /api/admin/analytics</code> - Global analytics</li>
                    <li><code>GET /api/admin/circles</code> - List all circles</li>
                    <li><code>POST /api/admin/seed-circles</code> - Seed all circles with top_movies.txt</li>
                </ul>
            </div>

            <div class="section">
                <h2>Documentation</h2>
                <p>For detailed API documentation, see <code>CLAUDE.md</code> in the repository.</p>
            </div>
        </body>
        </html>
        '''
        return render_template_string(api_info)

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

    return app


# For running directly
if __name__ == '__main__':
    app = create_app()

    # Create tables if they don't exist (for development)
    with app.app_context():
        db.create_all()

    app.run(debug=True, host='0.0.0.0', port=5000)
