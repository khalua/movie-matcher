#!/usr/bin/env python3
"""Initialize database tables."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db

app = create_app()
with app.app_context():
    db.create_all()
    print('Tables created successfully!')
