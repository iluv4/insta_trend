"""Bridge between stored snapshots and the time-series engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import timeseries as ts
from .config import settings
from .models import METRIC_FIELDS, Account, MetricSnapshot


def _load_points(db: Session, account_id: int, metric: str) -> list[tuple[Any, float]]:
    rows = db.scalars(
        select(MetricSnapshot)
        .where(MetricSnapshot.account_id == account_id)
        .order_by(MetricSnapshot.captured_at)
    ).all()
    points: list[tuple[Any, float]] = []
    for row in rows:
        value = getattr(row, metric)
        if value is not None:
            points.append((row.captured_at, value))
    return points


def analyze_account_metric(
    db: Session,
    account: Account,
    metric: str,
    *,
    freq: str | None = None,
    forecast_horizon: int | None = None,
) -> dict[str, Any]:
    if metric not in METRIC_FIELDS:
        raise ValueError(f"unknown metric '{metric}'. choose one of {METRIC_FIELDS}")

    points = _load_points(db, account.id, metric)
    result = ts.analyze(
        points,
        freq=freq or settings.default_freq,
        forecast_horizon=forecast_horizon or settings.default_forecast_horizon,
        name=metric,
    )
    result["account"] = {
        "id": account.id,
        "username": account.username,
        "full_name": account.full_name,
        "label": account.label,
    }
    result["metric"] = metric
    return result


def available_metrics() -> tuple[str, ...]:
    return METRIC_FIELDS
