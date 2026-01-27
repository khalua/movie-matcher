# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Frontend (React)
- **Start development server**: `cd frontend && npm start` (runs on http://localhost:3000)
- **Build for production**: `cd frontend && npm run build` 
- **Run tests**: `cd frontend && npm test`
- **Install dependencies**: `cd frontend && npm install`

### Backend (Flask)
- **Start development server**: 
  ```bash
  cd backend
  source ./venv/bin/activate
  flask run --host=0.0.0.0 --port=5000
  ```
- **Environment setup**: Create and activate virtual environment in `backend/venv/`
- **Database**: PostgreSQL (configured via DATABASE_URL in backend/.env)

### Environment Variables
- **DATABASE_URL**: PostgreSQL connection string (required)
- **OMDB_API_KEY**: Required for movie search functionality
- **REACT_APP_API_URL**: Frontend API URL (defaults to http://localhost:5001)

## Architecture Overview

This is a full-stack movie matching application with a React frontend and Flask backend.

### Frontend Structure
- **Main App** (`frontend/src/App.js`): Handles authentication and navigation between views
- **MovieSwiper** (`frontend/src/MovieSwiper.js`): Tinder-style movie swiping interface
- **Matches** (`frontend/src/Matches.js`): View shared movie preferences between users
- **AddMovie** (`frontend/src/AddMovie.js`): Search and add movies via OMDB API
- **AllMovies** (`frontend/src/AllMovies.js`): Administrative view of all movies in database

### Backend Structure
- **Flask API** (`backend/app.py`): RESTful API with JWT authentication
- **Database Models**: User, Movie, and many-to-many relationships for likes/seen movies
- **Key Features**: 
  - User authentication with JWT tokens
  - Movie recommendation system (shows unseen movies)
  - OMDB API integration for movie metadata
  - Cross-user movie matching algorithm

### Database Schema (Multi-tenant with Circles)
- **Users**: Email-based auth with display names, site admin flag
- **Circles**: Groups for multi-tenancy isolation
- **CircleMember**: User membership in circles with roles (admin/member)
- **Movies**: Full metadata (title, year, poster, description, genre, rating, length, starring)
- **CircleMovie**: Movies associated with circles, with `is_system_seeded` flag
- **UserSwipe**: Like/dislike actions scoped to circles
- **Invitation**: Invite codes for joining circles
- **MatchEvent**: Tracks when all circle members like a movie

### API Endpoints
- Authentication: `/api/auth/login`, `/api/auth/register`, `/api/auth/profile`
- Circles: `/api/circles`, `/api/circles/<id>/members`, `/api/circles/<id>/invitations`
- Movies: `/api/movies/random`, `/api/movies/like`, `/api/movies/dislike`, `/api/movies/add`, `/api/movies/all`
- Matching: `/api/movies/matches` (finds movies liked by multiple selected users)
- Admin (site admin only): `/api/admin/analytics`, `/api/admin/circles`, `/api/admin/add-movie-all-circles`

### Database Migrations

This project uses a simple migration system that runs automatically on deploy via Dokku's release phase.

**Migration files location**: `backend/scripts/migrations/`

**Creating a new migration** (required when adding/modifying database columns or tables):
1. Create a new file: `backend/scripts/migrations/NNN_description.py` (e.g., `002_add_user_preferences.py`)
2. Implement a `migrate()` function that:
   - Checks if changes are already applied (idempotent)
   - Applies schema changes using raw SQL via `db.engine.connect()`
   - Calls `db.create_all()` for new tables

**Migration template**:
```python
#!/usr/bin/env python3
"""Migration NNN: Description of changes"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import text, inspect

def check_column_exists(inspector, table_name, column_name):
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        db.create_all()  # Creates new tables safely

        # Add columns with existence checks
        if not check_column_exists(inspector, 'table_name', 'new_column'):
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE table_name ADD COLUMN new_column TYPE'))
                conn.commit()

if __name__ == '__main__':
    migrate()
```

**Running migrations locally**: `python backend/scripts/run_migrations.py`

**On deploy**: Migrations run automatically via Procfile release phase before the web process starts.

### Deployment
- **Deploy to production**: `git push dokku` (migrations run automatically)
- Dokku runs `release: python backend/scripts/run_migrations.py` before starting the web process

### Development Notes
- Backend runs on port 5001, frontend on port 3000
- CORS configured for local development
- JWT tokens expire after 1 hour
- Frontend notes mention build order: "DO THIS ONE FIRST! TC" for npm run build, "DO THIS ONE SECOND! TC" for npm start