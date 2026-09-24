import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ignore any `.env` file or variable already set on the machine."""
    for var in ("APP_ENV", "LOG_LEVEL", "DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)


def _settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x")
    monkeypatch.setenv("APP_ENV", "production")

    settings = _settings()

    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/x"
    assert settings.app_env == "production"
    assert settings.log_level == "INFO"


def test_missing_database_url_is_rejected() -> None:
    with pytest.raises(ValidationError, match="database_url"):
        _settings()


def test_invalid_app_env_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x")
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValidationError, match="app_env"):
        _settings()
