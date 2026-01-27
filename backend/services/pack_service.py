"""Movie Pack Service - handles pack retrieval and addition to circles"""
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import func

from models import db, Movie, MoviePack, MoviePackCache, CircleMovie, UserSwipe
from services.seed_service import fetch_movie_from_omdb, find_movie_by_title
from services import tmdb_service

logger = logging.getLogger(__name__)

# Cache duration for dynamic packs (24 hours)
CACHE_DURATION_HOURS = 24


def get_all_packs():
    """Get all active movie packs with movie counts"""
    packs = MoviePack.query.filter_by(is_active=True).all()
    result = []

    for pack in packs:
        pack_data = pack.to_dict()
        pack_data['movie_count'] = len(pack.cached_movies)

        # Get preview posters (first 3 movies)
        preview_movies = MoviePackCache.query.filter_by(pack_id=pack.id)\
            .order_by(MoviePackCache.position)\
            .limit(3)\
            .all()
        pack_data['preview_posters'] = [
            pm.movie.poster for pm in preview_movies if pm.movie.poster
        ]

        result.append(pack_data)

    return result


def get_pack_by_id(pack_id):
    """Get a single pack by ID"""
    return MoviePack.query.filter_by(id=pack_id, is_active=True).first()


def get_pack_movies(pack_id, circle_id=None, user_id=None):
    """
    Get movies for a pack.
    If circle_id provided, includes already_in_circle flag.
    If user_id provided, includes user's swipe status.
    """
    pack = get_pack_by_id(pack_id)
    if not pack:
        return None, "Pack not found"

    # Check if cache needs refresh
    # For preview, we're lenient - use stale cache rather than hitting API
    cache_age = _get_cache_age(pack_id)

    if pack.pack_type == 'dynamic':
        # Only refresh if cache is completely empty
        # For preview, stale cache is acceptable - avoids API calls
        if cache_age is None:
            # No cache at all - do lightweight refresh (no details API calls)
            _refresh_dynamic_pack(pack, fetch_details=False)
        # If cache exists but is stale, still use it for preview
        # The actual add operation will refresh with full details if needed
    elif pack.pack_type == 'static':
        if cache_age is None:
            _refresh_static_pack(pack)

    # Get cached movies
    cached = MoviePackCache.query.filter_by(pack_id=pack_id)\
        .order_by(MoviePackCache.position)\
        .all()

    # If still no movies after refresh attempt, return an error
    if not cached:
        return None, f"Unable to load movies for {pack.name}. The streaming provider may be temporarily unavailable. Please try a different pack."

    # Get circle's existing movies if circle_id provided
    circle_movie_ids = set()
    if circle_id:
        circle_movies = CircleMovie.query.filter_by(circle_id=circle_id).all()
        circle_movie_ids = {cm.movie_id for cm in circle_movies}

    # Get user's swipes if user_id provided
    user_swipes = {}
    if user_id and circle_id:
        swipes = UserSwipe.query.filter_by(user_id=user_id, circle_id=circle_id).all()
        user_swipes = {s.movie_id: s.action for s in swipes}

    movies = []
    for cache_entry in cached:
        movie = cache_entry.movie
        movie_data = movie.to_dict()
        movie_data['already_in_circle'] = movie.id in circle_movie_ids
        movie_data['user_has_swiped'] = movie.id in user_swipes
        movie_data['user_swipe_action'] = user_swipes.get(movie.id)
        movies.append(movie_data)

    return {
        'pack': pack.to_dict(),
        'movies': movies,
        'total_count': len(movies),
        'in_circle_count': sum(1 for m in movies if m['already_in_circle'])
    }, None


