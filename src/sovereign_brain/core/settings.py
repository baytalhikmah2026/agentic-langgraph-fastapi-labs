"""Application settings, read from environment variables that start with SB_."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SB_", env_file=".env", extra="ignore")

    app_name: str = "Sovereign Brain"
    environment: Literal["local", "test", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
