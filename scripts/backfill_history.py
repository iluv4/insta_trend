"""Backfill synthetic *past* snapshots for accounts you already track.

Instagram APIs only expose current values, so a freshly tracked account has a
single point and the time-series charts are empty. This script generates a
plausible history (gentle growth + wobble + noise) that ends exactly at each
account's earliest real snapshot, so the present-day values stay real while
the charts have something to show — handy for demos and presentations.

Usage (locally or in the Render Shell):
    python -m scripts.backfill_history             # 60 days for every account
    python -m scripts.backfill_history --days 90
    python -m scripts.backfill_history --username nike

Re-running is safe: accounts whose history already spans --days are skipped.
"""

from __future__ import annotations

import argparse
import math
import random
from datetime import timedelta

from app import database
from app.models import Account, MetricSnapshot


def _history_to(anchor: float, days: int, *, daily_growth_pct: float, noise_pct: float) -> list[float]:
    """A series of ``days`` values that grows into ``anchor`` (oldest first)."""
    out = []
    for back in range(days, 0, -1):  # back = days ago
        value = anchor / ((1 + daily_growth_pct / 100) ** back)
        value += math.sin(back / 6.0) * anchor * 0.005  # gentle weekly-ish wobble
        value *= 1 + random.uniform(-noise_pct, noise_pct) / 100
        out.append(max(0.0, value))
    return out


def backfill(days: int = 60, username: str | None = None) -> None:
    database.init_db()
    db = database.SessionLocal()
    try:
        query = db.query(Account)
        if username:
            query = query.filter_by(username=username.lstrip("@").strip().lower())
        accounts = query.all()
        if not accounts:
            print("no matching accounts — add them in the dashboard first")
            return

        for account in accounts:
            snaps = sorted(account.snapshots, key=lambda s: s.captured_at)
            if not snaps:
                print(f"@{account.username}: no snapshots yet — click 'Collect now' first; skipped")
                continue

            earliest = snaps[0]
            span_days = (snaps[-1].captured_at - earliest.captured_at).days
            missing = days - span_days
            if missing <= 0:
                print(f"@{account.username}: history already spans {span_days}d; skipped")
                continue

            anchor_followers = earliest.followers or 10_000
            # Keep engagement ratios consistent with the real reading when present.
            like_ratio = (earliest.avg_likes / anchor_followers) if earliest.avg_likes else 0.04
            comment_ratio = (
                (earliest.avg_comments / earliest.avg_likes)
                if earliest.avg_likes and earliest.avg_comments
                else 0.03
            )

            growth_pct = random.uniform(0.15, 0.45)  # plausible daily follower growth
            followers = _history_to(anchor_followers, missing, daily_growth_pct=growth_pct, noise_pct=0.4)
            following = earliest.following or anchor_followers * 0.001
            posts_anchor = earliest.posts_count or 100

            for i, f in enumerate(followers):
                back = missing - i  # days before the earliest real snapshot
                avg_likes = f * like_ratio * random.uniform(0.85, 1.15)
                avg_comments = avg_likes * comment_ratio * random.uniform(0.85, 1.15)
                db.add(
                    MetricSnapshot(
                        account_id=account.id,
                        captured_at=earliest.captured_at - timedelta(days=back),
                        followers=round(f),
                        following=round(following),
                        posts_count=max(0, round(posts_anchor - back * 0.3)),
                        avg_likes=round(avg_likes),
                        avg_comments=round(avg_comments),
                        engagement_rate=round((avg_likes + avg_comments) / f * 100, 3) if f else None,
                    )
                )
            print(f"@{account.username}: backfilled {missing} daily snapshots ending at the real value")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=60, help="total history span to reach (default 60)")
    parser.add_argument("--username", help="only backfill this account")
    args = parser.parse_args()
    random.seed(42)
    backfill(days=args.days, username=args.username)
    print("done — refresh the dashboard")