def add_pack_to_circle(pack_id, circle_id, user_id):
    """
    Add all movies from a pack to a circle.
    - Skips movies already in circle
    - Preserves user's existing swipes
    - Sets source_pack attribution
    Returns dict with counts.
    """
    pack = get_pack_by_id(pack_id)
    if not pack:
        return None, "Pack not found"

    # Ensure pack cache is populated with full details
    # Always force a refresh with full details when actually adding
    if pack.pack_type == 'dynamic':
        cache_age = _get_cache_age(pack_id)
        if cache_age is None or cache_age > CACHE_DURATION_HOURS:
            _refresh_dynamic_pack(pack, fetch_details=True)
        else:
            # Cache exists and is fresh, but might have been created with
            # lightweight data from preview. Enrich any movies missing details.
            _enrich_pack_movies_if_needed(pack)

    # Get cached movies
    cached = MoviePackCache.query.filter_by(pack_id=pack_id).all()
    if not cached:
        return None, "Pack has no movies cached"

    # Get circle's existing movies
    existing = CircleMovie.query.filter_by(circle_id=circle_id).all()
    existing_movie_ids = {cm.movie_id for cm in existing}

    added_count = 0
    skipped_count = 0

    for cache_entry in cached:
        movie_id = cache_entry.movie_id

        if movie_id in existing_movie_ids:
            skipped_count += 1
            continue

        circle_movie = CircleMovie(
            circle_id=circle_id,
            movie_id=movie_id,
            added_by_id=user_id,
            is_system_seeded=True,
            source_pack_id=pack.id,
            source_pack_name=pack.name
        )
        db.session.add(circle_movie)
        added_count += 1

    db.session.commit()

    logger.info(f"Added pack '{pack.name}' to circle {circle_id}: {added_count} added, {skipped_count} skipped")

    return {
        'message': f"Added {added_count} movies from {pack.name}",
        'added_count': added_count,
        'skipped_count': skipped_count,
        'skipped_reason': 'already in circle' if skipped_count > 0 else None
    }, None


def refresh_pack(pack_id):
    """Manually refresh a pack's cache (with full details)"""
    pack = get_pack_by_id(pack_id)
    if not pack:
        return None, "Pack not found"

    if pack.pack_type == 'static':
        _refresh_static_pack(pack)
    else:
        _refresh_dynamic_pack(pack, fetch_details=True)

    return {'message': f"Refreshed pack '{pack.name}'"}, None


def _get_cache_age(pack_id):
    """Get age of pack cache in hours, or None if not cached"""
    latest = MoviePackCache.query.filter_by(pack_id=pack_id)\
        .order_by(MoviePackCache.cached_at.desc())\
        .first()

    if not latest:
        return None

    age = datetime.utcnow() - latest.cached_at
    return age.total_seconds() / 3600


def _refresh_static_pack(pack):
    """Refresh a static pack from its file"""
    config = pack.source_config or {}
    filename = config.get('file')
    if not filename:
        logger.error(f"Static pack {pack.id} has no file configured")
        return

    file_path = os.path.join(os.path.dirname(__file__), f'../misc/packs/{filename}')
    if not os.path.exists(file_path):
        logger.error(f"Pack file not found: {file_path}")
        return

    # Read titles from file
    with open(file_path, 'r') as f:
        content = f.read()
    titles = [t.strip() for t in content.split(';') if t.strip()]

    # Clear existing cache
    MoviePackCache.query.filter_by(pack_id=pack.id).delete()
    db.session.commit()  # Commit the delete before adding new entries

    # Add movies to cache
    # Track movie IDs we've already added to avoid duplicates
    added_movie_ids = set()
    position = 1

    for title in titles:
        # Try to find in DB first
        movie = find_movie_by_title(title)

        # If not found, fetch from OMDB
        if not movie:
            movie = fetch_movie_from_omdb(title, added_by_user_id=None)

        if movie and movie.id not in added_movie_ids:
            cache_entry = MoviePackCache(
                pack_id=pack.id,
                movie_id=movie.id,
                position=position,
                cached_at=datetime.utcnow()
            )
            db.session.add(cache_entry)
            added_movie_ids.add(movie.id)
            position += 1

    db.session.commit()
    logger.info(f"Refreshed static pack '{pack.name}': {position - 1} movies cached")


def _refresh_dynamic_pack(pack, fetch_details=True):
    """
    Refresh a dynamic pack from TMDB.

    Args:
        pack: The MoviePack to refresh
        fetch_details: If False, only use basic TMDB data (no credits/runtime API calls).
                      Use False for preview, True for actual add operations.
    """
    config = pack.source_config or {}
    provider_id = config.get('provider_id')
    genre_id = config.get('genre_id')

    try:
        if provider_id:
            tmdb_movies = tmdb_service.discover_by_provider(provider_id, limit=100)
        elif genre_id:
            tmdb_movies = tmdb_service.discover_by_genre(genre_id, limit=100)
        else:
            logger.error(f"Dynamic pack {pack.id} has no provider_id or genre_id")
            return
    except tmdb_service.TMDBRateLimitError as e:
        logger.error(f"Rate limit hit refreshing pack {pack.id}: {e}")
        return

    if not tmdb_movies:
        logger.warning(f"No movies returned from TMDB for pack {pack.id}")
        return

    # Clear existing cache
    MoviePackCache.query.filter_by(pack_id=pack.id).delete()
    db.session.commit()  # Commit the delete before adding new entries

    # Process movies and add to cache
    # Track movie IDs we've already added to avoid duplicates
    added_movie_ids = set()
    position = 1

    for tmdb_movie in tmdb_movies:
        movie = _get_or_create_movie_from_tmdb(tmdb_movie, fetch_details=fetch_details)
        if movie and movie.id not in added_movie_ids:
            cache_entry = MoviePackCache(
                pack_id=pack.id,
                movie_id=movie.id,
                position=position,
                cached_at=datetime.utcnow()
            )
            db.session.add(cache_entry)
            added_movie_ids.add(movie.id)
            position += 1

    db.session.commit()
    logger.info(f"Refreshed dynamic pack '{pack.name}': {position - 1} movies cached (fetch_details={fetch_details})")


