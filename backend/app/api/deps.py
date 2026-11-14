"""FastAPI dependencies shared by routers."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import UnauthenticatedError
from app.core.security import SESSION_COOKIE, read_session_token


def get_db_session(request: Request) -> Iterator[Session]:
    """One session per request, closed when the request ends."""
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


def get_settings_from_app(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


def require_session(request: Request) -> str:
    """The gate on every protected route: a valid session cookie, or 401."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise UnauthenticatedError("Sign in to continue.")
    settings = get_settings_from_app(request)
    return read_session_token(token, settings.session_secret.get_secret_value())
