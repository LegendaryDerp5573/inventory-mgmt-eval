"""Inventory Environment - Workflow-based evaluation over HTTP + SQLite.

This demonstrates:
- @env.tool() for agent-facing tools (HTTP calls to backend)
- @env.scenario() for evaluation lifecycle (prompt → agent runs → SQL checks)
- @env.initialize and @env.shutdown for lifecycle hooks
"""

import logging
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Mapping, Sequence

import httpx

from hud import Environment

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
BACKEND_URL = "http://localhost:8005"
PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "inventory" / "inventory.db"

# HTTP client for backend communication
http_client = httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0)

# Create the environment
env = Environment(name="inventory")


@env.tool()
async def get_items() -> Any:
    resp = await http_client.get("/items")
    resp.raise_for_status()
    return resp.json()


@env.tool()
async def get_item(item_id: int) -> Any:
    resp = await http_client.get(f"/items/{item_id}")
    resp.raise_for_status()
    return resp.json()


@env.tool()
async def update_quantity(item_id: int, quantity: int) -> Any:
    resp = await http_client.put(f"/items/{item_id}/quantity", json={"quantity": quantity})
    resp.raise_for_status()
    return resp.json()


@env.tool()
async def update_availability(item_id: int, available: int) -> Any:
    resp = await http_client.put(f"/items/{item_id}/available", json={"available": available})
    resp.raise_for_status()
    return resp.json()


@env.tool()
async def check_restock(item_id: int) -> Any:
    resp = await http_client.get(f"/items/{item_id}/restock")
    resp.raise_for_status()
    return resp.json()


@env.tool()
async def get_members() -> Any:
    resp = await http_client.get("/members")
    resp.raise_for_status()
    return resp.json()


@env.tool()
async def get_member(member_id: int) -> Any:
    resp = await http_client.get(f"/members/{member_id}")
    resp.raise_for_status()
    return resp.json()


@env.tool()
async def resolve_inquiry(member_id: int, resolved: bool) -> Any:
    resp = await http_client.put(f"/members/{member_id}/resolve", json={"resolved": resolved})
    resp.raise_for_status()
    return resp.json()


@env.tool()
async def get_audit() -> Any:
    resp = await http_client.get("/audit")
    resp.raise_for_status()
    return resp.json()


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


@env.initialize
async def init() -> None:
    """Check backend health on startup."""
    (await http_client.get("/health")).raise_for_status()


@env.shutdown
async def cleanup() -> None:
    """Close HTTP client on shutdown."""
    await http_client.aclose()


if __name__ == "__main__":
    env.run(transport="stdio")
