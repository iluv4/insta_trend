"""SQLAlchemy engine / session setup."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _normalize_db_url(url: str) -> str:
    """Route managed-Postgres URLs through the psycopg (v3) driver.

    Hosts like Render and Heroku hand out ``postgres://`` or ``postgresql://``
    URLs, which SQLAlchemy would otherwise map to the (uninstalled) psycopg2
    dialect. Rewriting the scheme to ``postgresql+psycopg://`` uses the psycopg3
    driver we ship in requirements. SQLite and explicit ``+driver`` URLs are
    left untouched.
    """

    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


database_url = _normalize_db_url(settings.database_url)

# ``check_same_thread`` is only meaningful for SQLite; harmless to pass via
# connect_args guarded by the URL scheme.
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

engine = create_engine(database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    from . import models  # noqa: F401  (ensure models are registered)

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
