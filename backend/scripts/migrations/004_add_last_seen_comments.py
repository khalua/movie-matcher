#!/usr/bin/env python3
"""
Migration 004: Add last_seen_comments_at to CircleMember

Adds column to track when a user last viewed comments in a circle,
used to show unread comment indicators in the UI.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import text, inspect


def check_column_exists(inspector, table_name, column_name):
    """Check if a column exists in a table"""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # Add last_seen_comments_at column to circle_members if it doesn't exist
        if not check_column_exists(inspector, 'circle_members', 'last_seen_comments_at'):
            print("Adding 'last_seen_comments_at' column to circle_members...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE circle_members ADD COLUMN last_seen_comments_at TIMESTAMP'))
                conn.commit()
            print("Column added.")
        else:
            print("Column 'last_seen_comments_at' already exists.")

        print("Migration 004 complete!")


if __name__ == '__main__':
    migrate()
