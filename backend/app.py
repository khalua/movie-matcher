from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, UniqueConstraint
import os
from datetime import timedelta
import random
import requests
from flask import request, jsonify
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://192.168.7.38:3000"]}})

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movie_matcher.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this!
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

OMDB_API_KEY = os.environ.get('OMDB_API_KEY')


# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    seen_movies = db.relationship('Movie', secondary='user_seen_movies', lazy='dynamic')
    liked_movies = db.relationship('Movie', secondary='user_likes', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # Make sure year is not nullable
    poster = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.String(10), nullable=False)
    length = db.Column(db.String(20), nullable=False)
    starring = db.Column(db.String(200), nullable=False)
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_by = db.relationship('User', backref=db.backref('added_movies', lazy='dynamic'))

    __table_args__ = (UniqueConstraint('title', 'year', name='_title_year_uc'),)


user_likes = db.Table('user_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('movie_id', db.Integer, db.ForeignKey('movie.id'), primary_key=True)
)

user_seen_movies = db.Table('user_seen_movies',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('movie_id', db.Integer, db.ForeignKey('movie.id'), primary_key=True)
)

# Routes
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
            body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
            h1 { color: #333; }
            h2 { color: #666; }
            code { background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>Welcome to the Movie Matcher API</h1>
        <p>This API provides endpoints for user authentication and movie matching functionality.</p>
        <h2>Available Endpoints:</h2>
        <ul>
            <li><code>POST /api/auth/register</code> - Register a new user</li>
            <li><code>POST /api/auth/login</code> - Log in a user</li>
            <li><code>GET /api/movies/random</code> - Get a random movie (requires authentication)</li>
            <li><code>POST /api/movies/like</code> - Like a movie (requires authentication)</li>
            <li><code>GET /api/users/matches</code> - Get movie matches (requires authentication)</li>
        </ul>
        <p>For more information on how to use these endpoints, please refer to the API documentation.</p>
    </body>
    </html>
    '''
    return render_template_string(api_info)


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"message": "Invalid username or password"}), 401

import logging
import random

@app.route('/api/movies/random', methods=['GET'])
@jwt_required()
def get_random_movie():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    
    logging.info(f"Fetching random movie for user: {current_user}")
    
    # Get all movie IDs
    all_movie_ids = db.session.query(Movie.id).all()
    all_movie_ids = [movie_id for (movie_id,) in all_movie_ids]
    logging.info(f"Total movies in database: {len(all_movie_ids)}")
    
    # Get IDs of movies the user has already seen
    seen_movie_ids = db.session.query(user_seen_movies.c.movie_id).filter(user_seen_movies.c.user_id == user.id).all()
    seen_movie_ids = [movie_id for (movie_id,) in seen_movie_ids]
    logging.info(f"Movies seen by user: {len(seen_movie_ids)}")
    
    # Find unseen movie IDs
    unseen_movie_ids = list(set(all_movie_ids) - set(seen_movie_ids))
    logging.info(f"Unseen movies: {len(unseen_movie_ids)}")
    
    if not unseen_movie_ids:
        logging.info("No unseen movies found")
        return jsonify({"message": "No more unseen movies"}), 404
    
    # Get a random unseen movie
    random_movie_id = random.choice(unseen_movie_ids)
    movie = Movie.query.get(random_movie_id)
    
    if not movie:
        logging.error(f"Movie with id {random_movie_id} not found in database")
        return jsonify({"message": "Error fetching movie", "error": "Movie not found in database"}), 500
    
    logging.info(f"Selected movie: {movie.title}")
    
    return jsonify({
        "id": movie.id,
        "title": movie.title,
        "year": movie.year,
        "poster": movie.poster,
        "description": movie.description,
        "genre": movie.genre,
        "rating": movie.rating,
        "length": movie.length,
        "starring": movie.starring
    }), 200


@app.route('/api/movies/like', methods=['POST'])
@jwt_required()
def like_movie():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    data = request.get_json()
    movie_id = data.get('movieId')

    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({"message": "Movie not found"}), 404

    if movie not in user.liked_movies:
        user.liked_movies.append(movie)
    
    # Mark the movie as seen
    if movie not in user.seen_movies:
        user.seen_movies.append(movie)
    
    db.session.commit()

    return jsonify({"message": "Movie liked and marked as seen successfully"}), 200

@app.route('/api/movies/dislike', methods=['POST'])
@jwt_required()
def dislike_movie():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    data = request.get_json()
    movie_id = data.get('movieId')

    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({"message": "Movie not found"}), 404

    # Just mark the movie as seen (we don't store dislikes)
    if movie not in user.seen_movies:
        user.seen_movies.append(movie)
    
    db.session.commit()

    return jsonify({"message": "Movie marked as seen successfully"}), 200

@app.route('/api/movies/matches', methods=['POST'])
@jwt_required()
def get_matches():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    
    logging.info(f"Fetching matches for user: {current_user}")
    
    if not user:
        logging.warning(f"User not found: {current_user}")
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json()
    selected_user_ids = data.get('userIds', [])
    
    if len(selected_user_ids) < 2:
        return jsonify({"error": "Please select at least two users to compare matches"}), 400
    
    try:
        # Find movies liked by all selected users
        matched_movies = (
            db.session.query(Movie)
            .join(user_likes)
            .filter(user_likes.c.user_id.in_(selected_user_ids))
            .group_by(Movie.id)
            .having(func.count(func.distinct(user_likes.c.user_id)) == len(selected_user_ids))
            .all()
        )
        
        result = []
        for movie in matched_movies:
            # Get all selected users who liked this movie
            matched_users = (
                User.query
                .join(user_likes)
                .filter(user_likes.c.movie_id == movie.id)
                .filter(User.id.in_(selected_user_ids))
                .all()
            )
            
            result.append({
                "id": movie.id,
                "title": movie.title,
                "poster": movie.poster,
                "description": movie.description,
                "genre": movie.genre,
                "rating": movie.rating,
                "length": movie.length,
                "starring": movie.starring,
                "match_count": len(matched_users),
                "matched_users": [{"id": u.id, "username": u.username} for u in matched_users]
            })
        
        logging.info(f"Matches found: {len(result)}")
        return jsonify(result), 200  # This will return an empty list if no matches are found
    except Exception as e:
        logging.error(f"Error fetching matches: {str(e)}")
        return jsonify({"error": "An error occurred while fetching matches"}), 500

@app.route('/api/movies/search', methods=['GET'])
@jwt_required()
def search_movie():
    query = request.args.get('query', '')
    if not query:
        return jsonify({"error": "No search query provided"}), 400

    # Split the query into individual movie titles
    movie_titles = [title.strip() for title in query.split(';') if title.strip()]

    results = []
    for title in movie_titles:
        response = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}")
        if response.status_code == 200:
            movie_data = response.json()
            if movie_data.get('Response') == 'True':
                results.append(movie_data)

    if not results:
        return jsonify({"error": "No movies found"}), 404

    return jsonify(results), 200

# add_movie route
@app.route('/api/movies/add', methods=['POST'])
@jwt_required()
def add_movie():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()

    new_movie = Movie(
        title=data['Title'],
        poster=data['Poster'],
        description=data['Plot'],
        genre=data['Genre'],
        rating=data['imdbRating'],
        length=data['Runtime'],
        starring=data['Actors'],
        year=int(data['Year']) if data.get('Year') else None,
        added_by=user
    )

    db.session.add(new_movie)
    db.session.commit()

    return jsonify({"message": "Movie added successfully", "id": new_movie.id}), 201

@app.route('/api/movies/all', methods=['GET'])
@jwt_required()
def get_all_movies():
    try:
        # Get all users
        all_users = User.query.all()
        all_user_ids = [user.id for user in all_users]

        # Query to get all movies with their like counts, users who have seen them, and the user who added them
        movies_data = db.session.query(
            Movie,
            func.count(user_likes.c.user_id).label('likes_count'),
            func.group_concat(user_seen_movies.c.user_id).label('seen_by_users'),
            User
        ).select_from(Movie) \
         .outerjoin(user_likes, Movie.id == user_likes.c.movie_id) \
         .outerjoin(user_seen_movies, Movie.id == user_seen_movies.c.movie_id) \
         .join(User, Movie.added_by_id == User.id) \
         .group_by(Movie.id) \
         .all()

        result = []
        for movie, likes_count, seen_by_users, added_by_user in movies_data:
            seen_user_ids = set(map(int, seen_by_users.split(','))) if seen_by_users else set()
            unseen_user_ids = set(all_user_ids) - seen_user_ids
            unseen_users = User.query.filter(User.id.in_(unseen_user_ids)).all()

            result.append({
                "id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "poster": movie.poster,
                "description": movie.description,
                "genre": movie.genre,
                "rating": movie.rating,
                "length": movie.length,
                "starring": movie.starring,
                "likes_count": likes_count,
                "unseen_by": [{"id": user.id, "username": user.username} for user in unseen_users],
                "added_by": {
                    "id": added_by_user.id,
                    "username": added_by_user.username
                }
            })

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error fetching all movies: {str(e)}")
        return jsonify({"error": "An error occurred while fetching movies"}), 500

@app.route('/api/debug/movie-counts', methods=['GET'])
@jwt_required()
def debug_movie_counts():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    
    total_movies = Movie.query.count()
    seen_movies = user.seen_movies.count()
    
    return jsonify({
        "total_movies": total_movies,
        "seen_movies": seen_movies,
        "unseen_movies": total_movies - seen_movies
    }), 200

@app.route('/api/debug/all-movies', methods=['GET'])
@jwt_required()
def get_all_movies_debug():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    
    all_movies = Movie.query.all()
    result = []
    for movie in all_movies:
        result.append({
            "id": movie.id,
            "title": movie.title,
            "seen": movie in user.seen_movies
        })
    
    return jsonify(result), 200

@app.route('/api/user/info', methods=['GET'])
@jwt_required()
def get_user_info():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    if user:
        return jsonify({"username": user.username}), 200
    else:
        return jsonify({"error": "User not found"}), 404

@app.route('/api/user/movie-history', methods=['GET'])
@jwt_required()
def get_movie_history():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    if user:
        seen_movies = user.seen_movies.all()
        liked_movies = user.liked_movies.all()
        
        movie_history = []
        for movie in seen_movies:
            movie_history.append({
                "title": movie.title,
                "liked": movie in liked_movies
            })
        
        return jsonify(movie_history), 200
    else:
        return jsonify({"error": "User not found"}), 404
    
@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_all_users():
    try:
        users = User.query.all()
        return jsonify([{"id": user.id, "username": user.username} for user in users]), 200
    except Exception as e:
        logging.error(f"Error fetching users: {str(e)}")
        return jsonify({"error": "An error occurred while fetching users"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)