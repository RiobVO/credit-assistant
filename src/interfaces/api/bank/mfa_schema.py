"""Pydantic-схемы для MFA endpoints (Phase 5.B)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EnrollStartResponse(BaseModel):
    # Base32 secret — показывается в UI как fallback (если QR не сканируется).
    secret: str
    # otpauth://... URI; фронт генерит QR-код из него.
    provisioning_uri: str


class EnrollVerifyRequest(BaseModel):
    # 6 цифр из authenticator app.
    code: str = Field(min_length=6, max_length=8)


class EnrollVerifyResponse(BaseModel):
    # 10 plain backup-codes — show-once, после этого только хеши в БД.
    backup_codes: list[str]


class MfaChallengeRequest(BaseModel):
    challenge_token: str
    # 6 цифр TOTP или recovery-код (8 символов A-Z0-9).
    code: str = Field(min_length=6, max_length=16)
    use_backup_code: bool = False


class MfaDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)
    # Подтверждение TOTP — защита от accidental disable, даже если пароль украли.
    code: str = Field(min_length=6, max_length=8)
