"""Seed items and members tables with fixed demo data."""

from typing import Optional

from .database import get_connection, initialize_database

ITEMS_ROWS = [
    ("Boxing Gloves", "SKU001", 15, 10, 1),
    ("Hand Wraps", "SKU002", 3, 10, 0),
    ("Mouth Guard", "SKU003", 20, 5, 1),
    ("Shin Guards", "SKU004", 8, 10, 1),
    ("Jump Rope", "SKU005", 2, 5, 0),
    ("Headgear", "SKU006", 12, 8, 1),
    ("Training Pads", "SKU007", 0, 5, 0),
    ("Grappling Dummy", "SKU008", 4, 3, 1),
]

MEMBERS_ROWS = [
    ("Alice Johnson", "alice@gym.com", 28, 30),
    ("Bob Smith", "bob@gym.com", 15, 20),
    ("Carlos Rivera", "carlos@gym.com", 9, 10),
    ("Dana Lee", "dana@gym.com", 0, 5),
    ("Evan Park", "evan@gym.com", 42, 45),
]


def run(db_path: Optional[str] = None) -> None:
    """Clear items and members, then insert fixed seed data."""
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM items")
        conn.execute("DELETE FROM members")
        conn.executemany(
            """
            INSERT INTO items (name, sku, quantity, threshold, available)
            VALUES (?, ?, ?, ?, ?)
            """,
            ITEMS_ROWS,
        )
        conn.executemany(
            """
            INSERT INTO members (name, email, inquiries_resolved, total_inquiries)
            VALUES (?, ?, ?, ?)
            """,
            MEMBERS_ROWS,
        )
        conn.commit()

    n_items = len(ITEMS_ROWS)
    n_members = len(MEMBERS_ROWS)
    print(f"Seeded {n_items} items and {n_members} members.")
