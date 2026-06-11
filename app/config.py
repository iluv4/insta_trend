"""Application settings loaded from environment / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Instagram data source (RapidAPI) ---
    rapidapi_key: str = ""
    rapidapi_host: str = "instagram120.p.rapidapi.com"

    # --- Storage ---
    database_url: str = "sqlite:///./insta_monitor.db"

    # --- Collection scheduler ---
    # How often the background collector snapshots every tracked account.
    collect_interval_minutes: int = 360  # 6 hours
    enable_scheduler: bool = True

    # --- Analysis defaults ---
    default_freq: str = "1D"
    default_forecast_horizon: int = 7

    # --- Demo data ---
    # When true, seed synthetic demo accounts on startup if the DB is empty.
    # Useful on hosts without shell access (e.g. Render free tier).
    seed_demo_on_startup: bool = False

    app_name: str = "Instagram Reference Monitor"


settings = Settings()
