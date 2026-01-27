#!/usr/bin/env python3
"""
Migration runner for Dokku release phase.

This script runs all migrations in order. Each migration is idempotent
(safe to run multiple times) and checks whether changes are needed before applying.

Usage:
    python backend/scripts/run_migrations.py

Add new migrations by creating numbered files in backend/scripts/migrations/
Example: 002_add_new_feature.py

Each migration must have a migrate() function.
"""
import sys
import os
import importlib.util

# Ensure backend is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'migrations')


def get_migration_files():
    """Get all migration files sorted by number"""
    if not os.path.exists(MIGRATIONS_DIR):
        return []

    files = []
    for f in os.listdir(MIGRATIONS_DIR):
        if f.endswith('.py') and not f.startswith('__'):
            files.append(f)

    # Sort by the numeric prefix (e.g., 001, 002, etc.)
    files.sort(key=lambda x: x.split('_')[0])
    return files


def run_migration(filename):
    """Run a single migration file"""
    filepath = os.path.join(MIGRATIONS_DIR, filename)

    # Load the module
    spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Run the migrate function
    if hasattr(module, 'migrate'):
        module.migrate()
    else:
        print(f"Warning: {filename} has no migrate() function, skipping.")


def main():
    print("=" * 60)
    print("Running database migrations...")
    print("=" * 60)

    migrations = get_migration_files()

    if not migrations:
        print("No migrations found.")
        return

    print(f"Found {len(migrations)} migration(s)")

    for filename in migrations:
        print()
        print("-" * 60)
        print(f"Running: {filename}")
        print("-" * 60)
        try:
            run_migration(filename)
        except Exception as e:
            print(f"ERROR in {filename}: {e}")
            sys.exit(1)

    print()
    print("=" * 60)
    print("All migrations completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
