import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.db import create_db_engine, create_session_factory


def test_in_memory_sqlite_sessions_share_one_database() -> None:
    session_factory = create_session_factory(create_db_engine("sqlite://"))
    with session_factory() as writer:
        writer.execute(text("CREATE TABLE note (body TEXT)"))
        writer.execute(text("INSERT INTO note VALUES ('kept')"))
        writer.commit()

    with session_factory() as reader:
        body = reader.execute(text("SELECT body FROM note")).scalar_one()

    assert body == "kept"


def test_sqlite_connections_enforce_foreign_keys() -> None:
    session_factory = create_session_factory(create_db_engine("sqlite://"))
    with session_factory() as session:
        session.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
        session.execute(text("CREATE TABLE child (parent_id INTEGER REFERENCES parent (id))"))

        with pytest.raises(IntegrityError):
            session.execute(text("INSERT INTO child VALUES (42)"))
