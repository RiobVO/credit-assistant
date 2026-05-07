"""Настройки приложения. Источник — переменные окружения и `.env`."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "dev", "staging", "prod"]
AppMode = Literal["bank", "accountant"]


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

    # Phase 4: режим инсталляции. Одна установка = один режим (PROJECT_BRIEF Section 2).
    # На bank install accountant-роуты не подключаются и наоборот (реализуется в 4.D).
    app_mode: AppMode = "accountant"

    # Postgres connection. Async URL with asyncpg driver — используется и приложением,
    # и Alembic (через async engine + run_sync в env.py).
    database_url: str = "postgresql+asyncpg://credit:credit@localhost:5433/credit_assistant"

    # Draft form retention. По умолчанию 30 дней; в проде регулируется через .env.
    draft_ttl_days: int = 30

    # CA-DS9: background-task для system_uptime_day. Default выключен — это
    # безопасное умолчание для unit/integration тестов и host-run dev (где у
    # бэкенда нет реальной БД под рукой). В docker-compose сервисе ``api``
    # ставим ``UPTIME_COLLECTOR_ENABLED=true`` явно. См.
    # infrastructure/jobs/uptime_collector.py.
    uptime_collector_enabled: bool = False
    uptime_collector_interval_seconds: float = 60.0

    # Auth (Phase 4.B). Дефолт намеренно небезопасный — на dev/local работает,
    # в проде обязан быть переопределён через .env (валидация в проде — задача
    # деплоя, не приложения). Для тестов hardcoded достаточен.
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7

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
