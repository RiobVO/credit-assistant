"""Pydantic-схемы черновиков формы.

Payload намеренно без типизации — UI шлёт partial-данные по ходу заполнения,
строгая валидация применяется только на финальном `POST /api/manual-input`.
Draft — "сырое содержимое формы", не контракт. См. ADR 0005.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DraftPayloadInput(_StrictModel):
    payload: dict[str, Any]


class DraftCreatedResponse(_StrictModel):
    draft_id: UUID
    expires_at: datetime


class DraftUpdatedResponse(_StrictModel):
    draft_id: UUID
    expires_at: datetime


class DraftResponse(_StrictModel):
    draft_id: UUID
    payload: dict[str, Any]
