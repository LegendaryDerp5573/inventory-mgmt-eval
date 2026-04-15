"""Inventory Environment - A simple bug-fix workflow for inventory tasks.

This demonstrates:
- @env.tool() for agent-facing tools
- @env.scenario() for evaluation lifecycle (setup → prompt → evaluate)
- @env.initialize and @env.shutdown for lifecycle hooks
"""

import asyncio
import logging
import os
from pathlib import Path
import sys
from typing import Any

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
BACKEND_PORT = os.getenv("BACKEND_PORT", "8005")
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
PROJECT_DIR = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_DIR / "tests"

# HTTP client for backend communication
http_client = httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0)

# Create the environment
env = Environment(name="inventory")


@env.tool()
async def bash_tool(command: str) -> str:
    """Run a shell command in the project directory."""
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=str(PROJECT_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    out_text = stdout.decode(errors="replace").strip()
    err_text = stderr.decode(errors="replace").strip()

    return (
        f"exit_code={process.returncode}\n"
        f"stdout:\n{out_text}\n\n"
        f"stderr:\n{err_text}"
    )


@env.tool()
async def edit_tool(path: str, content: str | None = None) -> str:
    """View a file when content is omitted, or overwrite it when provided."""
    target = (PROJECT_DIR / path).resolve()
    if PROJECT_DIR not in target.parents and target != PROJECT_DIR:
        return "Error: path must be inside project directory."

    if content is None:
        if not target.exists():
            return f"Error: file not found: {target}"
        if target.is_dir():
            return f"Error: path is a directory: {target}"
        return target.read_text(encoding="utf-8")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote file: {target}"


@env.scenario("fix-bug")
async def fix_bug(task_description: str) -> Any:
    """Run a bug-fix task and score based on pytest pass/fail."""
    _ = yield task_description

    process = await asyncio.create_subprocess_shell(
        f'pytest "{TESTS_DIR}"',
        cwd=str(PROJECT_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    logger.info("pytest stdout:\n%s", stdout.decode(errors="replace"))
    logger.info("pytest stderr:\n%s", stderr.decode(errors="replace"))
    yield 1.0 if process.returncode == 0 else 0.0


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
