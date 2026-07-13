from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="FVQL_",
        extra="ignore",
    )

    app_name: str = "Factory Vision Quality Loop"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./factory_vision.db"
    log_level: str = "INFO"
    log_file: Path = Path("logs/backend.jsonl")
    readiness_timeout_seconds: float = Field(default=2.0, gt=0)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
