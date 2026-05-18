"""POST /api/bank/auth/mfa/* — TOTP enrollment + challenge + disable.

Phase 5.B endpoints — real RFC 6238 TOTP enrollment-flow.

* ``/enroll/start``  — auth required. Возвращает новый base32 secret +
  provisioning_uri. Перетирает существующий secret, если был — re-enrollment.
* ``/enroll/verify`` — auth required. Принимает первый TOTP-code из app,
  verify по сохранённому secret. При успехе: ставит mfa_enrolled_at = now(),
  генерит 10 backup-codes (plain → user видит один раз, hashed → БД).
* ``/challenge``     — без auth, но требует short-lived ``mfa_challenge_token``
  (5 мин, выдаётся /login если у user mfa_secret IS NOT NULL). Verify TOTP
  или backup-code → выдаёт access+refresh.
* ``/disable``       — auth required. Требует current password + TOTP code
  для подтверждения. Очищает mfa_secret, mfa_enrolled_at, backup_codes.

Audit: enrollment / disable пишутся как ``mfa_enrolled`` / ``mfa_disabled``;
ошибки challenge — ``mfa_challenge_failed`` с masked-email.

TODO[CA-DS12]: ``mfa_secret`` сейчас plain в БД. Production должна шифровать
через банковский KMS/vault.
TODO[CA-DS13]: admin-reset endpoint для случая «потерял phone + backup
codes» — пока workaround через прямой SQL/seed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from infrastructure.auth.email_mask import mask_email
from infrastructure.auth.jwt_service import InvalidTokenError
from infrastructure.auth.totp_service import (
    consume_backup_code,
    generate_backup_codes,
    generate_enrollment,
    hash_backup_codes,
    verify_totp,
)
from interfaces.api.bank.auth_schema import AnalystResponse, LoginResponse
from interfaces.api.bank.dependencies import (
    AnalystRepoDep,
    AuditLogRepoDep,
    AuthnDep,
    CurrentAnalyst,
    HasherDep,
    JwtServiceDep,
)
from interfaces.api.bank.mfa_schema import (
    EnrollStartResponse,
    EnrollVerifyRequest,
    EnrollVerifyResponse,
    MfaChallengeRequest,
    MfaDisableRequest,
)

router = APIRouter(prefix="/api/bank/auth/mfa", tags=["bank-auth-mfa"])


@router.post("/enroll/start", response_model=EnrollStartResponse)
async def enroll_start(
    analyst: CurrentAnalyst,
    analyst_repo: AnalystRepoDep,
) -> EnrollStartResponse:
    """Генерирует новый TOTP secret и записывает в orm (не enrolled пока!).

    Re-enrollment: если у user уже есть secret — он перезаписывается. Это ОК:
    /enroll/verify требует свежий код от нового secret, так что сменить
    устройство = start + verify заново.
    """
    artifacts = generate_enrollment(analyst.email)
    orm = await analyst_repo.get_orm(analyst.id)
    if orm is None:
        raise HTTPException(status_code=404, detail="analyst_not_found")
    orm.mfa_secret = artifacts.secret
    # Пока не verify'нул — enrolled_at не ставим; mfa_enabled в API будет True
    # сразу (computed-from-secret), но UI до verify покажет «в процессе».
    orm.mfa_enrolled_at = None
    orm.mfa_backup_codes_hash = None
    # commit произойдёт через session.commit() в FastAPI dependencies.
    return EnrollStartResponse(
        secret=artifacts.secret,
        provisioning_uri=artifacts.provisioning_uri,
    )


@router.post("/enroll/verify", response_model=EnrollVerifyResponse)
async def enroll_verify(
    payload: EnrollVerifyRequest,
    analyst: CurrentAnalyst,
    analyst_repo: AnalystRepoDep,
    audit_log: AuditLogRepoDep,
    hasher: HasherDep,
) -> EnrollVerifyResponse:
    orm = await analyst_repo.get_orm(analyst.id)
    if orm is None or orm.mfa_secret is None:
        raise HTTPException(status_code=400, detail="mfa_not_started")

    if not verify_totp(orm.mfa_secret, payload.code):
        raise HTTPException(status_code=400, detail="invalid_code")

    backup_plain = generate_backup_codes()
    orm.mfa_backup_codes_hash = hash_backup_codes(backup_plain, hasher)
    orm.mfa_enrolled_at = datetime.now(tz=UTC)
    # CA-DS16: stored bool `orm.mfa_enabled` удалён — enrolled_at теперь
    # единственный источник truth для computed mfa_enabled.

    await audit_log.record(event="mfa_enrolled", analyst_id=analyst.id)
    return EnrollVerifyResponse(backup_codes=backup_plain)


@router.post("/challenge", response_model=LoginResponse)
async def challenge(
    payload: MfaChallengeRequest,
    jwt_service: JwtServiceDep,
    analyst_repo: AnalystRepoDep,
    audit_log: AuditLogRepoDep,
    hasher: HasherDep,
) -> LoginResponse:
    try:
        claims = jwt_service.decode(payload.challenge_token, expected_type="mfa_challenge")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="invalid_challenge_token") from exc

    orm = await analyst_repo.get_orm(claims.analyst_id)
    # Half-enrolled (secret есть, но enrolled_at NULL) — НЕ принимаем challenge:
    # такой user не должен был получить challenge_token изначально (login смотрит
    # на computed mfa_enabled = enrolled_at IS NOT NULL). Защита на случай если
    # БД был мутирован в обход (race / прямой SQL).
    if (
        orm is None
        or not orm.is_active
        or orm.mfa_secret is None
        or orm.mfa_enrolled_at is None
    ):
        raise HTTPException(status_code=401, detail="invalid_challenge_token")

    code_ok = False
    if payload.use_backup_code:
        if orm.mfa_backup_codes_hash:
            remaining = consume_backup_code(
                list(orm.mfa_backup_codes_hash), payload.code, hasher
            )
            if remaining is not None:
                orm.mfa_backup_codes_hash = remaining
                code_ok = True
    else:
        code_ok = verify_totp(orm.mfa_secret, payload.code)

    if not code_ok:
        await audit_log.record(
            event="mfa_challenge_failed",
            payload={"email": mask_email(orm.email)},
        )
        raise HTTPException(status_code=401, detail="invalid_code")

    identity = await analyst_repo.get_by_id(claims.analyst_id)
    if identity is None:
        raise HTTPException(status_code=401, detail="invalid_challenge_token")

    access = jwt_service.issue_access(identity.id)
    refresh = jwt_service.issue_refresh(identity.id)
    await audit_log.record(event="login", analyst_id=identity.id)
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        analyst=AnalystResponse(
            id=identity.id,
            email=identity.email,
            full_name=identity.full_name,
            role=identity.role,
            created_at=identity.created_at,
            password_changed_at=identity.password_changed_at,
            mfa_enabled=identity.mfa_enabled,
        ),
    )


@router.post("/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable(
    payload: MfaDisableRequest,
    analyst: CurrentAnalyst,
    analyst_repo: AnalystRepoDep,
    audit_log: AuditLogRepoDep,
    authn: AuthnDep,
) -> None:
    """Отключение требует **пароль + TOTP-код** одновременно — повышает уверенность
    что disable инициирует именно владелец, а не злоумышленник с украденным
    cookie/токеном."""
    auth_result = await authn.authenticate(analyst.email, payload.password)
    if auth_result is None:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    orm = await analyst_repo.get_orm(analyst.id)
    # Disable доступен только полностью enrolled-пользователям (verify был
    # успешен → mfa_enrolled_at != NULL). Half-enrolled state UI не показывает
    # «Отключить», но защита здесь дублирует invariant.
    if orm is None or orm.mfa_secret is None or orm.mfa_enrolled_at is None:
        raise HTTPException(status_code=400, detail="mfa_not_enabled")

    if not verify_totp(orm.mfa_secret, payload.code):
        raise HTTPException(status_code=401, detail="invalid_code")

    orm.mfa_secret = None
    orm.mfa_enrolled_at = None
    orm.mfa_backup_codes_hash = None
    # CA-DS16: stored bool удалён.
    await audit_log.record(event="mfa_disabled", analyst_id=analyst.id)
