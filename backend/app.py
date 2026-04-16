"""FastAPI backend for inventory management environment."""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI, HTTPException
import uvicorn

from inventory import database
from inventory import inventory as inventory_service
from inventory import members as members_service
import inventory.seed as seed

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
_ = (inventory_service, members_service)
DB_PATH = Path(__file__).resolve().parent.parent / "inventory" / "inventory.db"


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.setup(str(DB_PATH))
    seed.run(str(DB_PATH))
    yield


app = FastAPI(title="Inventory Management Backend", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset():
    if DB_PATH.exists():
        DB_PATH.unlink()
    database.setup(str(DB_PATH))
    seed.run(str(DB_PATH))
    logger.info("Database reset completed")
    return {"status": "reset", "ok": True}


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


@app.get("/items")
def get_items():
    with database.get_connection(str(DB_PATH)) as conn:
        rows = conn.execute("SELECT * FROM items ORDER BY id").fetchall()
    return [_row_to_dict(row) for row in rows]


@app.get("/items/{item_id}")
def get_item(item_id: int):
    with database.get_connection(str(DB_PATH)) as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    item = _row_to_dict(row)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


@app.put("/items/{item_id}/quantity")
def put_item_quantity(item_id: int, payload: dict[str, int]):
    if "quantity" not in payload:
        raise HTTPException(status_code=400, detail="quantity is required")
    item = inventory_service.update_quantity(
        item_id=item_id,
        quantity=int(payload["quantity"]),
        db_path=str(DB_PATH),
    )
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


@app.put("/items/{item_id}/available")
def put_item_available(item_id: int, payload: dict[str, int]):
    if "available" not in payload:
        raise HTTPException(status_code=400, detail="available is required")
    available = int(payload["available"])
    if available not in (0, 1):
        raise HTTPException(status_code=400, detail="available must be 0 or 1")
    with database.get_connection(str(DB_PATH)) as conn:
        conn.execute("UPDATE items SET available = ? WHERE id = ?", (available, item_id))
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        conn.commit()
    item = _row_to_dict(row)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


@app.get("/items/{item_id}/restock")
def get_item_restock(item_id: int):
    result = inventory_service.check_restock(item_id=item_id, db_path=str(DB_PATH))
    if result.get("item") is None:
        raise HTTPException(status_code=404, detail="item not found")
    return result


@app.get("/members")
def get_members():
    with database.get_connection(str(DB_PATH)) as conn:
        rows = conn.execute("SELECT * FROM members ORDER BY id").fetchall()
    return [_row_to_dict(row) for row in rows]


@app.get("/members/{member_id}")
def get_member(member_id: int):
    member = members_service.get_member(member_id=member_id, db_path=str(DB_PATH))
    if member is None:
        raise HTTPException(status_code=404, detail="member not found")
    return member


@app.put("/members/{member_id}/resolve")
def put_member_resolve(member_id: int, payload: dict[str, bool]):
    if "resolved" not in payload:
        raise HTTPException(status_code=400, detail="resolved is required")
    member = members_service.resolve_inquiry(
        member_id=member_id,
        resolved=bool(payload["resolved"]),
        db_path=str(DB_PATH),
    )
    if member is None:
        raise HTTPException(status_code=404, detail="member not found")
    return member


@app.get("/audit")
def get_audit():
    return inventory_service.run_audit_report(db_path=str(DB_PATH))


if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8005, reload=False)