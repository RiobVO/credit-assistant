"""POST/GET /api/bank/auth/* — login / refresh / logout / me.

Контракт см. в design spec `docs/superpowers/specs/2026-05-11-phase-4-bank-mode-design.md`
секция 4. Cookie-обёртка (httpOnly) выполняется на стороне Next BFF, backend
возвращает чистый JSON с токенами.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status

from application.use_cases.authenticate_analyst import (
    AuthenticateAnalyst,
    AuthenticationFailure,
)
from infrastructure.auth.jwt_service import InvalidTokenError
from interfaces.api.bank.auth_schema import (
    AnalystResponse,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MfaRequiredResponse,
    RefreshRequest,
    RefreshResponse,
)
from interfaces.api.bank.dependencies import (
    AnalystRepoDep,
    AuditLogRepoDep,
    AuthnDep,
    CurrentAnalyst,
    HasherDep,
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


@router.post(
    "/login",
    response_model=LoginResponse | MfaRequiredResponse,
    responses={401: {"description": "invalid_credentials"}},
)
async def login(
    payload: LoginRequest,
    request: Request,
    authn: AuthnDep,
    jwt_service: JwtServiceDep,
    audit_log: AuditLogRepoDep,
) -> LoginResponse | MfaRequiredResponse:
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
    # Phase 5.B: если у user real-TOTP enrollment — НЕ выдаём access/refresh.
    # Вместо этого короткий challenge_token (5 мин); frontend перенаправляет
    # на step-2 «введите код», итог через /mfa/challenge.
    if result.analyst.mfa_enabled:
        challenge_token = jwt_service.issue_mfa_challenge(result.analyst.id)
        return MfaRequiredResponse(challenge_token=challenge_token)

    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        analyst=AnalystResponse(
            id=result.analyst.id,
            email=result.analyst.email,
            full_name=result.analyst.full_name,
            role=result.analyst.role,
            created_at=result.analyst.created_at,
            password_changed_at=result.analyst.password_changed_at,
            mfa_enabled=result.analyst.mfa_enabled,
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


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"description": "password_unchanged"},
        401: {"description": "invalid_credentials"},
    },
)
async def change_password(
    payload: ChangePasswordRequest,
    analyst: CurrentAnalyst,
    authn: AuthnDep,
    analyst_repo: AnalystRepoDep,
    hasher: HasherDep,
    audit_log: AuditLogRepoDep,
) -> Response:
    """Авторизованная смена пароля.

    Pattern зеркальный `/mfa/disable`: re-auth по current через ``AuthnPort``,
    затем mutation на ORM-инстансе. Не делаем revoke сессий — JWT в v1
    stateless (TODO[CA-019]); access токен остаётся валидным до TTL.
    """
    identity = await authn.authenticate(analyst.email, payload.current_password)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials"
        )

    orm = await analyst_repo.get_orm(analyst.id)
    if orm is None:
        # CurrentAnalyst уже подтвердил identity, поэтому это defensive;
        # 404 здесь означал бы рассинхрон БД между двумя запросами.
        raise HTTPException(status_code=404, detail="analyst_not_found")

    # Запрет реюза текущего пароля: банковский compliance не любит «сменил на
    # тот же». Verify ДО hash() нового, чтобы не тратить bcrypt cost зря.
    if hasher.verify(payload.new_password, orm.password_hash):
        raise HTTPException(status_code=400, detail="password_unchanged")

    orm.password_hash = hasher.hash(payload.new_password)
    orm.password_changed_at = datetime.now(tz=UTC)
    await audit_log.record(event="password_changed", analyst_id=analyst.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AnalystResponse)
async def me(analyst: CurrentAnalyst) -> AnalystResponse:
    return AnalystResponse(
        id=analyst.id,
        email=analyst.email,
        full_name=analyst.full_name,
        role=analyst.role,
        created_at=analyst.created_at,
        password_changed_at=analyst.password_changed_at,
        mfa_enabled=analyst.mfa_enabled,
    )
