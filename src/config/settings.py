"""Настройки приложения. Источник — переменные окружения и `.env`."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "dev", "staging", "prod"]


class Settings(BaseSettings):
    """Глобальные настройки. Иммутабельны на время процесса (см. `get_settings`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: AppEnv = "local"
    log_level: str = "INFO"

    # Postgres connection. Async URL with asyncpg driver — используется и приложением,
    # и Alembic (через async engine + run_sync в env.py).
    database_url: str = "postgresql+asyncpg://credit:credit@localhost:5433/credit_assistant"

    # Draft form retention. По умолчанию 30 дней; в проде регулируется через .env.
    draft_ttl_days: int = 30

    # CORS: либо JSON-массив в .env, либо comma-separated — поддерживаем оба
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
    )

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Возвращает singleton настроек. Пересоздание — через `get_settings.cache_clear()`."""
    return Settings()
