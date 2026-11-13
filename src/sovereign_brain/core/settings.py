"""Application settings, read from environment variables that start with SB_."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SB_", env_file=".env", extra="ignore")

    app_name: str = "Sovereign Brain"
    environment: Literal["local", "test", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # The AI model (Lab 6) and the OpenAI-compatible path (Lab 7)
    llm_provider: Literal["ollama", "openai"] = "ollama"
    llm_model: str = "qwen3:4b"
    llm_temperature: float = 0.0
    ollama_base_url: str = "http://localhost:11434"
    openai_base_url: str = "http://localhost:11434/v1"
    openai_api_key: SecretStr = SecretStr("not-needed")

    # Agent safety (Lab 13): the most steps one graph run may take
    graph_recursion_limit: int = 25

    # Database (Lab 12)
    database_url: str = "postgresql+psycopg://sb:sb_local_pw@localhost:5432/sovereign_brain"

    # Sign-in tokens (Lab 16): set SB_JWT_SECRET in .env to your own long random value
    jwt_secret: SecretStr = SecretStr("local-development-only-secret-change-me-0123")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30

    # Rate limits for model calls (Lab 17), per signed-in analyst; Redis storage from Lab 18
    model_rate_limit: str = "5/minute"
    rate_limit_storage_uri: str = "memory://"

    # Redis cache for research answers (Lab 18)
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()
