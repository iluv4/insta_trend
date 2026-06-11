"""Backfill script behaviour against a temporary SQLite database."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pytest

import app.database as database
from app.models import Account, MetricSnapshot
from scripts.backfill_history import backfill


@pytest.fixture()
def db(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{tmp_path / 'backfill.db'}")
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", Session)
    database.init_db()
    random.seed(42)
    return Session


def _add_account_with_snapshot(Session, followers=50_000):
    with Session() as s:
        account = Account(username="brand", full_name="Brand")
        s.add(account)
        s.flush()
        s.add(
            MetricSnapshot(
                account_id=account.id,
                captured_at=datetime.now(timezone.utc),
                followers=followers,
                following=120,
                posts_count=300,
                avg_likes=2000,
                avg_comments=80,
                engagement_rate=4.16,
            )
        )
        s.commit()
        return account.id


def test_backfill_generates_history_ending_at_real_value(db):
    account_id = _add_account_with_snapshot(db, followers=50_000)
    backfill(days=30)

    with db() as s:
        snaps = (
            s.query(MetricSnapshot)
            .filter_by(account_id=account_id)
            .order_by(MetricSnapshot.captured_at)
            .all()
        )
    assert len(snaps) == 31  # 30 synthetic + 1 real
    # History rises into the real anchor and the real snapshot stays last/untouched.
    assert snaps[0].followers < 50_000
    assert snaps[-1].followers == 50_000
    # Daily spacing, oldest ~30 days back.
    assert (snaps[-1].captured_at - snaps[0].captured_at).days == 30


def test_backfill_is_idempotent_once_span_reached(db):
    _add_account_with_snapshot(db)
    backfill(days=30)
    backfill(days=30)  # second run must not add more rows

    with db() as s:
        assert s.query(MetricSnapshot).count() == 31


def test_backfill_skips_accounts_without_snapshots(db):
    with db() as s:
        s.add(Account(username="empty"))
        s.commit()
    backfill(days=30)

    with db() as s:
        assert s.query(MetricSnapshot).count() == 0
