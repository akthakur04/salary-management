"""Each test gets its own in-memory SQLite database, the reference data, and a pinned clock."""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.core.clock import FixedClock
from app.core.db import create_db_engine, create_session_factory
from app.models import Base
from tests.integration.factories import TODAY, Reference, seed_reference


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_db_engine("sqlite://")
    Base.metadata.create_all(engine)
    with create_session_factory(engine)() as db_session:
        yield db_session
    engine.dispose()


@pytest.fixture
def reference(session: Session) -> Reference:
    return seed_reference(session)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(TODAY)
