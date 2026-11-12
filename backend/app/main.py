"""Application factory. Run with `uvicorn app.main:create_app --factory`."""

from fastapi import APIRouter, FastAPI

from app.api import health
from app.api.errors import register_error_handlers
from app.core.config import Settings, get_settings
from app.core.db import create_db_engine, create_session_factory

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title="ACME Salary Management API", version="0.1.0")
    app.state.settings = settings
    app.state.session_factory = create_session_factory(create_db_engine(settings.database_url))
    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(health.router)
    app.include_router(api)
    return app
