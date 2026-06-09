"""Background scheduler that periodically snapshots every tracked account."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .collector import collect_all
from .config import settings
from .database import SessionLocal

logger = logging.getLogger("insta_monitor.scheduler")

_scheduler: BackgroundScheduler | None = None


def _run_collection() -> None:
    db = SessionLocal()
    try:
        results = collect_all(db)
        logger.info("scheduled collection complete: %s", results)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.enable_scheduler:
        logger.info("scheduler disabled via settings")
        return None
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_collection,
        trigger="interval",
        minutes=settings.collect_interval_minutes,
        id="collect_all",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("scheduler started: every %s min", settings.collect_interval_minutes)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
