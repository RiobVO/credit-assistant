"""POST/GET /api/bank/auth/* — login / refresh / logout / me.

Контракт см. в design spec `docs/superpowers/specs/2026-05-11-phase-4-bank-mode-design.md`
секция 4. Cookie-обёртка (httpOnly) выполняется на стороне Next BFF, backend
возвращает чистый JSON с токенами.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Body, HTTPException, Request, Response, status

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
    LogoutRequest,
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
    RefreshDenylistDep,
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
    denylist: RefreshDenylistDep,
) -> RefreshResponse:
    """T1.2 (CA-019): refresh rotation + denylist старого jti.

    Поток:
    1. Decode refresh → claims (signature + typ check).
    2. is_denied(jti) — fast-path: уже rotated/logged-out → 401 token_reused.
    3. analyst.is_active в БД — не доверяем токену слепо.
    4. deny(old_jti, expires_at=old_exp) с NX. NX=False → параллельный refresh
       уже отыграл, это reuse-attack/race → 401 token_reused.
    5. Issue новые access + refresh, возвращаем обе.

    Fail-mode при недоступности Redis: redis.ConnectionError всплывает наверх
    как 500 — fail closed, чтобы compromised tokens не проскочили.
    """
    try:
        claims = jwt_service.decode(payload.refresh_token, expected_type="refresh")
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
        ) from exc

    if await denylist.is_denied(claims.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_reused",
        )

    identity = await analyst_repo.get_by_id(claims.analyst_id)
    if identity is None or not identity.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
        )

    denied = await denylist.deny(claims.jti, expires_at=claims.expires_at)
    if not denied:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_reused",
        )

    access = jwt_service.issue_access(identity.id)
    new_refresh = jwt_service.issue_refresh(identity.id)
    return RefreshResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    analyst: CurrentAnalyst,
    audit_log: AuditLogRepoDep,
    jwt_service: JwtServiceDep,
    denylist: RefreshDenylistDep,
    payload: LogoutRequest | None = Body(default=None),  # noqa: B008 — FastAPI DI pattern
) -> Response:
    """T1.2 (CA-019): logout denylist'ит активный refresh из body (best-effort).

    Невалидный/чужой refresh — silently ignore: logout уже подтверждён
    access-токеном. BFF /logout читает ca_refresh cookie и прокидывает сюда;
    старые клиенты без поля refresh_token продолжают работать (denylist
    skip, токен истечёт натурально через TTL).
    """
    if payload is not None and payload.refresh_token:
        try:
            claims = jwt_service.decode(
                payload.refresh_token, expected_type="refresh"
            )
            # Защита от cross-account abuse: denylist'им только если refresh
            # принадлежит этому же аналитику (access уже подтвердил identity).
            if claims.analyst_id == analyst.id:
                await denylist.deny(claims.jti, expires_at=claims.expires_at)
        except InvalidTokenError:
            # Broken/expired refresh — натурального exp достаточно.
            pass

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

    # T1.5 (ADR-0019): LDAP-provisioned users держат password_hash=NULL —
    # пароль владеется LDAP-server'ом, change через bank-API запрещён.
    # UI обязан скрывать password-change для LDAP-users (флаг приходит
    # с /me?); защитный гвард на API-уровне на всякий случай.
    if orm.password_hash is None:
        raise HTTPException(status_code=400, detail="ldap_user_cannot_change_password")

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
