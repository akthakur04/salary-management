"""API tests share one in-memory database with the app, holding the integration reference data."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session

from tests.integration.factories import Reference, seed_reference


@pytest.fixture
def db(app: FastAPI) -> Iterator[Session]:
    with app.state.session_factory() as session:
        yield session


@pytest.fixture
def reference(db: Session) -> Reference:
    return seed_reference(db)
