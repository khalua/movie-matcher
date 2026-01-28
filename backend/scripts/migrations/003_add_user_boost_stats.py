#!/usr/bin/env python3
"""
Migration 003: Add User Boost Stats

New tables:
- user_boost_stats: Track daily boosted movie counts per user per circle
  Used to cap boosted movies at 10 per day for match prioritization feature
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import inspect


def check_table_exists(inspector, table_name):
    """Check if a table exists in the database"""
    return table_name in inspector.get_table_names()


def migrate():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # Create new tables (db.create_all handles this safely)
        print("Creating any missing tables...")
        db.create_all()
        print("Tables created/verified.")

        # Verify table was created
        inspector = inspect(db.engine)
        if check_table_exists(inspector, 'user_boost_stats'):
            print("Table 'user_boost_stats' exists.")
        else:
            print("Warning: 'user_boost_stats' table was not created.")

        print("Migration 003 complete!")


if __name__ == '__main__':
    migrate()
