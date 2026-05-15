"""Настройки приложения. Источник — переменные окружения и `.env`."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "dev", "staging", "prod"]
AppMode = Literal["bank", "accountant"]
AuthnMode = Literal["seeded", "ldap"]


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

    # T1.2 (CA-019): Redis для refresh-token denylist. None → NullDenylist
    # (stateless 7-day fallback для dev без compose). Задан, но Redis недоступен
    # → fail closed на /refresh и /logout (см. ADR-0016).
    redis_url: str | None = None

    # T1.3 (CA-DS12 / ADR-0017): comma-separated Fernet keys для PII encryption
    # at rest. Первый ключ — primary (write), остальные — read fallback для
    # rotation. Каждый ключ = 32-byte url-safe base64. None в dev → NullPiiEncryptor
    # (passthrough). В staging/prod startup-assert требует хотя бы один ключ.
    # См. docs/operations/pii-key-rotation.md.
    pii_enc_keys: str | None = None

    # T1.4 (ADR-0018): идентификатор brand-tenant для текущего deployment.
    # Single-tenant per deployment — каждая инсталляция = один банк. Значение
    # должно соответствовать существующему `config/brands/<id>.json`; иначе
    # startup-assert в `create_app` поднимет `RuntimeError`. Также проставляется
    # в `audit_log.brand_id` для forensics-trail при misconfiguration.
    brand_id: str = "default"

    # T1.5 (ADR-0019): AuthnPort backend selector.
    # ``seeded`` — local bcrypt (dev/staging без LDAP).
    # ``ldap`` — LDAP bind+search (production). Break-glass email whitelist
    # см. ``admin_break_glass_emails`` ниже.
    authn_mode: AuthnMode = "seeded"

    # T1.5: LDAP connection params. Активируются только когда ``authn_mode=ldap``.
    # URI: ``ldap://`` (port 389) или ``ldaps://`` (TLS, port 636).
    # Base DN — корень поиска users. Bind DN/password — service account для
    # search-фазы (после search'а user-bind для verify password — отдельный bind).
    ldap_uri: str | None = None
    ldap_base_dn: str | None = None
    ldap_bind_dn: str | None = None
    ldap_bind_password: str | None = None
    # User search filter — `{email}` placeholder заменяется на запрашиваемый
    # email. Default для AD: ``(&(objectClass=user)(mail={email}))``.
    ldap_user_search_filter: str = "(&(objectClass=user)(mail={email}))"
    # Group DNs для role mapping. User member of senior_analyst_group → senior;
    # иначе если member analyst_group → analyst; иначе bind fail (no role).
    ldap_role_analyst_group: str | None = None
    ldap_role_senior_analyst_group: str | None = None

    # T1.5: Break-glass email whitelist. Comma-separated. Для этих email'ов
    # даже в ``authn_mode=ldap`` используется local SeededAuthnAdapter (bcrypt).
    # Use-case: recovery когда LDAP-инфра недоступна или operator заблокирован.
    # Список audit'ится в ``audit_log.payload.authn_source='break_glass'``.
    admin_break_glass_emails: str = ""

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
