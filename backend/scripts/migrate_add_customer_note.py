"""
Migration script: Add 'note' column to customer table

This script adds the 'note' column to the existing customer table.
Safe to run multiple times - checks if column already exists.

Usage:
    python scripts/migrate_add_customer_note.py
"""

import sqlite3
from pathlib import Path


def migrate_add_customer_note():
    """Add note column to customer table if it doesn't exist."""
    db_path = Path(__file__).resolve().parent.parent / "invoices.db"

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    print(f"🔍 Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(customer)")
        columns = [column[1] for column in cursor.fetchall()]

        if "note" in columns:
            print(
                "✅ Column 'note' already exists in customer table. No migration needed."
            )
            return

        # Add the column
        print("📝 Adding 'note' column to customer table...")
        cursor.execute("ALTER TABLE customer ADD COLUMN note TEXT")
        conn.commit()

        print("✅ Migration successful! Column 'note' added to customer table.")

        # Verify
        cursor.execute("PRAGMA table_info(customer)")
        columns = cursor.fetchall()
        print("\n📋 Current customer table schema:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_add_customer_note()
