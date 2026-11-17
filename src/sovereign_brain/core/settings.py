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
    # Review loop (Lab 24): how often a draft may be sent back for correction
    max_revisions: int = 2
    # Tool errors (Lab 43): how many failed tool calls one question may have before giving up
    max_tool_retries: int = 2
    # Who chooses the research track (Lab 30): the model, or the word rules only
    research_router: Literal["rules", "model"] = "model"

    # Conversation memory (Labs 31-33): where thread checkpoints are kept
    checkpoint_store: Literal["memory", "sqlite", "postgres"] = "memory"
    checkpoint_sqlite_path: str = "data/checkpoints.sqlite"
    checkpoint_pool_size: int = 10  # PostgreSQL connections for checkpoints (Lab 33)
    # Thread expiry (Lab 34): unused threads are removed after this time (default 7 days)
    thread_ttl_minutes: int = 10080
    cleanup_interval_minutes: int = 60
    # Semantic memory (Lab 38): answers stored by meaning in Qdrant, across all threads
    semantic_memory: bool = True
    qdrant_url: str = "http://localhost:6333"
    memory_collection: str = "research_memory"
    embedding_model: str = "nomic-embed-text:v1.5"
    embedding_dimensions: int = 768  # nomic-embed-text returns 768 numbers per text
    memory_min_score: float = 0.6
    # Context window (Lab 40): older messages of a thread the model reads, at most
    history_limit: int = 20
    # MCP servers the API starts at start-up (Lab 44); an empty list switches MCP off
    mcp_servers: list[str] = ["desk", "notes", "market"]
    # Internal market-data API (Lab 46): only the market MCP server talks to it
    market_api_url: str = "http://localhost:8100"
    market_api_token: SecretStr = SecretStr("local-market-token-change-me")

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
