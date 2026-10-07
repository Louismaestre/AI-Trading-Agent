import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ignore any `.env` file or variable already set on the machine."""
    for var in (
        "APP_ENV",
        "LOG_LEVEL",
        "DATABASE_URL",
        "LLM_MODEL",
        "OLLAMA_BASE_URL",
        "LLM_TEMPERATURE",
        "LLM_KNOWLEDGE_CUTOFF",
        "FUNDAMENTALS_PUBLICATION_DELAY_DAYS",
        "RISK_FREE_RATE",
        "LLM_CACHE",
    ):
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
    assert settings.llm_model == "qwen3:8b"
    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.llm_temperature == 0
    assert settings.llm_knowledge_cutoff.isoformat() == "2025-04-01"
    assert settings.fundamentals_publication_delay_days == 60
    assert settings.risk_free_rate == 0
    assert settings.llm_cache is True


def test_missing_database_url_is_rejected() -> None:
    with pytest.raises(ValidationError, match="database_url"):
        _settings()


def test_invalid_app_env_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x")
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValidationError, match="app_env"):
        _settings()
