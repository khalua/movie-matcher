#!/usr/bin/env python3
"""Migration 013: Re-seed pack definitions to add new packs (A24, etc.)

The original migration 001 only seeds packs when the table is empty.
This migration ensures any new pack definitions added to seed_pack_definitions()
are inserted into production databases that already have existing packs.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db


def migrate():
    app = create_app()
    with app.app_context():
        from services.pack_service import seed_pack_definitions
        print("Re-seeding pack definitions (adds new packs, updates display_order)...")
        seed_pack_definitions()
        print("Pack definitions re-seeded.")


if __name__ == '__main__':
    migrate()
