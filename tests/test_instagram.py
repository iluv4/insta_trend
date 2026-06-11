"""Parsing tests for the RapidAPI client — no real network, httpx MockTransport."""

from __future__ import annotations

import httpx
import pytest

from app import instagram
from app.config import settings
from app.instagram import InstagramError, fetch_profile_metrics

LOOTER_HOST = "instagram-looter2.p.rapidapi.com"

# Trimmed instagram-looter2 /profile payload: Instagram's web profile object
# with recent posts embedded under edge_owner_to_timeline_media.edges.
LOOTER_PROFILE = {
    "status": True,
    "username": "nike",
    "full_name": "Nike",
    "edge_followed_by": {"count": 300_000_000},
    "edge_follow": {"count": 150},
    "edge_owner_to_timeline_media": {
        "count": 1200,
        "edges": [
            {"node": {"edge_liked_by": {"count": 1000}, "edge_media_to_comment": {"count": 50}}},
            {"node": {"edge_liked_by": {"count": 3000}, "edge_media_to_comment": {"count": 150}}},
        ],
    },
}


@pytest.fixture()
def looter_settings(monkeypatch):
    monkeypatch.setattr(settings, "rapidapi_host", LOOTER_HOST)
    monkeypatch.setattr(settings, "rapidapi_key", "test-key")


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_looter_profile_parsing(looter_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.host == LOOTER_HOST
        assert request.url.params["username"] == "nike"
        assert request.headers["x-rapidapi-key"] == "test-key"
        return httpx.Response(200, json=LOOTER_PROFILE)

    metrics = fetch_profile_metrics("@nike", client=_client(handler))
    assert metrics.username == "nike"
    assert metrics.full_name == "Nike"
    assert metrics.followers == 300_000_000
    assert metrics.following == 150
    assert metrics.posts_count == 1200
    assert metrics.avg_likes == 2000
    assert metrics.avg_comments == 100
    assert metrics.engagement_rate == pytest.approx(2100 / 300_000_000 * 100)


def test_looter_status_false_raises(looter_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": False, "message": "user not found"})

    with pytest.raises(InstagramError, match="user not found"):
        fetch_profile_metrics("ghost", client=_client(handler))


def test_looter_http_error_raises(looter_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    with pytest.raises(InstagramError, match="profile fetch failed"):
        fetch_profile_metrics("nike", client=_client(handler))


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "rapidapi_key", "")
    with pytest.raises(InstagramError, match="RAPIDAPI_KEY"):
        fetch_profile_metrics("nike", client=_client(lambda r: httpx.Response(200, json={})))


def test_instagram120_still_uses_post(monkeypatch):
    monkeypatch.setattr(settings, "rapidapi_host", "instagram120.p.rapidapi.com")
    monkeypatch.setattr(settings, "rapidapi_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json={"result": {"follower_count": 5000, "full_name": "X"}})
        return httpx.Response(200, json={"result": {"edges": []}})

    metrics = fetch_profile_metrics("brand", client=_client(handler))
    assert metrics.followers == 5000
    assert metrics.full_name == "X"
