"""API + collector integration tests using a fake Instagram source."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database, scheduler
from app.collector import collect_account
from app.main import app
from app.models import Account


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Isolated in-memory-ish SQLite per test, and no background scheduler.
    engine = create_engine(
        f"sqlite:///{tmp_path/'test.db'}", connect_args={"check_same_thread": False}, future=True
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSession)
    monkeypatch.setattr(scheduler, "SessionLocal", TestingSession)
    database.Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db
    # Disable the real scheduler during the app lifespan.
    monkeypatch.setattr("app.main.start_scheduler", lambda: None)
    with TestClient(app) as c:
        c._Session = TestingSession  # stash for tests that seed data directly
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_account_crud(client):
    r = client.post("/api/accounts", json={"username": "@Nike", "label": "competitor"})
    assert r.status_code == 201
    acc = r.json()
    assert acc["username"] == "nike"  # normalised
    assert client.post("/api/accounts", json={"username": "nike"}).status_code == 409
    assert len(client.get("/api/accounts").json()) == 1
    assert client.delete(f"/api/accounts/{acc['id']}").status_code == 204
    assert client.get("/api/accounts").json() == []


class _FakeMetrics:
    def __init__(self, followers):
        self.full_name = "Fake"
        self.followers = followers
        self.following = 100
        self.posts_count = 50
        self.avg_likes = followers * 0.05
        self.avg_comments = followers * 0.005
        self.engagement_rate = 5.5


def test_collect_and_analyze(client):
    acc = client.post("/api/accounts", json={"username": "growthco"}).json()

    # Seed a rising follower history directly via the collector with a fake source.
    Session = client._Session
    db = Session()
    account = db.get(Account, acc["id"])
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(20):
        collect_account(
            db,
            account,
            fetch_fn=lambda u, n=i: _FakeMetrics(10000 + n * 500),
            captured_at=base + timedelta(days=i),
        )
    db.close()

    snaps = client.get(f"/api/accounts/{acc['id']}/snapshots").json()
    assert len(snaps) == 20

    res = client.get(f"/api/analytics/{acc['id']}?metric=followers&horizon=5").json()
    assert res["trend"] == "rising"
    assert res["count"] == 20
    assert res["growth"]["absolute_change"] == pytest.approx(19 * 500)
    assert len(res["forecast"]["values"]) == 5
    assert res["forecast"]["values"][-1] > res["growth"]["current"]  # keeps climbing


def test_analyze_unknown_metric(client):
    acc = client.post("/api/accounts", json={"username": "x"}).json()
    r = client.get(f"/api/analytics/{acc['id']}?metric=bogus")
    assert r.status_code == 400


def test_backfill_endpoint(client):
    acc = client.post("/api/accounts", json={"username": "demo"}).json()

    # No snapshots yet → 400 (need one real anchor first).
    assert client.post(f"/api/accounts/{acc['id']}/backfill").status_code == 400

    Session = client._Session
    db = Session()
    account = db.get(Account, acc["id"])
    collect_account(db, account, fetch_fn=lambda u: _FakeMetrics(50_000))
    db.close()

    r = client.post(f"/api/accounts/{acc['id']}/backfill?days=30")
    assert r.status_code == 200
    assert r.json()["added"] == 30

    snaps = client.get(f"/api/accounts/{acc['id']}/snapshots").json()
    assert len(snaps) == 31
    followers = [s["followers"] for s in sorted(snaps, key=lambda s: s["captured_at"])]
    assert followers[-1] == 50_000  # the real reading stays the endpoint
    assert followers[0] < 50_000  # history grows into it

    # Second run is a no-op once the span is reached.
    assert client.post(f"/api/accounts/{acc['id']}/backfill?days=30").json()["added"] == 0

    # Unknown account → 404.
    assert client.post("/api/accounts/999/backfill").status_code == 404


def test_metrics_endpoint(client):
    body = client.get("/api/analytics/metrics").json()
    assert "followers" in body["metrics"]
    assert "engagement_rate" in body["metrics"]
