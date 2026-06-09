"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routers import accounts, analytics
from .scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(accounts.router)
app.include_router(analytics.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def dashboard():
        return FileResponse(str(STATIC_DIR / "index.html"))
