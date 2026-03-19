#!/usr/bin/env python3
"""
Safe schema migration script.

Compares the current SQLAlchemy ORM models against the live SQLite database
and adds any columns that are missing.  Existing data is never touched.

Usage:
    python migrate_db.py [--db PATH]   # defaults to chatbot.db resolved from DATABASE_URL

A timestamped backup is always created before any changes are made.
"""
import argparse
import os
import shutil
import sqlite3
from datetime import datetime

# ---------------------------------------------------------------------------
# SQLAlchemy type → SQLite DDL fragment
# ---------------------------------------------------------------------------
_TYPE_MAP = {
    "VARCHAR":  "TEXT",
    "STRING":   "TEXT",
    "TEXT":     "TEXT",
    "INTEGER":  "INTEGER",
    "FLOAT":    "REAL",
    "DATETIME": "TEXT",
    "BOOLEAN":  "INTEGER",
    "BLOB":     "BLOB",
}

def _sqlalchemy_type_to_sqlite(sa_type: str) -> str:
    """Convert a SQLAlchemy type string to a SQLite column type."""
    upper = sa_type.upper().split("(")[0].strip()
    return _TYPE_MAP.get(upper, "TEXT")


# ---------------------------------------------------------------------------
# Core migration logic
# ---------------------------------------------------------------------------
def get_orm_schema() -> dict[str, dict[str, str]]:
    """
    Return a mapping of  { table_name: { col_name: sqlite_type } }
    derived from the SQLAlchemy model *metadata* (not the live DB).
    """
    from database import Base

    schema: dict[str, dict[str, str]] = {}
    for table_name, table_obj in Base.metadata.tables.items():
        schema[table_name] = {}
        for col in table_obj.columns:
            sqlite_type = _sqlalchemy_type_to_sqlite(str(col.type))
            schema[table_name][col.name] = sqlite_type
    return schema


def get_db_schema(conn: sqlite3.Connection) -> dict[str, dict[str, str]]:
    """
    Return a mapping of  { table_name: { col_name: declared_type } }
    read directly from SQLite PRAGMA calls.
    """
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]

    schema: dict[str, dict[str, str]] = {}
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        schema[table] = {row[1]: row[2] for row in cur.fetchall()}
    return schema


def migrate(db_path: str) -> None:
    """Apply any missing columns to *db_path*, creating a backup first."""

    if not os.path.exists(db_path):
        print(f"[migrate] No database found at {db_path} — nothing to migrate.")
        return

    # -- Backup ----------------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"[migrate] Backup created: {backup_path}")

    # -- Ensure all ORM tables exist first (create_all is a no-op for existing tables)
    from database import init_db
    init_db()

    # -- Compare ORM vs live DB ------------------------------------------
    conn = sqlite3.connect(db_path)
    try:
        orm_schema = get_orm_schema()
        db_schema  = get_db_schema(conn)

        changes_made = False

        for table, orm_cols in orm_schema.items():
            if table not in db_schema:
                # Table is entirely new — create_all above already handled it.
                print(f"[migrate] Table '{table}' was newly created by init_db().")
                continue

            existing_cols = db_schema[table]

            for col_name, col_type in orm_cols.items():
                if col_name not in existing_cols:
                    ddl = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"
                    print(f"[migrate] Adding column: {table}.{col_name} ({col_type})")
                    conn.execute(ddl)
                    changes_made = True

        if changes_made:
            conn.commit()
            print("[migrate] Migration committed successfully.")
        else:
            print("[migrate] Schema is already up to date — no changes needed.")

    except Exception as exc:
        conn.rollback()
        print(f"[migrate] ERROR: {exc}")
        print(f"[migrate] Rolling back. Your original data is safe in: {backup_path}")
        raise
    finally:
        conn.close()

    # -- Print final schema ----------------------------------------------
    from sqlalchemy import inspect as sa_inspect
    from database import engine

    inspector = sa_inspect(engine)
    print("\n[migrate] Current schema:")
    for table in inspector.get_table_names():
        cols = inspector.get_columns(table)
        col_names = ", ".join(c["name"] for c in cols)
        print(f"  {table}: {col_names}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite DB to match current ORM models.")
    parser.add_argument("--db", default=None, help="Path to chatbot.db (default: resolved from DATABASE_URL)")
    args = parser.parse_args()

    if args.db:
        db_path = os.path.abspath(args.db)
    else:
        from database import DATABASE_URL
        db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)

    print(f"[migrate] Target database: {db_path}")
    migrate(db_path)
