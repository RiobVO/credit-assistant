"""AuthenticateAnalyst: login → tokens, с записью в audit_log.

Use case оркеструет AuthnPort + JwtService + AuditLogRepository. Outcome —
дискриминированный union: ``AuthenticationSuccess`` либо ``AuthenticationFailure``.
Endpoint мапит failure → 401, success → 200 с токенами.
"""

from __future__ import annotations

from dataclasses import dataclass

from application.dto.analyst_identity import AnalystIdentity
from application.ports.authn_port import AuthnPort
from infrastructure.auth.jwt_service import JwtService
from infrastructure.persistence.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)


@dataclass(frozen=True, slots=True)
class AuthenticationSuccess:
    analyst: AnalystIdentity
    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class AuthenticationFailure:
    reason: str  # 'invalid_credentials' | 'inactive_account'


AuthenticationResult = AuthenticationSuccess | AuthenticationFailure


class AuthenticateAnalyst:
    def __init__(
        self,
        authn: AuthnPort,
        jwt_service: JwtService,
        audit_log: SqlAlchemyAuditLogRepository,
    ) -> None:
        self._authn = authn
        self._jwt = jwt_service
        self._audit = audit_log

    async def execute(
        self, email: str, password: str, *, ip: str | None = None
    ) -> AuthenticationResult:
        analyst = await self._authn.authenticate(email, password)
        if analyst is None:
            await self._audit.record(
                event="login_failed",
                payload={"email": email, "ip": ip} if ip else {"email": email},
            )
            return AuthenticationFailure(reason="invalid_credentials")

        access = self._jwt.issue_access(analyst.id)
        refresh = self._jwt.issue_refresh(analyst.id)
        await self._audit.record(
            event="login",
            analyst_id=analyst.id,
            payload={"ip": ip} if ip else {},
        )
        return AuthenticationSuccess(
            analyst=analyst,
            access_token=access,
            refresh_token=refresh,
        )
