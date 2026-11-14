from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def make_test_settings(database_url: str = "sqlite://") -> Settings:
    return Settings(_env_file=None, app_env="test", database_url=database_url)


@pytest.fixture
def app() -> FastAPI:
    return create_app(make_test_settings())


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
