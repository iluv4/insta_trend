"""Database models.

Two tables drive everything:

* ``Account``        — an Instagram profile we are tracking (the "reference").
* ``MetricSnapshot`` — one timestamped row of metrics per collection run. This
  is the raw time-series the analysis engine reads back.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g. "competitor"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    snapshots: Mapped[list["MetricSnapshot"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="MetricSnapshot.captured_at",
    )


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (UniqueConstraint("account_id", "captured_at", name="uq_account_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    followers: Mapped[float | None] = mapped_column(Float, nullable=True)
    following: Mapped[float | None] = mapped_column(Float, nullable=True)
    posts_count: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Engagement aggregated across the most recent posts at capture time.
    avg_likes: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_comments: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="snapshots")


# Metric columns that the analysis API is allowed to chart / forecast.
METRIC_FIELDS = (
    "followers",
    "following",
    "posts_count",
    "avg_likes",
    "avg_comments",
    "engagement_rate",
)
