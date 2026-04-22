"""Pydantic-схемы для bank/auth endpoints."""

from __future__ import annotations

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


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    analyst: AnalystResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
