#!/usr/bin/env python3
"""
Migration 005: Add password reset columns to User

Adds password_reset_token and password_reset_expires columns
to support password reset functionality via email.
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

        # Add password_reset_token column
        if not check_column_exists(inspector, 'users', 'password_reset_token'):
            print("Adding 'password_reset_token' column to users...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(100) UNIQUE'))
                conn.commit()
            print("Column added.")
        else:
            print("Column 'password_reset_token' already exists.")

        # Add password_reset_expires column
        if not check_column_exists(inspector, 'users', 'password_reset_expires'):
            print("Adding 'password_reset_expires' column to users...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN password_reset_expires TIMESTAMP'))
                conn.commit()
            print("Column added.")
        else:
            print("Column 'password_reset_expires' already exists.")

        # Add index on password_reset_token for faster lookups
        print("Creating index on password_reset_token if not exists...")
        with db.engine.connect() as conn:
            try:
                conn.execute(text('CREATE INDEX IF NOT EXISTS idx_users_password_reset_token ON users (password_reset_token)'))
                conn.commit()
            except Exception as e:
                # Index might already exist in some form
                print(f"Index creation skipped: {e}")

        print("Migration 005 complete!")


if __name__ == '__main__':
    migrate()
