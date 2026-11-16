import pytest

from app.core.config import Settings


def test_settings_default_to_local_sqlite_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.database_url == "sqlite:///./salary.db"


def test_settings_read_database_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/salary")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/salary"


@pytest.mark.parametrize(
    "provided",
    [
        "postgres://user:pass@db:5432/salary",
        "postgresql://user:pass@db:5432/salary",
    ],
)
def test_hosted_postgres_urls_use_the_psycopg_driver(
    monkeypatch: pytest.MonkeyPatch, provided: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", provided)

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/salary"
