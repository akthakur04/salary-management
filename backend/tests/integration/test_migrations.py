"""The Alembic migrations build exactly the schema the ORM models describe."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

from app.core.db import create_db_engine
from app.models import Base

ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


def _alembic_config(database_url: str) -> Config:
    config = Config(ALEMBIC_INI)
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    return config


def test_migrated_schema_matches_the_models(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migrated.db'}"

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_db_engine(database_url)
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert differences == []


def test_migrations_downgrade_to_an_empty_database(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = _alembic_config(database_url)
    command.upgrade(config, "head")

    command.downgrade(config, "base")

    engine = create_db_engine(database_url)
    remaining = inspect(engine).get_table_names()
    engine.dispose()
    assert remaining == ["alembic_version"]
