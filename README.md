# Movie Matcher

A collaborative movie selection application that helps groups decide what to watch together. Users can swipe through movies Tinder-style, and the app identifies films that everyone wants to see.

## Features

### Multi-Tenant Architecture
- **Friend Circles**: Create isolated groups for different friend groups, family, coworkers, etc.
- **Circle Management**: Admins can invite members, manage permissions, and curate movie selections
- **Cross-Circle Awareness**: See if you've already swiped a movie in other circles

### Movie Discovery
- **Tinder-Style Swiping**: Intuitive left/right swipe interface for movie preferences
- **OMDB Integration**: Rich movie metadata including posters, descriptions, cast, and ratings
- **TMDB Integration**: Real-time streaming availability information
- **Smart Recommendations**: Only shows movies you haven't seen yet within each circle

### Collaboration
- **Match Detection**: Automatically identifies movies that all selected users liked
- **Per-Circle History**: Swipe preferences are isolated to each circle
- **Invitation System**: Share secure invite codes to add friends to circles

### User Experience
- **Email-Based Authentication**: Simple, secure login system
- **Circle Switching**: Easily switch between different friend groups
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Tech Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens with Flask-JWT-Extended
- **APIs**: OMDB API for movie data, TMDB API for streaming info

### Frontend
- **Framework**: React
- **State Management**: Context API for circle management
- **HTTP Client**: Axios with automatic auth headers
- **Styling**: CSS with responsive design

### Deployment
- **Platform**: Dokku-ready (Heroku-compatible)
- **Process Manager**: Gunicorn for production
- **Environment**: Environment variable-based configuration

## Getting Started

### Prerequisites
- Python 3.12 or 3.13
- PostgreSQL
- Node.js and npm
- OMDB API key (free at http://www.omdbapi.com/)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/khalua/movie-matcher.git
cd movie-matcher
```

2. Set up PostgreSQL:
```bash
createdb movie_matcher
```

3. Configure backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your API keys
```

4. Initialize database:
```bash
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"

# Optional: Create test data
python scripts/create_test_data.py
```

5. Start backend server:
```bash
flask run --host=0.0.0.0 --port=5000
```

6. In a new terminal, start frontend:
```bash
cd frontend
npm install
npm start
```

7. Open http://localhost:3000 in your browser

## Usage

### Creating Your First Circle

1. Register an account with your email
2. After login, navigate to "Manage Circles"
3. Create a new circle and give it a name
4. Generate an invitation code to share with friends
5. Add movies using the "Add Movie" search feature

### Swiping Movies

1. Select your circle from the dropdown in the header
2. Navigate to "Swipe Movies"
3. Swipe right (like) or left (dislike) on each movie
4. Movies you've already reviewed won't appear again in this circle

### Finding Matches

1. Go to "View Matches"
2. Select which circle members to compare
3. The app shows all movies that everyone selected has liked
4. Perfect for deciding what to watch together

## Configuration

### Environment Variables

The backend requires these environment variables (set in `.env`):

```bash
DATABASE_URL=postgresql://localhost/movie_matcher
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
OMDB_API_KEY=<your-omdb-api-key>
TMDB_API_KEY=<your-tmdb-api-key>  # Optional
CORS_ORIGINS=http://localhost:3000
FLASK_ENV=development
```

### API Keys

- **OMDB API**: Get a free key at http://www.omdbapi.com/
- **TMDB API**: Optional, for streaming availability. Get at https://www.themoviedb.org/settings/api

## Deployment

The application is configured for deployment on Dokku or Heroku:

1. Set up your Dokku app and PostgreSQL database
2. Configure environment variables on your Dokku instance
3. Push to deploy:
```bash
git push dokku main
```

See [SETUP.md](SETUP.md) for detailed deployment instructions.

## Architecture

### Database Schema

- **Users**: Email-based authentication with JWT tokens
- **Circles**: Isolated groups with admin permissions
- **CircleMembers**: Many-to-many relationship between users and circles
- **Movies**: Global movie pool with OMDB metadata
- **CircleMovies**: Association between movies and circles
- **UserSwipes**: Per-circle swipe history (like/dislike)
- **Invitations**: Time-limited invitation codes for joining circles

### Authorization

The app uses a header-based authorization system:
- `Authorization: Bearer <jwt-token>` for user authentication
- `X-Circle-Id: <circle-id>` for circle-scoped operations

All circle-related endpoints validate that the user is a member of the specified circle before allowing access.

## Development

### Running Tests

```bash
# Backend tests (if implemented)
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Project Structure

```
movie-matcher/
├── backend/
│   ├── app.py              # Application factory
│   ├── config.py           # Environment configuration
│   ├── models.py           # Database models
│   ├── auth.py             # Authorization decorators
│   ├── routes/             # API endpoints
│   ├── services/           # Business logic
│   └── scripts/            # Utility scripts
├── frontend/
│   └── src/
│       ├── components/     # React components
│       ├── contexts/       # State management
│       ├── api/            # API client
│       └── App.js          # Main application
└── README.md
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is available for personal and educational use.

## Acknowledgments

- Movie data provided by OMDB API
- Streaming availability from TMDB API
- Built with assistance from Claude (Anthropic)

## Support

For detailed setup instructions, see [SETUP.md](SETUP.md)

For issues or questions, please open an issue on GitHub.
