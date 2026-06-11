"""Synthetic time-series dataset for insta_trend hashtag analysis.

The :mod:`insta_trend` core ranks hashtags from a *static* batch of posts. To
demonstrate **time-series analysis** we need the same hashtags observed over
many days. This module generates a deterministic, realistic daily panel:

    date, hashtag, posts, likes

Each hashtag is built from three classic time-series components so the later
analysis (trend, moving average, weekly seasonality, forecast) has something
real to find:

    value(t) = level + trend * t + seasonal(weekday) + noise

The generator is seeded, so every run — and therefore every chart and every
slide — is reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Hashtags taken from the project's own SAMPLE_POSTS so the deck stays on-brand.
START_DATE = "2026-01-01"
N_DAYS = 84  # 12 weeks


@dataclass(frozen=True)
class TagProfile:
    """Time-series shape for one hashtag."""

    name: str
    level: float          # baseline daily posts
    trend_per_day: float  # linear drift (can be negative = fading)
    weekly_amp: float     # strength of the weekday seasonal swing
    peak_weekday: int     # 0=Mon ... 6=Sun, weekday with the seasonal peak
    noise: float          # std-dev of multiplicative noise
    likes_per_post: float


PROFILES: list[TagProfile] = [
    TagProfile("sunset",      level=42, trend_per_day=0.55, weekly_amp=0.22, peak_weekday=5, noise=0.10, likes_per_post=31),
    TagProfile("coffee",      level=60, trend_per_day=0.05, weekly_amp=0.30, peak_weekday=0, noise=0.08, likes_per_post=12),
    TagProfile("hiking",      level=18, trend_per_day=0.70, weekly_amp=0.45, peak_weekday=6, noise=0.14, likes_per_post=24),
    TagProfile("devlife",     level=33, trend_per_day=-0.28, weekly_amp=0.18, peak_weekday=2, noise=0.09, likes_per_post=9),
    TagProfile("outdoors",    level=22, trend_per_day=0.40, weekly_amp=0.38, peak_weekday=6, noise=0.12, likes_per_post=18),
    TagProfile("photography", level=28, trend_per_day=0.30, weekly_amp=0.20, peak_weekday=5, noise=0.11, likes_per_post=21),
]


def build_panel(seed: int = 7) -> pd.DataFrame:
    """Return a tidy daily panel: one row per (date, hashtag).

    Columns: ``date``, ``hashtag``, ``posts``, ``likes``.
    """

    rng = np.random.default_rng(seed)
    dates = pd.date_range(START_DATE, periods=N_DAYS, freq="D")
    t = np.arange(N_DAYS)

    frames = []
    for p in PROFILES:
        weekday = dates.weekday.to_numpy()
        seasonal = p.weekly_amp * np.cos(2 * np.pi * (weekday - p.peak_weekday) / 7)
        base = (p.level + p.trend_per_day * t) * (1 + seasonal)
        shock = rng.normal(1.0, p.noise, size=N_DAYS)
        posts = np.clip(np.round(base * shock), 0, None).astype(int)
        likes = np.round(posts * p.likes_per_post * rng.normal(1.0, 0.12, size=N_DAYS)).astype(int)
        frames.append(
            pd.DataFrame(
                {"date": dates, "hashtag": p.name, "posts": posts, "likes": likes}
            )
        )

    panel = pd.concat(frames, ignore_index=True)
    return panel


def wide_posts(panel: pd.DataFrame) -> pd.DataFrame:
    """Pivot to a date-indexed wide frame of daily posts (one column per tag)."""

    wide = panel.pivot(index="date", columns="hashtag", values="posts")
    return wide.sort_index()


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    panel = build_panel()
    print(panel.head(12).to_string(index=False))
    print("\nshape:", panel.shape)
    print("date range:", panel["date"].min().date(), "->", panel["date"].max().date())
