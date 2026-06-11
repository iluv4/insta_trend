"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routers import accounts, analytics
from .scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


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


# Log the resolved static path at import time so deploys (Render/Docker/…) show
# in their logs whether the dashboard assets were found in the container.
logger.info("STATIC_DIR=%s exists=%s index=%s", STATIC_DIR, STATIC_DIR.exists(), INDEX_HTML.exists())

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Register "/" unconditionally so the homepage never silently 404s when the
# static directory is missing — instead it explains where the dashboard is and
# points at the API. When index.html is present it serves the dashboard.
@app.get("/", include_in_schema=False)
def dashboard():
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return JSONResponse(
        status_code=503,
        content={
            "status": "dashboard_unavailable",
            "detail": f"static dashboard not found at {INDEX_HTML}",
            "api_docs": "/docs",
            "health": "/api/health",
        },
    )
