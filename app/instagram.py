"""Instagram data source client (RapidAPI / instagram120).

Wraps the same RapidAPI host the sibling project uses. Network failures and a
missing API key are turned into a typed ``InstagramError`` so callers (the
collector, the API layer) can degrade gracefully instead of crashing the
scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .config import settings


class InstagramError(RuntimeError):
    pass


@dataclass
class ProfileMetrics:
    username: str
    full_name: str | None
    followers: float | None
    following: float | None
    posts_count: float | None
    avg_likes: float | None
    avg_comments: float | None
    engagement_rate: float | None


def _headers() -> dict[str, str]:
    if not settings.rapidapi_key:
        raise InstagramError("RAPIDAPI_KEY is not configured")
    return {
        "x-rapidapi-key": settings.rapidapi_key,
        "x-rapidapi-host": settings.rapidapi_host,
        "Content-Type": "application/json",
    }


def _safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_engagement(posts: list[dict]) -> tuple[float | None, float | None]:
    """Mean likes / comments across whatever recent posts the API returned."""
    likes: list[float] = []
    comments: list[float] = []
    for edge in posts:
        node = edge.get("node", edge)
        like = _safe_float(
            node.get("like_count")
            or node.get("edge_liked_by", {}).get("count")
            or node.get("edge_media_preview_like", {}).get("count")
        )
        comment = _safe_float(
            node.get("comment_count")
            or node.get("edge_media_to_comment", {}).get("count")
        )
        if like is not None:
            likes.append(like)
        if comment is not None:
            comments.append(comment)
    avg_likes = sum(likes) / len(likes) if likes else None
    avg_comments = sum(comments) / len(comments) if comments else None
    return avg_likes, avg_comments


def _build_metrics(username: str, result: dict, post_edges: list[dict]) -> ProfileMetrics:
    """Map whichever profile fields are present onto ``ProfileMetrics``."""
    followers = _safe_float(
        result.get("follower_count")
        or result.get("followers")
        or result.get("edge_followed_by", {}).get("count")
    )
    following = _safe_float(
        result.get("following_count")
        or result.get("following")
        or result.get("edge_follow", {}).get("count")
    )
    posts_count = _safe_float(
        result.get("media_count")
        or result.get("posts_count")
        or result.get("edge_owner_to_timeline_media", {}).get("count")
    )
    full_name = result.get("full_name") or result.get("fullName")

    avg_likes, avg_comments = _extract_engagement(post_edges)
    engagement_rate = None
    if followers and followers > 0 and (avg_likes is not None or avg_comments is not None):
        engagement_rate = ((avg_likes or 0) + (avg_comments or 0)) / followers * 100.0

    return ProfileMetrics(
        username=username,
        full_name=full_name,
        followers=followers,
        following=following,
        posts_count=posts_count,
        avg_likes=avg_likes,
        avg_comments=avg_comments,
        engagement_rate=engagement_rate,
    )


def _fetch_instagram120(username: str, client: httpx.Client) -> ProfileMetrics:
    """instagram120: POST ``/api/instagram/profile`` and ``/api/instagram/posts``."""
    base = f"https://{settings.rapidapi_host}/api/instagram"
    try:
        profile_resp = client.post(f"{base}/profile", json={"username": username}, headers=_headers())
        profile_resp.raise_for_status()
        profile = profile_resp.json()
    except httpx.HTTPError as exc:
        raise InstagramError(f"profile fetch failed for @{username}: {exc}") from exc

    result = profile.get("result", profile.get("data", profile))

    edges: list[dict] = []
    try:
        posts_resp = client.post(f"{base}/posts", json={"username": username}, headers=_headers())
        posts_resp.raise_for_status()
        posts_data = posts_resp.json()
        edges = posts_data.get("result", {}).get("edges") or posts_data.get("edges") or []
    except httpx.HTTPError:
        pass  # engagement is best-effort; profile counts are the priority

    return _build_metrics(username, result, edges)


def _fetch_looter(username: str, client: httpx.Client) -> ProfileMetrics:
    """instagram-looter2: GET ``/profile?username=…``.

    Returns the Instagram web profile object (``edge_followed_by`` etc.),
    which usually embeds the recent posts under
    ``edge_owner_to_timeline_media.edges`` — enough for engagement averages
    without a second request.
    """
    url = f"https://{settings.rapidapi_host}/profile"
    try:
        resp = client.get(url, params={"username": username}, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise InstagramError(f"profile fetch failed for @{username}: {exc}") from exc

    if isinstance(data, dict) and data.get("status") is False:
        raise InstagramError(
            f"profile fetch failed for @{username}: {data.get('message') or 'unknown error'}"
        )

    # The user object may sit at the top level or be nested under data.user.
    result = data.get("data", {}).get("user") if isinstance(data.get("data"), dict) else None
    result = result or data.get("user") or data

    edges = result.get("edge_owner_to_timeline_media", {}).get("edges") or []
    return _build_metrics(username, result, edges)


def fetch_profile_metrics(username: str, *, client: httpx.Client | None = None) -> ProfileMetrics:
    """Fetch a single point-in-time metrics reading for ``username``.

    The request shape is chosen from ``RAPIDAPI_HOST``: instagram-looter2 uses
    a single GET, instagram120 (the default) uses two POSTs. Whichever fields
    are present are mapped onto ``ProfileMetrics``; engagement rate =
    (avg likes + avg comments) / followers.
    """
    username = username.lstrip("@").strip()
    owns_client = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        if "looter" in settings.rapidapi_host:
            return _fetch_looter(username, client)
        return _fetch_instagram120(username, client)
    finally:
        if owns_client:
            client.close()
