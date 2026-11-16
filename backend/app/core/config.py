"""Application settings, read from environment variables (and a local `.env` in development)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SESSION_SECRET_LENGTH = 32

# Hosts such as Render hand out postgres:// or postgresql:// URLs, which SQLAlchemy
# would open with psycopg2. The app ships psycopg (version 3), so name it.
_HOSTED_POSTGRES_SCHEMES = ("postgres://", "postgresql://")
_PSYCOPG_SCHEME = "postgresql+psycopg://"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./salary.db"

    # The single HR login (M9). The password is stored only as a bcrypt hash.
    hr_admin_email: str = ""
    hr_admin_password_hash: SecretStr = SecretStr("")
    session_secret: SecretStr = SecretStr("")
    session_hours: int = 8
    cookie_secure: bool = True

    # Pending changes due within this many days count as exceptions (Overview, sidebar badge).
    pending_window_days: int = 60

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_for_postgres(cls, url: str) -> str:
        for scheme in _HOSTED_POSTGRES_SCHEMES:
            if url.startswith(scheme):
                return _PSYCOPG_SCHEME + url.removeprefix(scheme)
        return url


def ensure_auth_configured(settings: Settings) -> None:
    """Fail at start-up, not at first login, if the HR login isn't set up."""
    problems = []
    if not settings.hr_admin_email.strip():
        problems.append("HR_ADMIN_EMAIL is empty")
    if not settings.hr_admin_password_hash.get_secret_value().startswith("$2"):
        problems.append("HR_ADMIN_PASSWORD_HASH is not a bcrypt hash")
    if len(settings.session_secret.get_secret_value()) < MIN_SESSION_SECRET_LENGTH:
        problems.append(f"SESSION_SECRET is shorter than {MIN_SESSION_SECRET_LENGTH} characters")
    if problems:
        raise RuntimeError(
            "The HR login isn't configured: "
            + "; ".join(problems)
            + ". See .env.example and `python -m app.core.hash_password`."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
