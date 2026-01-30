#!/usr/bin/env python3
"""Migration 008: Add OMDB API usage tracking table"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import text, inspect


def check_table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def migrate():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # Create the omdb_api_usage table if it doesn't exist
        if not check_table_exists(inspector, 'omdb_api_usage'):
            db.create_all()
            print("Created omdb_api_usage table")
        else:
            print("omdb_api_usage table already exists")


if __name__ == '__main__':
    migrate()
