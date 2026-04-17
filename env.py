"""Inventory Environment - Workflow-based evaluation with direct tools."""

import logging
from pathlib import Path
import sqlite3
import sys
from typing import Any, Mapping, Sequence

from hud import Environment
from inventory.database import get_connection, initialize_database
from inventory.inventory import (
    add_item, update_quantity, check_restock,
    get_instock_rate, run_audit_report,
)
from inventory.members import (
    get_member, resolve_inquiry, get_resolution_rate,
)

# Configure logging to stderr (MCP uses stdout for communication)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s | %(name)s | %(message)s",
    force=True,
)
for logger_name in ["httpx", "httpcore"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Backend configuration
PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "inventory" / "inventory.db"

# Create the environment
env = Environment(name="inventory-mgmt-env")
_ = (add_item, get_instock_rate, get_resolution_rate)


@env.tool()
def get_items() -> list[dict[str, Any]]:
    initialize_database(str(DB_PATH))
    with get_connection(str(DB_PATH)) as conn:
        rows = conn.execute("SELECT * FROM items ORDER BY id").fetchall()
    return [dict(row) for row in rows]


@env.tool()
def get_item(item_id: int) -> dict[str, Any]:
    initialize_database(str(DB_PATH))
    with get_connection(str(DB_PATH)) as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row is not None else {}


@env.tool()
def update_item_quantity(item_id: int, quantity: int) -> dict[str, Any]:
    initialize_database(str(DB_PATH))
    item = update_quantity(item_id=item_id, quantity=quantity, db_path=str(DB_PATH))
    return item if item is not None else {}


@env.tool()
def update_item_availability(item_id: int, available: int) -> dict[str, Any]:
    initialize_database(str(DB_PATH))
    with get_connection(str(DB_PATH)) as conn:
        conn.execute("UPDATE items SET available = ? WHERE id = ?", (available, item_id))
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        conn.commit()
    return dict(row) if row is not None else {}


@env.tool()
def check_item_restock(item_id: int) -> dict[str, Any]:
    initialize_database(str(DB_PATH))
    return check_restock(item_id=item_id, db_path=str(DB_PATH))


@env.tool()
def get_members() -> list[dict[str, Any]]:
    initialize_database(str(DB_PATH))
    with get_connection(str(DB_PATH)) as conn:
        rows = conn.execute("SELECT * FROM members ORDER BY id").fetchall()
    return [dict(row) for row in rows]


@env.tool()
def get_member_by_id(member_id: int) -> dict[str, Any]:
    initialize_database(str(DB_PATH))
    member = get_member(member_id=member_id, db_path=str(DB_PATH))
    return member if member is not None else {}


@env.tool()
def resolve_member_inquiry(member_id: int, resolved: bool) -> dict[str, Any]:
    initialize_database(str(DB_PATH))
    member = resolve_inquiry(member_id=member_id, resolved=resolved, db_path=str(DB_PATH))
    return member if member is not None else {}


@env.tool()
def get_audit_report() -> dict[str, Any]:
    initialize_database(str(DB_PATH))
    return run_audit_report(db_path=str(DB_PATH))


@env.scenario("workflow")
async def workflow(instruction: str, checks: Sequence[Mapping[str, Any]]) -> Any:
    _ = yield instruction

    conn = sqlite3.connect(str(DB_PATH))
    try:
        for i, check in enumerate(checks):
            query = check["query"]
            expected = check["expected"]
            row = conn.execute(query).fetchone()
            actual = row[0] if row is not None and len(row) > 0 else None
            if actual != expected:
                logger.info(
                    "Check %s failed. query=%r expected=%r actual=%r",
                    i,
                    query,
                    expected,
                    actual,
                )
                yield 0.0
                return
    finally:
        conn.close()

    yield 1.0

if __name__ == "__main__":
    env.run(transport="stdio")
