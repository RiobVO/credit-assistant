"""POST/GET /api/bank/auth/* — login / refresh / logout / me.

Контракт см. в design spec `docs/superpowers/specs/2026-05-11-phase-4-bank-mode-design.md`
секция 4. Cookie-обёртка (httpOnly) выполняется на стороне Next BFF, backend
возвращает чистый JSON с токенами.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from application.use_cases.authenticate_analyst import (
    AuthenticateAnalyst,
    AuthenticationFailure,
)
from infrastructure.auth.jwt_service import InvalidTokenError
from interfaces.api.bank.auth_schema import (
    AnalystResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
)
from interfaces.api.bank.dependencies import (
    AnalystRepoDep,
    AuditLogRepoDep,
    AuthnDep,
    CurrentAnalyst,
    JwtServiceDep,
)

router = APIRouter(prefix="/api/bank/auth", tags=["bank-auth"])


def _client_ip(request: Request) -> str | None:
    """Возвращает IP клиента. За reverse proxy банка должен прийти X-Forwarded-For,
    но в POC доверяем request.client.host напрямую.
    """
    if request.client is None:
        return None
    return request.client.host


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    authn: AuthnDep,
    jwt_service: JwtServiceDep,
    audit_log: AuditLogRepoDep,
) -> LoginResponse:
    use_case = AuthenticateAnalyst(authn, jwt_service, audit_log)
    result = await use_case.execute(
        email=payload.email,
        password=payload.password,
        ip=_client_ip(request),
    )
    if isinstance(result, AuthenticationFailure):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )
    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        analyst=AnalystResponse(
            id=result.analyst.id,
            email=result.analyst.email,
            full_name=result.analyst.full_name,
            role=result.analyst.role,
        ),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest,
    jwt_service: JwtServiceDep,
    analyst_repo: AnalystRepoDep,
) -> RefreshResponse:
    try:
        claims = jwt_service.decode(payload.refresh_token, expected_type="refresh")
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
        ) from exc

    # Не доверяем токену слепо: проверяем, что analyst активен.
    identity = await analyst_repo.get_by_id(claims.analyst_id)
    if identity is None or not identity.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
        )

    access = jwt_service.issue_access(identity.id)
    return RefreshResponse(access_token=access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    analyst: CurrentAnalyst,
    audit_log: AuditLogRepoDep,
) -> Response:
    # JWT stateless: серверной инвалидации в v1 нет. Реальный logout — удаление
    # httpOnly cookie на стороне Next BFF. Здесь только аудит-запись.
    await audit_log.record(event="logout", analyst_id=analyst.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AnalystResponse)
async def me(analyst: CurrentAnalyst) -> AnalystResponse:
    return AnalystResponse(
        id=analyst.id,
        email=analyst.email,
        full_name=analyst.full_name,
        role=analyst.role,
    )
