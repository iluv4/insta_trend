"""Functional core for ranking trending hashtags.

The model is deliberately small and dependency-free so it is easy to test and
to plug a real Instagram data source in later. A :class:`Post` is whatever the
caller already has; :func:`rank_trends` turns a collection of posts into a
ranked list of hashtags weighted by how often they appear and how much
engagement (likes) they attract.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

_HASHTAG_RE = re.compile(r"#(\w+)", re.UNICODE)


@dataclass(frozen=True)
class Post:
    """A single Instagram-style post.

    Only the fields needed for trend scoring are modelled. ``likes`` defaults to
    zero so callers can rank by raw frequency alone.
    """

    caption: str
    likes: int = 0


@dataclass(frozen=True)
class TrendScore:
    """The computed standing of one hashtag within a set of posts."""

    hashtag: str
    count: int
    total_likes: int
    score: float = field(compare=False)


def extract_hashtags(caption: str) -> list[str]:
    """Return the lowercased hashtags found in ``caption``, in order.

    The leading ``#`` is stripped. Matching is case-insensitive so ``#Coffee``
    and ``#coffee`` are treated as the same tag.
    """

    return [match.lower() for match in _HASHTAG_RE.findall(caption)]


def rank_trends(posts: list[Post], *, like_weight: float = 0.01) -> list[TrendScore]:
    """Rank hashtags across ``posts`` from most to least trending.

    The score for a hashtag is ``count + like_weight * total_likes``: appearing
    in more posts is the primary signal, with engagement as a tie-breaking
    boost. Ties are broken alphabetically so the ordering is deterministic.

    Raises:
        ValueError: if ``like_weight`` is negative.
    """

    if like_weight < 0:
        raise ValueError("like_weight must be non-negative")

    counts: dict[str, int] = defaultdict(int)
    likes: dict[str, int] = defaultdict(int)

    for post in posts:
        for tag in set(extract_hashtags(post.caption)):
            counts[tag] += 1
            likes[tag] += post.likes

    scores = [
        TrendScore(
            hashtag=tag,
            count=counts[tag],
            total_likes=likes[tag],
            score=counts[tag] + like_weight * likes[tag],
        )
        for tag in counts
    ]
    scores.sort(key=lambda s: (-s.score, s.hashtag))
    return scores