def _get_or_create_movie_from_tmdb(tmdb_movie, fetch_details=True):
    """
    Get existing movie from DB or create from TMDB data.

    Args:
        tmdb_movie: TMDB movie data dict from discover endpoint
        fetch_details: If True, fetch full details (credits, runtime) for new movies.
                      If False, create with basic data only (for lightweight preview).
    """
    # First, try to find by title/year from basic TMDB data (no extra API call)
    title = tmdb_movie.get('title', '')
    release_date = tmdb_movie.get('release_date', '')
    year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

    if not title or not year:
        return None

    # Check if movie already exists in DB - if so, skip the details API call
    existing = Movie.query.filter_by(title=title, year=year).first()
    if existing:
        return existing

    # Movie doesn't exist - create it
    # Only fetch full details if requested (skips this for preview mode)
    movie_data = tmdb_service.tmdb_to_movie_data(tmdb_movie, include_details=fetch_details)

    if not movie_data['title'] or not movie_data['year']:
        return None

    # Double-check with the cleaned title from TMDB (might differ slightly)
    existing = Movie.query.filter_by(
        title=movie_data['title'],
        year=movie_data['year']
    ).first()

    if existing:
        return existing

    # Create new movie
    movie = Movie(
        title=movie_data['title'],
        year=movie_data['year'],
        poster=movie_data['poster'],
        description=movie_data['description'],
        genre=movie_data['genre'],
        rating=movie_data['rating'],
        length=movie_data['length'],
        starring=movie_data['starring'],
        added_by_id=None
    )
    db.session.add(movie)
    db.session.flush()

    return movie


def _enrich_pack_movies_if_needed(pack):
    """
    Check if cached movies are missing details (from lightweight preview)
    and fetch full details for any incomplete movies.
    """
    cached = MoviePackCache.query.filter_by(pack_id=pack.id).all()

    for cache_entry in cached:
        movie = cache_entry.movie
        # Check if movie is missing key details (sign of lightweight creation)
        # starring and length='N/A' are indicators of incomplete data
        if not movie.starring and movie.length == 'N/A':
            # Try to enrich from TMDB
            try:
                tmdb_movie = tmdb_service.search_movie(movie.title, movie.year)
                if tmdb_movie:
                    movie_data = tmdb_service.tmdb_to_movie_data(tmdb_movie, include_details=True)
                    # Update missing fields
                    if movie_data['starring']:
                        movie.starring = movie_data['starring']
                    if movie_data['length'] != 'N/A':
                        movie.length = movie_data['length']
            except tmdb_service.TMDBRateLimitError:
                logger.warning(f"Rate limit hit while enriching movie {movie.id}")
                break  # Stop enriching if we hit rate limit

    db.session.commit()


