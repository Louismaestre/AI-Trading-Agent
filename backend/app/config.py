"""Application settings, loaded from environment variables and the root `.env` file."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # `../.env` is the root file shared with Docker Compose. Real env vars take precedence.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
