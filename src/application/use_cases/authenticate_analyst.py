"""AuthenticateAnalyst: login → tokens, с записью в audit_log.

Use case оркеструет AuthnPort + JwtService + AuditLogRepository. Outcome —
дискриминированный union: ``AuthenticationSuccess`` либо ``AuthenticationFailure``.
Endpoint мапит failure → 401, success → 200 с токенами.
"""

from __future__ import annotations

from dataclasses import dataclass

from application.dto.analyst_identity import AnalystIdentity
from application.ports.authn_port import AuthnPort
from infrastructure.auth.email_mask import mask_email
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
        result = await self._authn.authenticate(email, password)
        if result is None:
            # T1.3 (ADR-0017): email маскируется в audit_log — full PII не утекает,
            # но partial identifier остаётся для compliance debugging.
            masked = mask_email(email)
            failed_payload: dict[str, object] = {"email": masked}
            if ip:
                failed_payload["ip"] = ip
            await self._audit.record(event="login_failed", payload=failed_payload)
            return AuthenticationFailure(reason="invalid_credentials")

        analyst = result.identity
        access = self._jwt.issue_access(analyst.id)
        refresh = self._jwt.issue_refresh(analyst.id)
        # T1.5 (ADR-0019): authn_source в payload — compliance видит источник
        # верификации (seeded/ldap/break_glass) для каждого login event.
        login_payload: dict[str, object] = {"authn_source": result.source}
        if ip:
            login_payload["ip"] = ip
        await self._audit.record(
            event="login",
            analyst_id=analyst.id,
            payload=login_payload,
        )
        return AuthenticationSuccess(
            analyst=analyst,
            access_token=access,
            refresh_token=refresh,
        )
