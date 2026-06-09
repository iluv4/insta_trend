"""Turn live profile readings into ``MetricSnapshot`` rows.

Kept separate from the HTTP client so it can be unit-tested with a fake
``fetch_fn`` and reused by both the API ("collect now") and the scheduler.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .instagram import ProfileMetrics, fetch_profile_metrics
from .models import Account, MetricSnapshot


def collect_account(
    db: Session,
    account: Account,
    *,
    fetch_fn=fetch_profile_metrics,
    captured_at: datetime | None = None,
) -> MetricSnapshot:
    """Fetch one reading for ``account`` and persist it as a snapshot."""
    metrics: ProfileMetrics = fetch_fn(account.username)
    captured_at = captured_at or datetime.now(timezone.utc)

    # Keep the cached display name fresh when the source provides one.
    if metrics.full_name and not account.full_name:
        account.full_name = metrics.full_name

    snapshot = MetricSnapshot(
        account_id=account.id,
        captured_at=captured_at,
        followers=metrics.followers,
        following=metrics.following,
        posts_count=metrics.posts_count,
        avg_likes=metrics.avg_likes,
        avg_comments=metrics.avg_comments,
        engagement_rate=metrics.engagement_rate,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def collect_all(db: Session, *, fetch_fn=fetch_profile_metrics) -> dict[str, str]:
    """Collect a snapshot for every tracked account.

    Returns a per-account status map so a single failing profile doesn't abort
    the whole run (important for the scheduled job).
    """
    accounts = db.scalars(select(Account)).all()
    results: dict[str, str] = {}
    for account in accounts:
        try:
            collect_account(db, account, fetch_fn=fetch_fn)
            results[account.username] = "ok"
        except Exception as exc:  # noqa: BLE001 - report, don't crash the batch
            db.rollback()
            results[account.username] = f"error: {exc}"
    return results
