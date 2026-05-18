"""FastAPI DI для Bank Mode: auth-сервисы, AuthnAdapter, current analyst.

Singletons:
* ``get_password_hasher`` — bcrypt context, ленивый stateless.
* ``get_jwt_service`` — из Settings, ленивый stateless.

Per-request:
* ``get_authn_adapter`` — AnalystRepository + PasswordHasher на текущей сессии.
* ``get_audit_log_repo`` — AuditLogRepository на текущей сессии.
* ``get_analyst_repo`` — AnalystRepository на текущей сессии.
* ``get_current_analyst`` — декодирует access JWT из ``Authorization: Bearer``,
  поднимает identity из БД, проверяет ``is_active``. 401 на любую ошибку.
"""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.analyst_identity import AnalystIdentity
from application.ports.authn_port import AuthnPort
from application.ports.refresh_token_denylist_port import RefreshTokenDenylistPort
from config.settings import get_settings
from infrastructure.auth.break_glass_authn_adapter import (
    BreakGlassAuthnAdapter,
    parse_break_glass_emails,
)
from infrastructure.auth.jwt_service import InvalidTokenError, JwtService
from infrastructure.auth.ldap3_client import Ldap3Client
from infrastructure.auth.ldap_authn_adapter import LdapAuthnAdapter, LdapSettings
from infrastructure.auth.null_refresh_token_denylist import NullRefreshTokenDenylist
from infrastructure.auth.password_hasher import PasswordHasher
from infrastructure.auth.redis_refresh_token_denylist import RedisRefreshTokenDenylist
from infrastructure.auth.seeded_authn_adapter import SeededAuthnAdapter
from infrastructure.persistence.database import get_session
from infrastructure.persistence.repositories.analyst_repository import (
    SqlAlchemyAnalystRepository,
)
from infrastructure.persistence.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)


@lru_cache(maxsize=1)
def get_password_hasher() -> PasswordHasher:
    return PasswordHasher(rounds=12)


@lru_cache(maxsize=1)
def get_jwt_service() -> JwtService:
    settings = get_settings()
    return JwtService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_ttl=timedelta(minutes=settings.jwt_access_ttl_minutes),
        refresh_ttl=timedelta(days=settings.jwt_refresh_ttl_days),
    )


@lru_cache(maxsize=1)
def get_refresh_token_denylist() -> RefreshTokenDenylistPort:
    """T1.2 (CA-019): refresh-token denylist для rotation на /refresh и /logout.

    REDIS_URL=None → NullDenylist (stateless 7-day fallback для dev без compose).
    REDIS_URL задан → Redis adapter поверх singleton-client. При недоступности
    Redis caller (auth.py /refresh) ловит ConnectionError и отдаёт 503 — fail
    closed, чтобы compromised tokens не проскочили.

    См. ADR-0016 «Refresh-token rotation».
    """
    settings = get_settings()
    if not settings.redis_url:
        return NullRefreshTokenDenylist()
    from redis.asyncio import Redis

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    return RedisRefreshTokenDenylist(client)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
HasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
JwtServiceDep = Annotated[JwtService, Depends(get_jwt_service)]
RefreshDenylistDep = Annotated[
    RefreshTokenDenylistPort, Depends(get_refresh_token_denylist)
]


async def get_analyst_repo(session: SessionDep) -> SqlAlchemyAnalystRepository:
    return SqlAlchemyAnalystRepository(session)


async def get_audit_log_repo(session: SessionDep) -> SqlAlchemyAuditLogRepository:
    # T1.4 (ADR-0018): brand_id берётся из Settings, single source of truth.
    return SqlAlchemyAuditLogRepository(session, brand_id=get_settings().brand_id)


AnalystRepoDep = Annotated[SqlAlchemyAnalystRepository, Depends(get_analyst_repo)]
AuditLogRepoDep = Annotated[SqlAlchemyAuditLogRepository, Depends(get_audit_log_repo)]


