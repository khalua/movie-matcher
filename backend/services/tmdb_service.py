"""TMDB API Service for fetching movies by streaming provider and genre"""
import os
import logging
import requests
from datetime import datetime, date
from models import db, TMDBApiUsage

logger = logging.getLogger(__name__)

TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# TMDB Provider IDs
PROVIDERS = {
    'netflix': 8,
    'prime': 9,
    'hulu': 15,
    'disney': 337,
    'max': 1899,  # Formerly HBO Max (384)
    'kanopy': 191,
}

# TMDB Genre IDs
GENRES = {
    'action': 28,
    'comedy': 35,
    'horror': 27,
    'scifi': 878,
    'documentary': 99,
}

# TMDB Genre ID to name mapping (to avoid extra API calls)
GENRE_NAMES = {
    28: 'Action',
    12: 'Adventure',
    16: 'Animation',
    35: 'Comedy',
    80: 'Crime',
    99: 'Documentary',
    18: 'Drama',
    10751: 'Family',
    14: 'Fantasy',
    36: 'History',
    27: 'Horror',
    10402: 'Music',
    9648: 'Mystery',
    10749: 'Romance',
    878: 'Science Fiction',
    10770: 'TV Movie',
    53: 'Thriller',
    10752: 'War',
    37: 'Western',
}

# Rate limiting thresholds
DAILY_ALERT_THRESHOLD = 800
DAILY_HARD_LIMIT = 1000


class TMDBRateLimitError(Exception):
    """Raised when TMDB daily limit is approached"""
    pass


def log_tmdb_call(count=1):
    """Log TMDB API calls for rate tracking"""
    today = date.today()
    usage = TMDBApiUsage.query.filter_by(date=today).first()

    if not usage:
        usage = TMDBApiUsage(date=today, call_count=0)
        db.session.add(usage)

    usage.call_count += count
    usage.last_call_at = datetime.utcnow()
    db.session.commit()

    # Check if we've hit the alert threshold
    if usage.call_count >= DAILY_ALERT_THRESHOLD:
        logger.warning(f"TMDB API usage alert: {usage.call_count} calls today (threshold: {DAILY_ALERT_THRESHOLD})")

    return usage.call_count


def check_tmdb_rate_limit():
    """Check if we're approaching the rate limit. Returns (can_proceed, current_count)"""
    today = date.today()
    usage = TMDBApiUsage.query.filter_by(date=today).first()

    if not usage:
        return True, 0

    if usage.call_count >= DAILY_HARD_LIMIT:
        return False, usage.call_count

    return True, usage.call_count


def get_tmdb_usage():
    """Get TMDB API usage statistics"""
    today = date.today()
    usage = TMDBApiUsage.query.filter_by(date=today).first()

    # Get last 7 days
    from datetime import timedelta
    week_start = today - timedelta(days=6)
    week_usage = TMDBApiUsage.query.filter(
        TMDBApiUsage.date >= week_start
    ).order_by(TMDBApiUsage.date.desc()).all()

    return {
        'today': {
            'calls': usage.call_count if usage else 0,
            'limit': DAILY_HARD_LIMIT,
            'percentage': round((usage.call_count / DAILY_HARD_LIMIT * 100), 1) if usage else 0
        },
        'this_week': [
            {'date': u.date.isoformat(), 'calls': u.call_count}
            for u in week_usage
        ],
        'alert_threshold': DAILY_ALERT_THRESHOLD,
        'alert_triggered': usage.call_count >= DAILY_ALERT_THRESHOLD if usage else False,
        'limit_info': {
            'daily_limit': DAILY_HARD_LIMIT,
            'reset_time': 'No daily limit (50 req/sec)',
            'plan': 'Free tier'
        }
    }


