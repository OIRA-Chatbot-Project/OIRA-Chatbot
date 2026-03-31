#!/usr/bin/env python3
"""
Script to recreate the SQLite database with current models.
This will backup the old database (if exists) and create a new one.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
from datetime import datetime
from core.database import init_db, DATABASE_URL

def recreate_database():
    """Recreate the database from scratch"""

    # Extract database path from DATABASE_URL
    db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")

    # Make it absolute if relative
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)

    print(f"Database path: {db_path}")

    # Check if database exists
    if os.path.exists(db_path):
        # Create backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"

        print(f"Backing up existing database to: {backup_path}")
        shutil.copy2(db_path, backup_path)

        # Delete old database
        print(f"Deleting old database: {db_path}")
        os.remove(db_path)
        print("Old database deleted successfully")
    else:
        print("No existing database found")

    # Create new database with current schema
    print("Creating new database with current models...")
    init_db()
    print(f"✓ Database created successfully at: {db_path}")

    # Verify tables were created
    from sqlalchemy import inspect
    from core.database import engine

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\nCreated tables:")
    for table in tables:
        columns = inspector.get_columns(table)
        print(f"  - {table} ({len(columns)} columns)")
        for col in columns:
            print(f"      • {col['name']}: {col['type']}")

    print("\n✓ Database recreation completed successfully!")

if __name__ == "__main__":
    recreate_database()