@lru_cache(maxsize=1)
def _get_ldap_settings() -> LdapSettings:
    """T1.5 (ADR-0019): резолвит LdapSettings из Settings + cache singleton.

    Зовётся только когда ``authn_mode=ldap``. Все обязательные LDAP-поля
    должны быть заданы — иначе ``_validate_runtime_config`` свалит старт.
    """
    settings = get_settings()
    if (
        settings.ldap_uri is None
        or settings.ldap_base_dn is None
        or settings.ldap_bind_dn is None
        or settings.ldap_bind_password is None
        or settings.ldap_role_analyst_group is None
        or settings.ldap_role_senior_analyst_group is None
    ):
        raise RuntimeError(
            "LDAP-настройки неполные при AUTHN_MODE=ldap "
            "(см. ADR-0019, docs/operations/ldap-setup.md). "
            "Требуются: LDAP_URI, LDAP_BASE_DN, LDAP_BIND_DN, "
            "LDAP_BIND_PASSWORD, LDAP_ROLE_ANALYST_GROUP, "
            "LDAP_ROLE_SENIOR_ANALYST_GROUP."
        )
    return LdapSettings(
        uri=settings.ldap_uri,
        base_dn=settings.ldap_base_dn,
        bind_dn=settings.ldap_bind_dn,
        bind_password=settings.ldap_bind_password,
        user_search_filter=settings.ldap_user_search_filter,
        role_analyst_group=settings.ldap_role_analyst_group,
        role_senior_analyst_group=settings.ldap_role_senior_analyst_group,
    )


@lru_cache(maxsize=1)
def _get_ldap_client() -> Ldap3Client:
    """Singleton Ldap3Client — Server-объект внутри переиспользуется
    между запросами (DNS / TLS cache)."""
    return Ldap3Client(_get_ldap_settings())


async def get_authn_adapter(
    analyst_repo: AnalystRepoDep,
    hasher: HasherDep,
) -> AuthnPort:
    """T1.5 (ADR-0019): switch по ``authn_mode``.

    * ``seeded`` (default, dev/staging): SeededAuthnAdapter напрямую.
    * ``ldap`` (production bank): BreakGlassAuthnAdapter — email в whitelist
      → SeededAdapter; иначе → LdapAuthnAdapter.
    """
    settings = get_settings()
    seeded = SeededAuthnAdapter(analyst_repo, hasher)
    if settings.authn_mode == "seeded":
        return seeded

    ldap = LdapAuthnAdapter(
        client=_get_ldap_client(),
        settings=_get_ldap_settings(),
        analyst_upsert=analyst_repo,
    )
    return BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=parse_break_glass_emails(
            settings.admin_break_glass_emails
        ),
    )


AuthnDep = Annotated[AuthnPort, Depends(get_authn_adapter)]


_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="unauthorized",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_optional_current_analyst(
    authorization: Annotated[str | None, Header()] = None,
    jwt_service: JwtService = Depends(get_jwt_service),  # noqa: B008
    analyst_repo: SqlAlchemyAnalystRepository = Depends(get_analyst_repo),  # noqa: B008
) -> AnalystIdentity | None:
    """Best-effort извлечение identity. ``None`` если токена нет / невалиден /
    аналитик неактивен. Используется shared-endpoints в bank mode для audit:
    handler не падает на отсутствии токена (mode-gating на router-уровне сам
    отвергнёт unauth), а просто пропускает audit-запись.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt_service.decode(token, expected_type="access")
    except InvalidTokenError:
        return None

    identity = await analyst_repo.get_by_id(claims.analyst_id)
    if identity is None or not identity.is_active:
        return None
    return identity


async def get_current_analyst(
    optional: Annotated[AnalystIdentity | None, Depends(get_optional_current_analyst)],
) -> AnalystIdentity:
    """Строгий вариант: 401 если identity не получена. Используется на router-
    уровне в bank mode и явно в bank-endpoints (search/history/auth.me)."""
    if optional is None:
        raise _UNAUTHORIZED
    return optional


CurrentAnalyst = Annotated[AnalystIdentity, Depends(get_current_analyst)]
OptionalAnalyst = Annotated[AnalystIdentity | None, Depends(get_optional_current_analyst)]
