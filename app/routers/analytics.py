"""Time-series analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..analytics import analyze_account_metric, available_metrics
from ..database import get_db
from ..models import Account

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/metrics")
def metrics():
    return {"metrics": list(available_metrics())}


@router.get("/{account_id}")
def analyze(
    account_id: int,
    metric: str = Query("followers", description="metric to analyse"),
    freq: str | None = Query(None, description="resample frequency, e.g. 1D, 12H, 1W"),
    horizon: int | None = Query(None, ge=1, le=90, description="forecast steps"),
    db: Session = Depends(get_db),
):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    try:
        return analyze_account_metric(
            db, account, metric, freq=freq, forecast_horizon=horizon
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
