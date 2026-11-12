"""Database engine and session factory. SQLite in development and tests, Postgres in production."""

from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _is_in_memory_sqlite(database_url: str) -> bool:
    return database_url in ("sqlite://", "sqlite:///:memory:")


def create_db_engine(database_url: str) -> Engine:
    """Create an engine with the connection settings each backend needs.

    In-memory SQLite gets a single shared connection, otherwise every session
    would see its own empty database.
    """
    if not database_url.startswith("sqlite"):
        return create_engine(database_url, pool_pre_ping=True)

    kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
    if _is_in_memory_sqlite(database_url):
        kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
