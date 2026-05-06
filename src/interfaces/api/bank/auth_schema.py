"""Pydantic-схемы для bank/auth endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # Email-формат намеренно не валидируем: при невалидном email lookup в БД
    # вернёт None → login_failed, что эквивалентно неверным credentials и не
    # утекает enumeration через 422 vs 401.
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class AnalystResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    # Phase 5 Settings: эти поля рендерятся в /settings → Профиль.
    # `created_at` — «В системе с».
    # `password_changed_at` — «Пароль свежий N дней назад».
    # `mfa_enabled` — chip «✓ 2FA активна» (см. TODO[CA-DS10] про real enrollment).
    created_at: datetime
    password_changed_at: datetime
    mfa_enabled: bool


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    analyst: AnalystResponse


class MfaRequiredResponse(BaseModel):
    """Phase 5.B: возвращается из /login если у user real-TOTP enrollment.
    Frontend переключается на step-2 «введите код»; пользователь не получает
    access/refresh пока не пройдёт /mfa/challenge."""

    requires_mfa: bool = True
    challenge_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
