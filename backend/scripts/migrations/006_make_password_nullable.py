#!/usr/bin/env python3
"""
Migration 006: Make password_hash nullable for OAuth users

Allows users to sign up via Google OAuth without a password.
OAuth-only users can optionally set a password later.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import text, inspect


def migrate():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # Check current column definition
        columns = inspector.get_columns('users')
        password_col = next((c for c in columns if c['name'] == 'password_hash'), None)

        if password_col:
            # PostgreSQL: ALTER COLUMN to drop NOT NULL constraint
            print("Making 'password_hash' column nullable for OAuth users...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL'))
                conn.commit()
            print("Column 'password_hash' is now nullable.")
        else:
            print("Column 'password_hash' not found - skipping.")

        print("Migration 006 complete!")


if __name__ == '__main__':
    migrate()
