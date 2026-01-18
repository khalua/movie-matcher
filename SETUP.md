# Movie Matcher - Multi-Tenant Setup Guide

## 🎉 Migration Complete!

Your Movie Matcher app has been successfully transformed from a single-tenant SQLite application to a multi-tenant PostgreSQL system with circle-based isolation!

## 📋 What's New

### Architecture Changes
- **Email-based authentication** (instead of username)
- **Circles** - Create isolated movie groups
- **Multi-circle support** - Users can belong to multiple circles
- **Circle-scoped swipes** - Swipe history tracked per circle
- **Cross-circle awareness** - See if you've swiped a movie in other circles
- **Invitation system** - Admins generate codes to invite users
- **Site admin** - First user becomes site admin
- **PostgreSQL** - Production-ready database

## 🚀 Quick Start (Local Development)

### 1. Set Up PostgreSQL

```bash
# Create database
createdb movie_matcher
```

### 2. Configure Backend

```bash
cd backend

# Create .env file from template
cp .env.example .env

# Generate JWT secret and add to .env
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Add your API keys to .env
# Edit .env and add:
# OMDB_API_KEY=your-omdb-key
# TMDB_API_KEY=your-tmdb-key (optional)
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
# Create all tables
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"

# Create test data (optional)
python scripts/create_test_data.py
```

### 5. Run Backend

```bash
# Start Flask server
flask run --host=0.0.0.0 --port=5000
```

### 6. Run Frontend

```bash
# In a new terminal
cd frontend
npm install
npm start
```

### 7. Access the App

Open http://localhost:3000

## 🔐 Test Accounts

After running `create_test_data.py`:

- **tony@example.com** / password (Site Admin)
- **alice@example.com** / password
- **bob@example.com** / password
- **charlie@example.com** / password

## 📁 New File Structure

### Backend
```
backend/
├── app.py                  # Application factory
├── config.py               # Environment-based config
├── models.py               # Database models
├── auth.py                 # Authorization decorators
├── requirements.txt        # Python dependencies
├── Procfile                # Dokku deployment
├── app.json                # Dokku config
├── .env.example            # Environment template
├── routes/
│   ├── auth.py            # Authentication endpoints
│   ├── movies.py          # Movie endpoints
│   ├── circles.py         # Circle management
│   └── admin.py           # Site admin endpoints
├── services/
│   ├── seed_service.py    # Movie seeding
│   └── analytics_service.py
└── scripts/
    └── create_test_data.py
```

### Frontend
```
frontend/src/
├── App.js                  # CircleProvider integration
├── api/
│   └── client.js          # Axios with interceptors
├── contexts/
│   └── CircleContext.js   # Circle state management
├── components/
│   ├── CircleSelector.js  # Circle dropdown
│   ├── CircleSelector.css
│   ├── CircleManagement.js
│   └── CircleManagement.css
├── MovieSwiper.js         # Updated with cross-circle badges
├── AddMovie.js            # Multi-circle selection
├── Matches.js             # Circle-scoped
└── AllMovies.js           # Circle-scoped
```

## 🎯 Key Features

### Circle Management
- **Create circles**: Any user can create a circle (becomes admin)
- **Invite members**: Admins generate invite codes
- **Switch circles**: Dropdown in header to switch between circles
- **Circle isolation**: Movies, swipes, and matches are circle-specific

### Cross-Circle Awareness
When swiping a movie, you'll see badges showing if you've already swiped it in other circles:
- "Already swiped in: Family Circle (👍)"
- "Already swiped in: Work Friends (👎)"

### Multi-Circle Movie Adding
When adding movies:
- Select which circles to add the movie to
- All circles checked by default
- Movie added to global pool if new

### Admin Features
- **Circle admins**: Manage their circle(s), generate invites, remove members
- **Site admin**: First user, can view global analytics, seed all circles

## 🔧 API Changes

### Headers Required
All circle-scoped endpoints now require:
```
Authorization: Bearer <token>
X-Circle-Id: <circle_id>
```

The frontend automatically adds these via axios interceptors.

### New Endpoints
- `GET /api/circles` - List user's circles
- `POST /api/circles` - Create circle
- `POST /api/circles/:id/invitations` - Generate invite code
- `DELETE /api/circles/:id/members/:uid` - Remove member
- `GET /api/admin/analytics` - Global analytics (site admin)

### Modified Endpoints
- `POST /api/auth/login` - Now returns user + circles
- `POST /api/auth/register` - Email-based
- `GET /api/movies/random` - Returns cross-circle swipe data
- `POST /api/movies/add` - Accepts circle_ids[]

## 🚢 Deploying to Dokku

### 1. Set Up Dokku App

```bash
# On your Dokku server
dokku apps:create movie-matcher

# Provision PostgreSQL
dokku postgres:create movie-matcher-db
dokku postgres:link movie-matcher-db movie-matcher
```

### 2. Configure Environment

```bash
dokku config:set movie-matcher \
  JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  OMDB_API_KEY="your-omdb-key" \
  TMDB_API_KEY="your-tmdb-key" \
  CORS_ORIGINS="https://movie-matcher.yourdomain.com" \
  FLASK_ENV="production"
```

### 3. Deploy

```bash
# On your local machine
git remote add dokku dokku@your-server:movie-matcher
git push dokku main
```

### 4. Initialize Database

```bash
# Run on Dokku
dokku run movie-matcher python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Verify PostgreSQL is running
psql -l
```

### CORS Errors
Update `CORS_ORIGINS` in `.env` to include your frontend URL.

### Missing API Keys
Ensure `OMDB_API_KEY` is set in `.env` file.

### Circle Context Errors
Check that `X-Circle-Id` header is being sent (open browser DevTools > Network).

## 📚 Next Steps

1. **Create your first circle**: Login and go to "Manage Circles"
2. **Invite friends**: Generate an invite code and share it
3. **Add movies**: Use "Add Movie" to populate your circle
4. **Start swiping**: Review movies in "Review Movies"
5. **Find matches**: Use "View Matches" to find movies everyone wants to watch

## 🎬 Enjoy Your Multi-Tenant Movie Matcher!

Need help? Check the logs:
```bash
# Backend logs
cd backend && flask run

# Frontend logs
cd frontend && npm start
```
