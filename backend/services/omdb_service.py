"""OMDB API Service with usage tracking"""
import os
import logging
from datetime import datetime, date
from models import db, OMDBApiUsage

logger = logging.getLogger(__name__)

OMDB_API_KEY = os.environ.get('OMDB_API_KEY')

# OMDB rate limits (free tier)
DAILY_LIMIT = 1000


def log_omdb_call(count=1):
    """Log OMDB API calls for rate tracking"""
    today = date.today()
    usage = OMDBApiUsage.query.filter_by(date=today).first()

    if not usage:
        usage = OMDBApiUsage(date=today, call_count=0)
        db.session.add(usage)

    usage.call_count += count
    usage.last_call_at = datetime.utcnow()
    db.session.commit()

    # Log warning if approaching limit
    if usage.call_count >= 800:
        logger.warning(f"OMDB API usage alert: {usage.call_count} calls today (limit: {DAILY_LIMIT})")

    return usage.call_count


def get_omdb_usage():
    """Get OMDB API usage statistics"""
    from datetime import timedelta

    today = date.today()
    usage = OMDBApiUsage.query.filter_by(date=today).first()

    # Get last 7 days
    week_start = today - timedelta(days=6)
    week_usage = OMDBApiUsage.query.filter(
        OMDBApiUsage.date >= week_start
    ).order_by(OMDBApiUsage.date.desc()).all()

    return {
        'today': {
            'calls': usage.call_count if usage else 0,
            'limit': DAILY_LIMIT,
            'percentage': round((usage.call_count / DAILY_LIMIT * 100), 1) if usage else 0
        },
        'this_week': [
            {'date': u.date.isoformat(), 'calls': u.call_count}
            for u in week_usage
        ],
        'limit_info': {
            'daily_limit': DAILY_LIMIT,
            'reset_time': 'Midnight UTC (resets daily)',
            'plan': 'Free tier'
        }
    }
