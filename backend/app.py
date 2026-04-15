"""FastAPI backend for inventory management environment."""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys

from fastapi import FastAPI
import uvicorn

from inventory import database
from inventory import inventory as inventory_service
from inventory import members as members_service

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
    logger.info("Database reset completed")
    return {"status": "reset", "ok": True}

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8005, reload=False)