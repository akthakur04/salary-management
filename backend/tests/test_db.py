from sqlalchemy import text

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
