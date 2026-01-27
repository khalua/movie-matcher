# Movie Packs Feature - Design Document

**Status: IMPLEMENTED**

## Overview

Allow circle admins to bulk-add curated movie collections ("packs") to their circles. Packs come from two sources:
1. **Static packs** - Curated lists stored as files (Oscars, Classics, etc.)
2. **Dynamic packs** - Fetched from TMDB API (streaming services, genres)

## Pack Size

Packs contain their **full list of movies** - no arbitrary limit. Static packs are curated to appropriate sizes (e.g., ~95 Oscar winners, ~100 AFI films). Dynamic packs from TMDB will fetch up to **100 movies** per pack to balance comprehensiveness with API usage.

## Pack Categories

### Static Packs (Curated Files)
| Pack Name | Approx Size | Source | File |
|-----------|-------------|--------|------|
| Top 100 Classics | ~100 | Existing top_movies.txt | `packs/classics.txt` |
| Oscar Best Picture Winners | ~95 | Wikipedia/static | `packs/oscar_best_picture.txt` |
| AFI Top 100 | 100 | AFI list | `packs/afi_top_100.txt` |
| Foreign Film Essentials | ~50 | Curated | `packs/foreign_essentials.txt` |
| 90s Nostalgia | ~50 | Curated | `packs/90s_nostalgia.txt` |
| 80s Bangers | ~50 | Curated | `packs/80s_bangers.txt` |
| 70s Epics | ~40 | Curated | `packs/70s_epics.txt` |

### Dynamic Packs (TMDB API)
| Pack Name | TMDB Provider ID | Genre Filter | Max Size |
|-----------|------------------|--------------|----------|
| Netflix Picks | 8 | - | 100 |
| Prime Video Picks | 9 | - | 100 |
| Hulu Picks | 15 | - | 100 |
| Disney+ Picks | 337 | - | 100 |
| HBO Max Picks | 384 | - | 100 |
| Kanopy Picks | 191 | - | 100 |
| Action Hits | - | 28 | 100 |
| Comedy Favorites | - | 35 | 100 |
| Horror Essentials | - | 27 | 100 |
| Sci-Fi Classics | - | 878 | 100 |
| Documentary Gems | - | 99 | 100 |

## Database Changes

### New Table: `movie_pack`
```sql
CREATE TABLE movie_pack (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,           -- "Netflix Picks"
    slug VARCHAR(50) UNIQUE NOT NULL,     -- "netflix-picks"
    description TEXT,                      -- "Top 25 movies on Netflix"
    pack_type VARCHAR(20) NOT NULL,       -- "static" or "dynamic"
    source_config JSONB,                  -- {"provider_id": 8} or {"file": "oscar_best_picture.txt"}
    icon VARCHAR(50),                     -- emoji or icon identifier
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### New Table: `movie_pack_cache`
```sql
CREATE TABLE movie_pack_cache (
    id SERIAL PRIMARY KEY,
    pack_id INTEGER REFERENCES movie_pack(id),
    movie_id INTEGER REFERENCES movie(id),
    position INTEGER,                     -- order in pack (1-25)
    cached_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(pack_id, movie_id)
);
```

### Modify: `circle_movie` table
```sql
ALTER TABLE circle_movie
ADD COLUMN source_pack_id INTEGER REFERENCES movie_pack(id),
ADD COLUMN source_pack_name VARCHAR(100);  -- Denormalized for display
```

### New Table: `tmdb_api_usage`
```sql
CREATE TABLE tmdb_api_usage (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    call_count INTEGER DEFAULT 0,
    last_call_at TIMESTAMP,
    UNIQUE(date)
);
```

## API Endpoints

### Pack Management

#### `GET /api/packs`
List all available movie packs.

**Response:**
```json
{
  "packs": [
    {
      "id": 1,
      "name": "Netflix Picks",
      "slug": "netflix-picks",
      "description": "Top 25 popular movies currently on Netflix",
      "pack_type": "dynamic",
      "icon": "🎬",
      "movie_count": 25,
      "preview_posters": ["url1", "url2", "url3"]
    }
  ]
}
```

#### `GET /api/packs/<pack_id>/preview`
Preview movies in a pack before adding.

**Response:**
```json
{
  "pack": {
    "id": 1,
    "name": "Netflix Picks",
    "movies": [
      {
        "title": "Movie Title",
        "year": 2024,
        "poster": "url",
        "already_in_circle": false,
        "user_has_swiped": true,
        "user_swipe_action": "like"
      }
    ]
  }
}
```

#### `POST /api/circles/<circle_id>/add-pack`
Add a pack to a circle. **Circle admin only.**

**Request:**
```json
{
  "pack_id": 1
}
```

**Response:**
```json
{
  "message": "Added 23 movies from Netflix Picks",
  "added_count": 23,
  "skipped_count": 2,
  "skipped_reason": "already in circle"
}
```

### TMDB Rate Limit Monitoring

#### `GET /api/admin/tmdb-usage`
Get TMDB API usage stats. **Site admin only.**

**Response:**
```json
{
  "today": {
    "calls": 847,
    "limit": 1000,
    "percentage": 84.7
  },
  "this_week": [
    {"date": "2026-01-27", "calls": 847},
    {"date": "2026-01-26", "calls": 523}
  ],
  "alert_threshold": 800,
  "alert_triggered": true
}
```

## Backend Services

### New File: `backend/services/pack_service.py`

```python
class PackService:
    TMDB_DAILY_LIMIT = 1000  # Approximate, actual is per-second
    ALERT_THRESHOLD = 800

    def get_all_packs(self) -> List[Pack]:
        """Return all active packs with preview info"""

    def get_pack_movies(self, pack_id: int, circle_id: int = None) -> List[Movie]:
        """
        Get movies for a pack.
        - Static: read from file, fetch from OMDB if needed
        - Dynamic: check cache, refresh from TMDB if stale (>24h)
        If circle_id provided, include already_in_circle flag
        """

    def add_pack_to_circle(self, pack_id: int, circle_id: int, user_id: int) -> dict:
        """
        Add pack movies to circle.
        - Skip movies already in circle
        - Preserve user's existing swipes
        - Set source_pack_id and source_pack_name on CircleMovie
        - Track TMDB API usage
        """

    def refresh_dynamic_pack(self, pack_id: int) -> None:
        """
        Refresh a dynamic pack from TMDB.
        Called by scheduled job or manually by admin.
        """

    def check_tmdb_usage(self) -> dict:
        """Check today's TMDB API usage and alert if threshold reached"""

    def log_tmdb_call(self, count: int = 1) -> None:
        """Log TMDB API calls for rate tracking"""