def seed_pack_definitions():
    """Seed the movie_packs table with all pack definitions"""
    packs = [
        # Static - Curated
        {
            'name': 'Top 100 Classics',
            'slug': 'classics',
            'description': 'The greatest films of all time, spanning decades of cinema',
            'pack_type': 'static',
            'category': 'curated',
            'source_config': {'file': 'classics.txt'},
            'icon': '🎬'
        },
        {
            'name': 'Oscar Best Picture Winners',
            'slug': 'oscar-best-picture',
            'description': 'Academy Award winners for Best Picture',
            'pack_type': 'static',
            'category': 'curated',
            'source_config': {'file': 'oscar_best_picture.txt'},
            'icon': '🏆'
        },
        {
            'name': 'AFI Top 100',
            'slug': 'afi-top-100',
            'description': 'American Film Institute\'s 100 greatest American films',
            'pack_type': 'static',
            'category': 'curated',
            'source_config': {'file': 'afi_top_100.txt'},
            'icon': '🇺🇸'
        },
        {
            'name': 'Foreign Film Essentials',
            'slug': 'foreign-essentials',
            'description': 'Must-see international cinema from around the world',
            'pack_type': 'static',
            'category': 'curated',
            'source_config': {'file': 'foreign_essentials.txt'},
            'icon': '🌍'
        },
        {
            'name': '90s Nostalgia',
            'slug': '90s-nostalgia',
            'description': 'The films that defined the 1990s',
            'pack_type': 'static',
            'category': 'curated',
            'source_config': {'file': '90s_nostalgia.txt'},
            'icon': '📼'
        },
        {
            'name': '80s Bangers',
            'slug': '80s-bangers',
            'description': 'Iconic films from the 1980s - from Breakfast Club to Die Hard',
            'pack_type': 'static',
            'category': 'curated',
            'source_config': {'file': '80s_bangers.txt'},
            'icon': '🕶️'
        },
        {
            'name': '70s Epics',
            'slug': '70s-epics',
            'description': 'The grand cinema of the 1970s - Godfather, Dog Day Afternoon, and more',
            'pack_type': 'static',
            'category': 'curated',
            'source_config': {'file': '70s_epics.txt'},
            'icon': '🎞️'
        },

        # Dynamic - Streaming
        {
            'name': 'Netflix Picks',
            'slug': 'netflix',
            'description': 'Popular movies currently streaming on Netflix',
            'pack_type': 'dynamic',
            'category': 'streaming',
            'source_config': {'provider_id': 8},
            'icon': '🔴'
        },
        {
            'name': 'Prime Video Picks',
            'slug': 'prime-video',
            'description': 'Popular movies currently streaming on Prime Video',
            'pack_type': 'dynamic',
            'category': 'streaming',
            'source_config': {'provider_id': 9},
            'icon': '📦'
        },
        {
            'name': 'Hulu Picks',
            'slug': 'hulu',
            'description': 'Popular movies currently streaming on Hulu',
            'pack_type': 'dynamic',
            'category': 'streaming',
            'source_config': {'provider_id': 15},
            'icon': '💚'
        },
        {
            'name': 'Disney+ Picks',
            'slug': 'disney-plus',
            'description': 'Popular movies currently streaming on Disney+',
            'pack_type': 'dynamic',
            'category': 'streaming',
            'source_config': {'provider_id': 337},
            'icon': '🏰'
        },
        {
            'name': 'Max Picks',
            'slug': 'max',
            'description': 'Popular movies currently streaming on Max',
            'pack_type': 'dynamic',
            'category': 'streaming',
            'source_config': {'provider_id': 1899},
            'icon': '💜'
        },
        {
            'name': 'Kanopy Picks',
            'slug': 'kanopy',
            'description': 'Thoughtful cinema available free through your library on Kanopy',
            'pack_type': 'dynamic',
            'category': 'streaming',
            'source_config': {'provider_id': 191},
            'icon': '📚'
        },

        # Dynamic - Genre
        {
            'name': 'Action Hits',
            'slug': 'action',
            'description': 'Top-rated action movies',
            'pack_type': 'dynamic',
            'category': 'genre',
            'source_config': {'genre_id': 28},
            'icon': '💥'
        },
        {
            'name': 'Comedy Favorites',
            'slug': 'comedy',
            'description': 'Highly-rated comedies to make you laugh',
            'pack_type': 'dynamic',
            'category': 'genre',
            'source_config': {'genre_id': 35},
            'icon': '😂'
        },
        {
            'name': 'Horror Essentials',
            'slug': 'horror',
            'description': 'Top-rated horror films for thrill seekers',
            'pack_type': 'dynamic',
            'category': 'genre',
            'source_config': {'genre_id': 27},
            'icon': '👻'
        },
        {
            'name': 'Sci-Fi Classics',
            'slug': 'sci-fi',
            'description': 'The best science fiction cinema has to offer',
            'pack_type': 'dynamic',
            'category': 'genre',
            'source_config': {'genre_id': 878},
            'icon': '🚀'
        },
        {
            'name': 'Documentary Gems',
            'slug': 'documentary',
            'description': 'Compelling documentaries that inform and inspire',
            'pack_type': 'dynamic',
            'category': 'genre',
            'source_config': {'genre_id': 99},
            'icon': '🎥'
        },
    ]

    for pack_data in packs:
        existing = MoviePack.query.filter_by(slug=pack_data['slug']).first()
        if not existing:
            pack = MoviePack(**pack_data)
            db.session.add(pack)
            logger.info(f"Added pack: {pack_data['name']}")

    db.session.commit()
    logger.info(f"Pack definitions seeded: {len(packs)} packs")
