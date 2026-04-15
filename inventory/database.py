import sqlite3
from pathlib import Path
from typing import Optional


DEFAULT_DB_PATH = Path(__file__).with_name("inventory.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a SQLite connection."""
    path = db_path or str(DEFAULT_DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(db_path: Optional[str] = None) -> None:
    """Create required tables if they do not already exist."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT NOT NULL UNIQUE,
                quantity INTEGER NOT NULL DEFAULT 0,
                threshold INTEGER NOT NULL DEFAULT 0,
                available INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                inquiries_resolved INTEGER NOT NULL DEFAULT 0,
                total_inquiries INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
