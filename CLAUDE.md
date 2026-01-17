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
- **Database**: SQLite database stored at `backend/instance/movie_matcher.db`

### Environment Variables
- **OMDB_API_KEY**: Required for movie search functionality
- **REACT_APP_API_URL**: Frontend API URL (defaults to http://localhost:5000)

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

### Database Schema
- **Users**: Basic auth with username/password
- **Movies**: Full metadata (title, year, poster, description, genre, rating, length, starring)
- **Relationships**: 
  - `user_likes`: Many-to-many for user movie preferences
  - `user_seen_movies`: Many-to-many for tracking viewed movies
  - `added_by`: Foreign key tracking who added each movie

### API Endpoints
- Authentication: `/api/auth/login`, `/api/auth/register`
- Movies: `/api/movies/random`, `/api/movies/like`, `/api/movies/dislike`, `/api/movies/add`
- Matching: `/api/movies/matches` (finds movies liked by multiple selected users)
- Admin: `/api/movies/all`, `/api/users`

### Development Notes
- Backend runs on port 5000, frontend on port 3000
- CORS configured for local development
- JWT tokens expire after 1 hour
- Frontend notes mention build order: "DO THIS ONE FIRST! TC" for npm run build, "DO THIS ONE SECOND! TC" for npm start