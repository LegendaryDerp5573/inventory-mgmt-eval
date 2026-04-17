"""Inventory Environment - Workflow-based evaluation with FastAPI connection.

This demonstrates:
- env.connect_fastapi() for agent-facing tools from FastAPI routes
- @env.scenario() for evaluation lifecycle (prompt → agent runs → SQL checks)
"""

import logging
from pathlib import Path
import sqlite3
import sys
from typing import Any, Mapping, Sequence

from backend.app import app as fastapi_app
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
PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "inventory" / "inventory.db"

# Create the environment
env = Environment(name="inventory-mgmt-env")
env.connect_fastapi(fastapi_app)


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
