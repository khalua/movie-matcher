#!/usr/bin/env python3
"""Migration 009: Add circle_pack_installs table to track pack installations per circle"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db
from sqlalchemy import text, inspect


def check_table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def backfill_installs(conn):
    """Backfill install records from circle_movies and inferred pack membership."""
    # 1. Direct backfill: circle_movies with source_pack_id set
    conn.execute(text("""
        INSERT INTO circle_pack_installs (circle_id, pack_id, installed_by_id, installed_at, is_active)
        SELECT cm.circle_id, cm.source_pack_id,
               COALESCE(cm.added_by_id, c.created_by_id),
               MIN(cm.added_at), true
        FROM circle_movies cm
        JOIN circles c ON c.id = cm.circle_id
        WHERE cm.source_pack_id IS NOT NULL
          AND COALESCE(cm.added_by_id, c.created_by_id) IS NOT NULL
        GROUP BY cm.circle_id, cm.source_pack_id, COALESCE(cm.added_by_id, c.created_by_id)
        ON CONFLICT (circle_id, pack_id) DO NOTHING
    """))

    # 2. Inferred backfill: circles whose movies match a pack's cache (>50% overlap)
    #    but have no source_pack_id set (pre-pack-system seeded circles)
    rows = conn.execute(text("""
        SELECT cm.circle_id, mpc.pack_id,
               COUNT(*) as overlap,
               (SELECT COUNT(*) FROM movie_pack_cache mpc2 WHERE mpc2.pack_id = mpc.pack_id) as pack_size
        FROM circle_movies cm
        JOIN movie_pack_cache mpc ON mpc.movie_id = cm.movie_id
        WHERE cm.source_pack_id IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM circle_pack_installs cpi
              WHERE cpi.circle_id = cm.circle_id AND cpi.pack_id = mpc.pack_id
          )
        GROUP BY cm.circle_id, mpc.pack_id
        HAVING COUNT(*) > 0.5 * (SELECT COUNT(*) FROM movie_pack_cache mpc2 WHERE mpc2.pack_id = mpc.pack_id)
    """)).fetchall()

    for row in rows:
        circle_id, pack_id = row[0], row[1]
        # Use the circle creator as the installer
        creator = conn.execute(text(
            "SELECT created_by_id FROM circles WHERE id = :cid"
        ), {'cid': circle_id}).fetchone()

        if not creator or not creator[0]:
            # Fall back to the circle admin
            admin = conn.execute(text(
                "SELECT user_id FROM circle_members WHERE circle_id = :cid AND role = 'admin' LIMIT 1"
            ), {'cid': circle_id}).fetchone()
            installer_id = admin[0] if admin else None
        else:
            installer_id = creator[0]

        if installer_id:
            conn.execute(text("""
                INSERT INTO circle_pack_installs (circle_id, pack_id, installed_by_id, installed_at, is_active)
                SELECT :circle_id, :pack_id, :installer_id,
                       COALESCE(MIN(cm.added_at), NOW()), true
                FROM circle_movies cm
                WHERE cm.circle_id = :circle_id
                ON CONFLICT (circle_id, pack_id) DO NOTHING
            """), {
                'circle_id': circle_id,
                'pack_id': pack_id,
                'installer_id': installer_id
            })

    conn.commit()


def migrate():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        if not check_table_exists(inspector, 'circle_pack_installs'):
            db.create_all()
            print("Created circle_pack_installs table")

        with db.engine.connect() as conn:
            backfill_installs(conn)
            count = conn.execute(text("SELECT COUNT(*) FROM circle_pack_installs")).fetchone()[0]
            print(f"Backfilled pack installations: {count} total records")


if __name__ == '__main__':
    migrate()
