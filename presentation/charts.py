"""Time-series analysis + chart rendering for the insta_trend deck.

Every figure is saved as a PNG into ``presentation/assets/`` so the slide
builder can embed them. Chart labels are kept in English (the hashtags are
English anyway) to avoid any missing-glyph issues; the Korean narrative lives
in the slide text.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from timeseries_data import build_panel, wide_posts  # noqa: E402

ASSETS = Path(__file__).resolve().parent / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

# A small, consistent palette (Instagram-ish gradient endpoints + supports).
PALETTE = {
    "sunset": "#E1306C",
    "coffee": "#8a5a44",
    "hiking": "#2E8B57",
    "devlife": "#405DE6",
    "outdoors": "#F77737",
    "photography": "#833AB4",
}
GRID = "#E6E6E6"
INK = "#222222"

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "axes.edgecolor": "#CCCCCC",
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "font.size": 11,
    }
)

FIGSIZE = (10.2, 5.2)


def _save(fig: plt.Figure, name: str) -> Path:
    path = ASSETS / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _style_dates(ax) -> None:
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


# --------------------------------------------------------------------------- #
# Chart 1 — raw daily time series for every hashtag
# --------------------------------------------------------------------------- #
def chart_overview(wide: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tag in wide.columns:
        ax.plot(wide.index, wide[tag], color=PALETTE[tag], lw=1.6, label=f"#{tag}")
    ax.set_title("Daily posts per hashtag — 12 weeks (raw signal)", fontweight="bold")
    ax.set_ylabel("posts / day")
    ax.legend(ncol=3, frameon=False, fontsize=9, loc="upper left")
    _style_dates(ax)
    return _save(fig, "01_overview.png")


# --------------------------------------------------------------------------- #
# Chart 2 — raw vs 7-day moving average for one focus hashtag
# --------------------------------------------------------------------------- #
def chart_moving_average(wide: pd.DataFrame, tag: str = "hiking") -> Path:
    s = wide[tag]
    ma7 = s.rolling(7, center=True).mean()
    ma14 = s.rolling(14, center=True).mean()

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(s.index, s, color="#BBBBBB", lw=1.3, label="raw")
    ax.plot(ma7.index, ma7, color=PALETTE[tag], lw=2.6, label="7-day MA")
    ax.plot(ma14.index, ma14, color=INK, lw=2.0, ls="--", label="14-day MA")
    ax.set_title(f"Smoothing #{tag}: moving averages remove daily noise", fontweight="bold")
    ax.set_ylabel("posts / day")
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    _style_dates(ax)
    return _save(fig, "02_moving_average.png")


# --------------------------------------------------------------------------- #
# Chart 3 — additive decomposition (trend / seasonal / residual)
# --------------------------------------------------------------------------- #
def _decompose(s: pd.Series, period: int = 7):
    trend = s.rolling(period, center=True).mean()
    detrended = s - trend
    seasonal = detrended.groupby(s.index.weekday).transform("mean")
    residual = s - trend - seasonal
    return trend, seasonal, residual


def chart_decomposition(wide: pd.DataFrame, tag: str = "hiking") -> Path:
    s = wide[tag]
    trend, seasonal, residual = _decompose(s)

    fig, axes = plt.subplots(4, 1, figsize=(10.2, 6.6), sharex=True)
    axes[0].plot(s.index, s, color=PALETTE[tag], lw=1.5)
    axes[0].set_ylabel("observed")
    axes[1].plot(trend.index, trend, color=INK, lw=2.0)
    axes[1].set_ylabel("trend")
    axes[2].plot(seasonal.index, seasonal, color="#F77737", lw=1.4)
    axes[2].set_ylabel("weekly")
    axes[3].plot(residual.index, residual, color="#999999", lw=1.0)
    axes[3].axhline(0, color="#CCCCCC", lw=0.8)
    axes[3].set_ylabel("residual")
    for ax in axes:
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    _style_dates(axes[-1])
    axes[0].set_title(f"Additive decomposition of #{tag}", fontweight="bold")
    return _save(fig, "03_decomposition.png")


# --------------------------------------------------------------------------- #
# Chart 4 — weekly seasonality profile (avg posts by weekday)
# --------------------------------------------------------------------------- #
def chart_weekly_profile(wide: pd.DataFrame) -> Path:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tag in wide.columns:
        s = wide[tag]
        by_wd = s.groupby(s.index.weekday).mean()
        # index 0..6 -> normalise to % of that tag's mean to compare shapes
        norm = by_wd / by_wd.mean() * 100
        ax.plot(range(7), norm.values, marker="o", color=PALETTE[tag], lw=1.8, label=f"#{tag}")
    ax.axhline(100, color="#CCCCCC", lw=1.0, ls=":")
    ax.set_xticks(range(7))
    ax.set_xticklabels(days)
    ax.set_ylabel("posts vs own avg (%)")
    ax.set_title("Weekly seasonality: when each hashtag peaks", fontweight="bold")
    ax.legend(ncol=3, frameon=False, fontsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    return _save(fig, "04_weekly_profile.png")


# --------------------------------------------------------------------------- #
# Chart 5 — growth: indexed cumulative posts (momentum ranking)
# --------------------------------------------------------------------------- #
def chart_growth(wide: pd.DataFrame) -> Path:
    # 7-day MA, then index to 100 at the first valid point.
    fig, ax = plt.subplots(figsize=FIGSIZE)
    growth = {}
    for tag in wide.columns:
        ma = wide[tag].rolling(7, center=True).mean().dropna()
        indexed = ma / ma.iloc[0] * 100
        ax.plot(indexed.index, indexed, color=PALETTE[tag], lw=2.0, label=f"#{tag}")
        growth[tag] = indexed.iloc[-1] - 100
    ax.axhline(100, color="#CCCCCC", lw=1.0, ls=":")
    ax.set_ylabel("index (start = 100)")
    ax.set_title("Momentum: growth indexed to week 1", fontweight="bold")
    ax.legend(ncol=3, frameon=False, fontsize=9, loc="upper left")
    _style_dates(ax)
    _save(fig, "05_growth.png")
    return growth  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# Chart 6 — forecast: trend + weekly seasonality projected 14 days ahead
# --------------------------------------------------------------------------- #
def _fit_forecast(s: pd.Series, horizon: int = 14):
    t = np.arange(len(s))
    # linear trend via least squares
    coef = np.polyfit(t, s.values, 1)
    trend_fit = np.polyval(coef, t)
    detrended = s.values - trend_fit
    weekday = s.index.weekday.to_numpy()
    seasonal_by_wd = pd.Series(detrended).groupby(weekday).mean()

    future_t = np.arange(len(s), len(s) + horizon)
    future_idx = pd.date_range(s.index[-1] + pd.Timedelta(days=1), periods=horizon)
    future_wd = future_idx.weekday.to_numpy()
    future = np.polyval(coef, future_t) + seasonal_by_wd.reindex(future_wd).to_numpy()

    resid_std = float(np.std(detrended - seasonal_by_wd.reindex(weekday).to_numpy()))
    return future_idx, np.clip(future, 0, None), resid_std, coef[0]


def chart_forecast(wide: pd.DataFrame, tag: str = "sunset", horizon: int = 14) -> Path:
    s = wide[tag]
    fidx, fvals, resid_std, slope = _fit_forecast(s, horizon)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(s.index, s, color="#BBBBBB", lw=1.4, label="history")
    ax.plot(s.rolling(7, center=True).mean(), color=PALETTE[tag], lw=2.2, label="7-day MA")
    ax.plot(fidx, fvals, color=INK, lw=2.4, ls="--", label="forecast (+14d)")
    ax.fill_between(fidx, fvals - 1.96 * resid_std, fvals + 1.96 * resid_std,
                    color=PALETTE[tag], alpha=0.15, label="95% band")
    ax.set_ylabel("posts / day")
    ax.set_title(f"Forecast for #{tag}: trend + weekly seasonality (+14 days)", fontweight="bold")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    _style_dates(ax)
    _save(fig, "06_forecast.png")
    return slope  # type: ignore[return-value]


def render_all() -> dict:
    """Render every chart and return a few computed numbers for the slides."""

    panel = build_panel()
    wide = wide_posts(panel)

    chart_overview(wide)
    chart_moving_average(wide, "hiking")
    chart_decomposition(wide, "hiking")
    chart_weekly_profile(wide)
    growth = chart_growth(wide)
    slope = chart_forecast(wide, "sunset")

    # numbers used in the narrative
    totals = panel.groupby("hashtag")["posts"].sum().sort_values(ascending=False)
    first_wk = wide.iloc[:7].mean()
    last_wk = wide.iloc[-7:].mean()
    growth_pct = ((last_wk - first_wk) / first_wk * 100).sort_values(ascending=False)

    return {
        "n_days": len(wide),
        "n_tags": wide.shape[1],
        "n_posts": int(panel["posts"].sum()),
        "date_start": wide.index.min().date().isoformat(),
        "date_end": wide.index.max().date().isoformat(),
        "totals": totals,
        "growth_pct": growth_pct,
        "sunset_slope": float(slope),
    }


if __name__ == "__main__":
    stats = render_all()
    print("Charts written to", ASSETS)
    print("posts:", stats["n_posts"], "tags:", stats["n_tags"], "days:", stats["n_days"])
    print("\nGrowth (last week vs first week):")
    print(stats["growth_pct"].round(1).to_string())
