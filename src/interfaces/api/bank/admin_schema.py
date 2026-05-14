"""Pydantic-схемы для bank/admin endpoints (CA-DS13)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdminResetMfaRequest(BaseModel):
    """POST /api/bank/admin/analysts/reset-mfa — senior сбрасывает 2FA коллеге.

    Email вместо UUID — UX-критерий: senior помнит коллегу по email
    (`ivanov@bank.uz`), а не по uuid. Backend сам ищет identity.
    """

    email: str = Field(min_length=3, max_length=255)
