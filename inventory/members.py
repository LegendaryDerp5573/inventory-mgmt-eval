from typing import Any, Dict, Optional

from .database import get_connection, initialize_database


def _to_dict(row: Optional[Any]) -> Optional[Dict[str, Any]]:
    return dict(row) if row is not None else None


def add_member(name: str, email: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO members (name, email, inquiries_resolved, total_inquiries)
            VALUES (?, ?, 0, 0)
            """,
            (name, email),
        )
        member_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        conn.commit()
    return _to_dict(row) or {}


def get_member(member_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    return _to_dict(row)


def update_member(
    member_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    initialize_database(db_path)
    current = get_member(member_id, db_path=db_path)
    if current is None:
        return None

    next_name = name if name is not None else current["name"]
    next_email = email if email is not None else current["email"]

    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE members SET name = ?, email = ? WHERE id = ?",
            (next_name, next_email, member_id),
        )
        row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        conn.commit()
    return _to_dict(row)


def resolve_inquiry(member_id: int, resolved: bool, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    initialize_database(db_path)
    member = get_member(member_id, db_path=db_path)
    if member is None:
        return None

    total_inquiries = member["total_inquiries"] + 1
    inquiries_resolved = member["inquiries_resolved"] + (1 if resolved else 0)

    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE members
            SET inquiries_resolved = ?, total_inquiries = ?
            WHERE id = ?
            """,
            (inquiries_resolved, total_inquiries, member_id),
        )
        row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        conn.commit()
    return _to_dict(row)


def get_resolution_rate(member_id: int, db_path: Optional[str] = None) -> Optional[float]:
    member = get_member(member_id, db_path=db_path)
    if member is None:
        return None
    total = member["total_inquiries"]
    if total == 0:
        return 0.0
    return member["inquiries_resolved"] / total
