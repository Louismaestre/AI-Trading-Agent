"""Application settings, loaded from environment variables and the root `.env` file."""

import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # `../.env` is the root file shared with Docker Compose. Real env vars take precedence.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str
    llm_model: str = "qwen3:8b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    llm_temperature: float = 0
    # Replays must start after this date so the model cannot "remember" later prices.
    llm_knowledge_cutoff: datetime.date = datetime.date(2025, 4, 1)
    # A quarter is unknown until this many days after period_end (yfinance has no filing date).
    fundamentals_publication_delay_days: int = 60
    # Annual risk-free rate used for Sharpe / Sortino (e.g. 0.02 for 2 % €STR).
    risk_free_rate: Decimal = Decimal("0")


@lru_cache
def get_settings() -> Settings:
    return Settings()