```

### New File: `backend/services/tmdb_service.py`

```python
class TMDBService:
    BASE_URL = "https://api.themoviedb.org/3"

    # Provider IDs
    PROVIDERS = {
        'netflix': 8,
        'prime': 9,
        'hulu': 15,
        'disney': 337,
        'hbo': 384,
        'kanopy': 191,
    }

    # Genre IDs
    GENRES = {
        'action': 28,
        'comedy': 35,
        'horror': 27,
        'scifi': 878,
        'documentary': 99,
    }

    def discover_by_provider(self, provider_id: int, limit: int = 100) -> List[dict]:
        """
        Fetch top movies from a streaming provider.
        Uses: /discover/movie?with_watch_providers={id}&watch_region=US&sort_by=popularity.desc
        Paginates through results to get up to `limit` movies.
        """

    def discover_by_genre(self, genre_id: int, limit: int = 100) -> List[dict]:
        """
        Fetch top movies in a genre.
        Uses: /discover/movie?with_genres={id}&sort_by=vote_average.desc&vote_count.gte=1000
        Paginates through results to get up to `limit` movies.
        """

    def get_movie_details(self, tmdb_id: int) -> dict:
        """Get full movie details including credits"""

    def search_movie(self, title: str, year: int = None) -> dict:
        """Search for a specific movie"""
