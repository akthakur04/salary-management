"""App-level fixtures: test settings with a known HR login, a pinned clock, and HTTP clients."""

from collections.abc import Iterator
from datetime import date

import bcrypt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.clock import FixedClock
from app.core.config import Settings
from app.main import create_app
from app.models import Base

HR_EMAIL = "meera.iyer@acme.example"
HR_PASSWORD = "correct horse battery staple"
# Low bcrypt cost keeps tests fast; production hashes use the default cost.
HR_PASSWORD_HASH = bcrypt.hashpw(HR_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
SESSION_SECRET = "test-only-session-secret-0123456789abcdefghijklmnop"
TODAY = date(2026, 11, 12)

# Secure cookies are only sent over HTTPS, as in production.
BASE_URL = "https://testserver"


def make_test_settings(database_url: str = "sqlite://") -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_url=database_url,
        hr_admin_email=HR_EMAIL,
        hr_admin_password_hash=SecretStr(HR_PASSWORD_HASH),
        session_secret=SecretStr(SESSION_SECRET),
    )


@pytest.fixture
def app() -> FastAPI:
    app = create_app(make_test_settings(), clock=FixedClock(TODAY))
    Base.metadata.create_all(app.state.session_factory.kw["bind"])
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, base_url=BASE_URL) as test_client:
        yield test_client


@pytest.fixture
def signed_in(client: TestClient) -> TestClient:
    response = client.post("/api/v1/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
    assert response.status_code == 200
    return client
