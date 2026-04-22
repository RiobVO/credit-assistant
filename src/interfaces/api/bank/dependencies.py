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
from config.settings import get_settings
from infrastructure.auth.jwt_service import InvalidTokenError, JwtService
from infrastructure.auth.password_hasher import PasswordHasher
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


SessionDep = Annotated[AsyncSession, Depends(get_session)]
HasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
JwtServiceDep = Annotated[JwtService, Depends(get_jwt_service)]


async def get_analyst_repo(session: SessionDep) -> SqlAlchemyAnalystRepository:
    return SqlAlchemyAnalystRepository(session)


async def get_audit_log_repo(session: SessionDep) -> SqlAlchemyAuditLogRepository:
    return SqlAlchemyAuditLogRepository(session)


AnalystRepoDep = Annotated[SqlAlchemyAnalystRepository, Depends(get_analyst_repo)]
AuditLogRepoDep = Annotated[SqlAlchemyAuditLogRepository, Depends(get_audit_log_repo)]


async def get_authn_adapter(
    analyst_repo: AnalystRepoDep,
    hasher: HasherDep,
) -> SeededAuthnAdapter:
    return SeededAuthnAdapter(analyst_repo, hasher)


AuthnDep = Annotated[SeededAuthnAdapter, Depends(get_authn_adapter)]


_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="unauthorized",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_analyst(
    authorization: Annotated[str | None, Header()] = None,
    jwt_service: JwtService = Depends(get_jwt_service),  # noqa: B008
    analyst_repo: SqlAlchemyAnalystRepository = Depends(get_analyst_repo),  # noqa: B008
) -> AnalystIdentity:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _UNAUTHORIZED

    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt_service.decode(token, expected_type="access")
    except InvalidTokenError as exc:
        raise _UNAUTHORIZED from exc

    identity = await analyst_repo.get_by_id(claims.analyst_id)
    if identity is None or not identity.is_active:
        raise _UNAUTHORIZED
    return identity


CurrentAnalyst = Annotated[AnalystIdentity, Depends(get_current_analyst)]