```

## Static Pack File Format

Location: `backend/misc/packs/`

Format (same as existing `top_movies.txt`):
```
The Shawshank Redemption; The Godfather; Schindler's List; ...
```

### Example Pack Contents

**80s Bangers** (`packs/80s_bangers.txt`):
```
The Breakfast Club; Ferris Bueller's Day Off; Back to the Future;
Die Hard; Ghostbusters; E.T. the Extra-Terrestrial; The Princess Bride;
Blade Runner; Raiders of the Lost Ark; Top Gun; Dirty Dancing;
Footloose; Sixteen Candles; Pretty in Pink; Say Anything;
The Terminator; Aliens; Predator; RoboCop; They Live;
Beetlejuice; Heathers; Fast Times at Ridgemont High; Risky Business;
Stand by Me; The Goonies; Gremlins; Big; Coming to America;
Beverly Hills Cop; Lethal Weapon; The Untouchables; Scarface;
Full Metal Jacket; Platoon; Raging Bull; The Shining; Blue Velvet;
Do the Right Thing; When Harry Met Sally; Moonstruck; Working Girl;
The Lost Boys; A Nightmare on Elm Street; The Thing; An American Werewolf in London;
Flashdance; Footloose; Purple Rain; La Bamba; ...
```

**70s Epics** (`packs/70s_epics.txt`):
```
The Godfather; The Godfather Part II; Chinatown; Dog Day Afternoon;
Apocalypse Now; Taxi Driver; One Flew Over the Cuckoo's Nest;
Network; All the President's Men; The Conversation; Serpico;
Reds; Barry Lyndon; The Deer Hunter; Coming Home;
Annie Hall; Manhattan; Nashville; McCabe & Mrs. Miller;
A Clockwork Orange; The Exorcist; Jaws; Star Wars;
Close Encounters of the Third Kind; Alien; Superman;
Rocky; The French Connection; The Sting; Papillon;
Deliverance; Marathon Man; Three Days of the Condor;
Carrie; The Omen; Halloween; Suspiria;
Saturday Night Fever; Grease; American Graffiti; ...
```

## Frontend Changes

### New Component: `PackSelector.js`
Modal/page for browsing and adding packs.

```jsx
// Features:
// - Grid of pack cards with icons and descriptions
// - "Preview" button to see movies before adding
// - "Add to Circle" button (circle admins only)
// - Shows overlap indicator (e.g., "3 movies already in your circle")
// - Filter by category (Streaming, Genre, Curated)
```

### Integration Points

1. **Circle Creation Flow**: After creating circle, prompt with PackSelector
2. **Circle Settings**: New "Movie Packs" tab for admins
3. **Movie Cards**: Show pack attribution badge if from a pack

### UI Mockup (Text)

```
┌─────────────────────────────────────────────────────────────┐
│  Add Movie Packs to [Circle Name]                      [X]  │
├─────────────────────────────────────────────────────────────┤
│  [Streaming ▼] [Genres ▼] [Curated ▼]                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 🎬 Netflix   │  │ 📺 Prime     │  │ 🏰 Disney+   │       │
│  │ Picks        │  │ Video Picks  │  │ Picks        │       │
│  │              │  │              │  │              │       │
│  │ 100 movies   │  │ 100 movies   │  │ 100 movies   │       │
│  │ 2 in circle  │  │ 0 in circle  │  │ 5 in circle  │       │
│  │              │  │              │  │              │       │
│  │ [Preview]    │  │ [Preview]    │  │ [Preview]    │       │
│  │ [+ Add]      │  │ [+ Add]      │  │ [+ Add]      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 🏆 Oscar     │  │ 🌍 Foreign   │  │ 💥 Action    │       │
│  │ Winners      │  │ Essentials   │  │ Hits         │       │
│  │ ~95 movies   │  │ ~50 movies   │  │ 100 movies   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 🕶️ 80s       │  │ 🎬 70s       │  │ 📼 90s       │       │
│  │ Bangers      │  │ Epics        │  │ Nostalgia    │       │
│  │ ~50 movies   │  │ ~40 movies   │  │ ~50 movies   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## TMDB Rate Limiting Strategy

1. **Cache aggressively**: Dynamic packs cached for 24 hours
2. **Track usage**: Log every TMDB call to `tmdb_api_usage` table
3. **Alert at threshold**: When daily calls > 800, log warning and set flag
4. **Graceful degradation**: If limit approached, serve cached data even if stale
5. **Future**: Email notification when threshold reached

### Rate Limit Middleware

```python
def check_tmdb_rate_limit():
    """Called before any TMDB API call"""
    usage = TMDBApiUsage.query.filter_by(date=date.today()).first()
    if usage and usage.call_count >= ALERT_THRESHOLD:
        logging.warning(f"TMDB API usage at {usage.call_count} calls today!")
        # Future: send email alert
    if usage and usage.call_count >= HARD_LIMIT:
        raise TMDBRateLimitError("Daily TMDB limit reached")
```

## Migration Plan

1. Create new database tables
2. Seed `movie_pack` table with pack definitions
3. Create static pack files in `backend/misc/packs/`
4. Implement PackService and TMDBService
5. Add API endpoints
6. Build frontend PackSelector component
7. Integrate into circle creation flow
8. Add to circle admin settings

## Open Questions

1. Should packs auto-refresh on a schedule, or only when viewed?
   - **Recommendation**: Refresh when viewed if cache >24h old

2. Should we show "last updated" on dynamic packs?
   - **Recommendation**: Yes, for transparency

3. How to handle movies that leave a streaming service?
   - **Recommendation**: Keep in circle, just update streaming availability

## Attribution Requirements

Per TMDB API terms:
- Must attribute JustWatch as source of streaming data
- Add footer text: "Streaming data provided by JustWatch via TMDB"
