
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "notes.db")


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():

    conn = get_db_connection()

    # USERS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # NOTES TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            category TEXT DEFAULT 'Personal',
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary TEXT DEFAULT '',
            priority TEXT DEFAULT 'Medium',
            reminder_at TEXT,
            is_pinned INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
            ON DELETE CASCADE
        )
    """)

    # AUTOMATIC DATABASE MIGRATION
    existing_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(notes)").fetchall()
    }

    new_columns = {
        "summary": "TEXT DEFAULT ''",
        "priority": "TEXT DEFAULT 'Medium'",
        "reminder_at": "TEXT",
        "is_pinned": "INTEGER DEFAULT 0"
    }

    for column, definition in new_columns.items():

        if column not in existing_columns:

            conn.execute(
                f"ALTER TABLE notes ADD COLUMN {column} {definition}"
            )

    conn.commit()
    conn.close()
