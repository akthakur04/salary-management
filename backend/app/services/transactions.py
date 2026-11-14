"""One unit of work per use case: commit everything, or roll back everything."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def transaction(session: Session) -> Iterator[None]:
    try:
        yield
        session.commit()
    except BaseException:
        session.rollback()
        raise
