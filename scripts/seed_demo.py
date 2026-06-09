"""Populate the database with synthetic time-series so you can explore the
dashboard and analytics without a RapidAPI key.

Usage:
    python -m scripts.seed_demo
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal, init_db
from app.models import Account, MetricSnapshot


def _series(days: int, base: float, daily_growth: float, noise: float, spike_day: int | None):
    """A rising line + sinusoidal wobble + noise, with an optional viral spike."""
    out = []
    for i in range(days):
        value = base + daily_growth * i
        value += math.sin(i / 6.0) * base * 0.01  # gentle weekly-ish wobble
        value += random.uniform(-noise, noise)
        if spike_day is not None and i == spike_day:
            value *= 1.8  # viral spike
        out.append(max(0.0, value))
    return out


def seed():
    init_db()
    db = SessionLocal()
    try:
        demo = {
            "nike": dict(base=300_000_000, growth=120_000, noise=80_000, spike=None, label="reference"),
            "risingbrand": dict(base=12_000, growth=900, noise=400, spike=40, label="competitor"),
            "plateaubrand": dict(base=85_000, growth=15, noise=600, spike=None, label="competitor"),
        }
        start = datetime.now(timezone.utc) - timedelta(days=60)
        for username, cfg in demo.items():
            account = db.query(Account).filter_by(username=username).one_or_none()
            if account is None:
                account = Account(username=username, full_name=username.title(), label=cfg["label"])
                db.add(account)
                db.flush()
            else:
                account.snapshots.clear()
                db.flush()

            followers = _series(60, cfg["base"], cfg["growth"], cfg["noise"], cfg["spike"])
            for i, f in enumerate(followers):
                avg_likes = f * random.uniform(0.03, 0.06)
                avg_comments = avg_likes * random.uniform(0.02, 0.05)
                db.add(
                    MetricSnapshot(
                        account_id=account.id,
                        captured_at=start + timedelta(days=i),
                        followers=round(f),
                        following=round(cfg["base"] * 0.001),
                        posts_count=100 + i,
                        avg_likes=round(avg_likes),
                        avg_comments=round(avg_comments),
                        engagement_rate=round((avg_likes + avg_comments) / f * 100, 3),
                    )
                )
            print(f"seeded @{username}: 60 daily snapshots")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    random.seed(42)
    seed()
    print("done. run: uvicorn app.main:app --reload  →  http://localhost:8000")
