"""Application factory. Run with `uvicorn app.main:create_app --factory`."""

from fastapi import APIRouter, Depends, FastAPI

from app.api import auth, health
from app.api.deps import require_session
from app.api.errors import register_error_handlers
from app.core.clock import Clock, SystemClock
from app.core.config import Settings, ensure_auth_configured, get_settings
from app.core.db import create_db_engine, create_session_factory

API_PREFIX = "/api/v1"

# Routes reachable without a session. Everything else requires one (tested by route table).
PUBLIC_PATHS = frozenset({f"{API_PREFIX}/health", f"{API_PREFIX}/auth/login"})


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    settings = settings or get_settings()
    ensure_auth_configured(settings)

    app = FastAPI(title="ACME Salary Management API", version="0.1.0")
    app.state.settings = settings
    app.state.clock = clock or SystemClock()
    app.state.session_factory = create_session_factory(create_db_engine(settings.database_url))
    register_error_handlers(app)

    public = APIRouter()
    public.include_router(health.router)
    public.include_router(auth.public_router)

    protected = APIRouter(dependencies=[Depends(require_session)])
    protected.include_router(auth.router)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(public)
    api.include_router(protected)
    app.include_router(api)
    return app