def discover_by_provider(provider_id, limit=100):
    """
    Fetch top movies from a streaming provider.
    Returns list of TMDB movie data dicts.
    """
    if not TMDB_API_KEY:
        logger.error("TMDB_API_KEY not configured")
        return []

    can_proceed, current_count = check_tmdb_rate_limit()
    if not can_proceed:
        raise TMDBRateLimitError(f"Daily TMDB limit reached: {current_count} calls")

    movies = []
    page = 1
    max_pages = (limit // 20) + 1  # TMDB returns 20 per page

    while len(movies) < limit and page <= max_pages:
        try:
            response = requests.get(
                f"{TMDB_BASE_URL}/discover/movie",
                params={
                    'api_key': TMDB_API_KEY,
                    'with_watch_providers': provider_id,
                    'watch_region': 'US',
                    'sort_by': 'popularity.desc',
                    'page': page
                },
                timeout=10
            )
            log_tmdb_call()

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            movies.extend(results)
            page += 1

            # Check if we've exhausted results
            if page > data.get('total_pages', 1):
                break

        except Exception as e:
            logger.error(f"Error fetching from TMDB provider {provider_id}: {e}")
            break

    return movies[:limit]


def discover_by_genre(genre_id, limit=100):
    """
    Fetch top movies in a genre.
    Returns list of TMDB movie data dicts.
    """
    if not TMDB_API_KEY:
        logger.error("TMDB_API_KEY not configured")
        return []

    can_proceed, current_count = check_tmdb_rate_limit()
    if not can_proceed:
        raise TMDBRateLimitError(f"Daily TMDB limit reached: {current_count} calls")

    movies = []
    page = 1
    max_pages = (limit // 20) + 1

    while len(movies) < limit and page <= max_pages:
        try:
            response = requests.get(
                f"{TMDB_BASE_URL}/discover/movie",
                params={
                    'api_key': TMDB_API_KEY,
                    'with_genres': genre_id,
                    'sort_by': 'vote_average.desc',
                    'vote_count.gte': 1000,  # Only well-reviewed movies
                    'page': page
                },
                timeout=10
            )
            log_tmdb_call()

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            movies.extend(results)
            page += 1

            if page > data.get('total_pages', 1):
                break

        except Exception as e:
            logger.error(f"Error fetching from TMDB genre {genre_id}: {e}")
            break

    return movies[:limit]


def get_movie_details(tmdb_id):
    """Get full movie details from TMDB including credits"""
    if not TMDB_API_KEY:
        return None

    can_proceed, _ = check_tmdb_rate_limit()
    if not can_proceed:
        raise TMDBRateLimitError("Daily TMDB limit reached")

    try:
        response = requests.get(
            f"{TMDB_BASE_URL}/movie/{tmdb_id}",
            params={
                'api_key': TMDB_API_KEY,
                'append_to_response': 'credits'
            },
            timeout=10
        )
        log_tmdb_call()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching TMDB movie {tmdb_id}: {e}")
        return None


def search_movie(title, year=None):
    """Search for a specific movie on TMDB"""
    if not TMDB_API_KEY:
        return None

    can_proceed, _ = check_tmdb_rate_limit()
    if not can_proceed:
        raise TMDBRateLimitError("Daily TMDB limit reached")

    try:
        params = {
            'api_key': TMDB_API_KEY,
            'query': title
        }
        if year:
            params['year'] = year

        response = requests.get(
            f"{TMDB_BASE_URL}/search/movie",
            params=params,
            timeout=10
        )
        log_tmdb_call()

        data = response.json()
        results = data.get('results', [])
        return results[0] if results else None
    except Exception as e:
        logger.error(f"Error searching TMDB for {title}: {e}")
        return None


def tmdb_to_movie_data(tmdb_movie, include_details=False):
    """
    Convert TMDB movie data to our Movie model format.
    If include_details=True, fetches additional details (credits, runtime).
    """
    if include_details:
        details = get_movie_details(tmdb_movie['id'])
        if details:
            tmdb_movie = {**tmdb_movie, **details}

    # Extract year from release_date
    release_date = tmdb_movie.get('release_date', '')
    year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

    # Get poster URL
    poster_path = tmdb_movie.get('poster_path')
    poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''

    # Get genres (from details or genre_ids)
    genres = tmdb_movie.get('genres', [])
    if genres:
        genre_str = ', '.join(g['name'] for g in genres[:3])
    else:
        # Use genre_ids from discover response with our cached mapping
        genre_ids = tmdb_movie.get('genre_ids', [])
        genre_names = [GENRE_NAMES.get(gid, '') for gid in genre_ids[:3]]
        genre_str = ', '.join(g for g in genre_names if g)

    # Get cast from credits
    credits = tmdb_movie.get('credits', {})
    cast = credits.get('cast', [])
    starring = ', '.join(c['name'] for c in cast[:4]) if cast else ''

    # Runtime
    runtime = tmdb_movie.get('runtime')
    length = f"{runtime} min" if runtime else 'N/A'

    # Rating (TMDB uses vote_average out of 10)
    vote_average = tmdb_movie.get('vote_average')
    rating = str(round(vote_average, 1)) if vote_average else 'N/A'

    return {
        'title': tmdb_movie.get('title', ''),
        'year': year,
        'poster': poster,
        'description': tmdb_movie.get('overview', ''),
        'genre': genre_str,
        'rating': rating,
        'length': length,
        'starring': starring,
        'tmdb_id': tmdb_movie.get('id')
    }
