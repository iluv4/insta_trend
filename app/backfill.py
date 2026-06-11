"""Generate a synthetic *past* for a tracked account (demo helper).

Instagram APIs only expose current values, so a freshly tracked account has a
single snapshot and the time-series charts are empty. ``backfill_account``
fabricates a plausible history (gentle growth + weekly wobble + noise) that
ends exactly at the account's earliest real snapshot — present-day values stay
real while the charts have something to show.

Used by the ``POST /api/accounts/{id}/backfill`` endpoint and the
``scripts.backfill_history`` CLI.
"""

from __future__ import annotations

import math
import random
from datetime import timedelta

from sqlalchemy.orm import Session

from .models import Account, MetricSnapshot


def _history_to(anchor: float, days: int) -> list[float]:
    """A series of ``days`` values ending exactly at ``anchor`` (oldest first).

    Built as a random walk in log-space rather than smooth compounding, so it
    looks like a real follower curve: segments of slow growth, plateaus and
    slight declines, day-to-day jitter, and the occasional viral bump that
    partially gives back. Overall growth lands between ~2–12% over the span.
    """
    # Segmented drift: most stretches grow slowly, some are flat, a few dip.
    increments: list[float] = []
    while len(increments) < days:
        segment = random.randint(5, 14)
        drift = random.choices(
            [random.uniform(0.0005, 0.002),    # slow growth
             random.uniform(-0.0002, 0.0004),  # plateau
             random.uniform(-0.001, -0.0002)], # mild decline
            weights=[0.55, 0.35, 0.10],
        )[0]
        for _ in range(min(segment, days - len(increments))):
            increments.append(drift + random.gauss(0, 0.0015))

    # 0–2 viral bumps that partially give back over the next few days.
    for _ in range(random.randint(0, 2)):
        at = random.randint(0, days - 1)
        bump = random.uniform(0.005, 0.02)
        increments[at] += bump
        for j in range(at + 1, min(at + 4, days)):
            increments[j] -= bump * 0.08

    # Pin the overall growth to a realistic 2–12% so the walk never ends up
    # net-negative (which would put the oldest point above today's value).
    target_total = random.uniform(math.log(1.02), math.log(1.12))
    adjust = (target_total - sum(increments)) / days
    increments = [inc + adjust for inc in increments]

    levels: list[float] = []
    level = 0.0
    for inc in increments:
        level += inc
        levels.append(level)
    last = levels[-1]
    return [max(0.0, anchor * math.exp(lv - last)) for lv in levels]


def backfill_account(db: Session, account: Account, days: int = 60) -> int:
    """Add synthetic snapshots so ``account``'s history spans ``days`` days.

    Returns the number of rows added: 0 when the account has no real snapshot
    yet (collect one first) or its history already spans the requested range.
    The caller commits.
    """
    snaps = sorted(account.snapshots, key=lambda s: s.captured_at)
    if not snaps:
        return 0

    earliest = snaps[0]
    span_days = (snaps[-1].captured_at - earliest.captured_at).days
    missing = days - span_days
    if missing <= 0:
        return 0

    anchor_followers = earliest.followers or 10_000
    # Keep engagement ratios consistent with the real reading when present.
    like_ratio = (earliest.avg_likes / anchor_followers) if earliest.avg_likes else 0.04
    comment_ratio = (
        (earliest.avg_comments / earliest.avg_likes)
        if earliest.avg_likes and earliest.avg_comments
        else 0.03
    )

    followers = _history_to(anchor_followers, missing)
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
    return missing
