"""
Migration script to add 'title' column to sessions table.
Run this once to update existing database.
"""

import sqlite3
import os

def migrate_database():
    db_path = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db").replace("sqlite:///", "")
    
    print(f"Connecting to database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'title' in columns:
            print(" 'title' column already exists in sessions table")
        else:
            print("Adding 'title' column to sessions table...")
            cursor.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
            conn.commit()
            print(" Successfully added 'title' column")
        
        print("\nMigration complete!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
