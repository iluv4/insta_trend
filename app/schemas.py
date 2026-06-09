"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    username: str = Field(..., description="Instagram handle, with or without '@'")
    label: str | None = Field(None, description="Free-form tag, e.g. 'competitor'")


class SnapshotOut(BaseModel):
    id: int
    captured_at: datetime
    followers: float | None
    following: float | None
    posts_count: float | None
    avg_likes: float | None
    avg_comments: float | None
    engagement_rate: float | None

    model_config = {"from_attributes": True}


class AccountOut(BaseModel):
    id: int
    username: str
    full_name: str | None
    label: str | None
    created_at: datetime
    snapshot_count: int = 0

    model_config = {"from_attributes": True}
