"""
Centralized database engine factory supporting SQLite and PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Any, cast

from sqlalchemy import Engine, event
from sqlmodel import Session, create_engine

import logfire
from care_pilot.config.app import get_settings
from care_pilot.platform.observability import get_logger

logfire_api = cast(Any, logfire)

logger = get_logger(__name__)


def _configure_sqlite_engine(engine: Engine) -> None:
    """Configure SQLite-specific behaviors like WAL mode and foreign keys."""

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@lru_cache(maxsize=1)
def get_db_engine() -> Engine:
    """
    Create and return a configured SQLAlchemy engine based on application settings.
    Result is cached to ensure connection pooling works correctly.
    """
    settings = get_settings()
    backend = settings.storage.app_data_backend

    if backend == "postgresql":
        if not settings.storage.api_postgres_url:
            raise ValueError("DATABASE_URL must be set for postgresql backend")

        logger.info("db_engine_init backend=postgresql")
        # Use standard high-performance defaults for Postgres
        engine = create_engine(
            settings.storage.api_postgres_url,
            pool_size=settings.storage.api_postgres_pool_size,
            max_overflow=10,
            pool_pre_ping=True,
        )
        logfire_api.instrument_sqlalchemy(engine)
        return engine

    # Default to SQLite
    db_path = settings.storage.api_sqlite_db_path
    db_url = f"sqlite:///{db_path}"
    logger.info("db_engine_init backend=sqlite path=%s", db_path)

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},  # Required for async/multi-thread use with SQLite
    )
    _configure_sqlite_engine(engine)
    logfire_api.instrument_sqlalchemy(engine)
    return engine


def get_session() -> Generator[Session, None, None]:
    """Provide a thread-safe SQLModel session."""
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
