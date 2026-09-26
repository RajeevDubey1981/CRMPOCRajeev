"""Wipe local DB data, keeping only the admin user plus roles/permissions/item_masters.

Run from api/ with the venv active:
  python scripts\\reset_local_db_keep_admin.py
"""
from __future__ import annotations

from sqlalchemy import inspect, text

from app.config import settings
from app.database import engine

KEEP_TABLES = {"users", "roles", "permissions", "alembic_version"}


def main() -> None:
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    truncate_tables = [t for t in all_tables if t not in KEEP_TABLES]

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in truncate_tables:
            conn.execute(text(f"TRUNCATE TABLE `{table}`"))
            print(f"[reset] truncated {table}")
        deleted = conn.execute(
            text("DELETE FROM users WHERE email <> :email"),
            {"email": settings.seed_admin_email},
        )
        print(f"[reset] removed {deleted.rowcount} non-admin user(s)")
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    print(f"[reset] done. Admin retained: {settings.seed_admin_email}")


if __name__ == "__main__":
    main()
