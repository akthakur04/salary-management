from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.core.db import create_db_engine
from app.models import Base
from app.seed.__main__ import main


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    database_url = f"sqlite:///{tmp_path / 'seed.db'}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    yield database_url
    get_settings.cache_clear()


def test_seed_command_loads_then_leaves_existing_data_alone(
    database: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["--employees", "50"])
    main(["--employees", "50"])

    first, second = capsys.readouterr().out.strip().splitlines()
    assert first.startswith("Loaded 50 employees")
    assert second.startswith("The database already has 50 employees. Nothing was changed")


def test_seed_command_reloads_with_reset(database: str, capsys: pytest.CaptureFixture[str]) -> None:
    main(["--employees", "50"])

    main(["--employees", "50", "--reset"])

    assert capsys.readouterr().out.strip().splitlines()[-1].startswith("Loaded 50 employees")
