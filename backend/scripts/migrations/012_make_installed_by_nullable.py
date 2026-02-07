#!/usr/bin/env python3
"""Migration 012: Make circle_pack_installs.installed_by_id nullable for user deletion"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Check current nullable status
            result = conn.execute(text("""
                SELECT is_nullable FROM information_schema.columns
                WHERE table_name = 'circle_pack_installs' AND column_name = 'installed_by_id'
            """))
            row = result.fetchone()
            if row and row[0] == 'NO':
                conn.execute(text('ALTER TABLE circle_pack_installs ALTER COLUMN installed_by_id DROP NOT NULL'))
                conn.commit()
                print("Made installed_by_id nullable")
            else:
                print("installed_by_id is already nullable or table doesn't exist")

if __name__ == '__main__':
    migrate()
