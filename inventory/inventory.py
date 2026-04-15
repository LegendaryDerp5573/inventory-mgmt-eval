from typing import Any, Dict, Optional

from .database import get_connection, initialize_database


def _to_dict(row: Optional[Any]) -> Optional[Dict[str, Any]]:
    return dict(row) if row is not None else None


def add_item(
    name: str,
    sku: str,
    quantity: int,
    threshold: int,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    initialize_database(db_path)
    available = 1 if quantity > 0 else 0
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO items (name, sku, quantity, threshold, available)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, sku, quantity, threshold, available),
        )
        item_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        conn.commit()
    return _to_dict(row) or {}


def remove_item(item_id: int, db_path: Optional[str] = None) -> bool:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        result = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
    return result.rowcount > 0


def update_quantity(item_id: int, quantity: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    initialize_database(db_path)
    available = 1 if quantity > 0 else 0
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE items SET quantity = ?, available = ? WHERE id = ?",
            (quantity, available, item_id),
        )
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        conn.commit()
    return _to_dict(row)


def check_restock(item_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    item = _to_dict(row)
    if item is None:
        return {"item": None, "restock_needed": False}
    restock_needed = item["quantity"] <= item["threshold"]
    return {"item": item, "restock_needed": restock_needed}


def get_instock_rate(db_path: Optional[str] = None) -> float:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
        if total == 0:
            return 0.0
        available = conn.execute("SELECT COUNT(*) AS c FROM items WHERE available = 1").fetchone()["c"]
    return available / total


def run_audit_report(db_path: Optional[str] = None) -> Dict[str, Any]:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        total_items = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
        low_stock = conn.execute(
            "SELECT COUNT(*) AS c FROM items WHERE quantity <= threshold"
        ).fetchone()["c"]
        out_of_stock = conn.execute("SELECT COUNT(*) AS c FROM items WHERE quantity = 0").fetchone()["c"]
        in_stock_rate = get_instock_rate(db_path)
    return {
        "total_items": total_items,
        "low_stock_items": low_stock,
        "out_of_stock_items": out_of_stock,
        "in_stock_rate": in_stock_rate,
    }
