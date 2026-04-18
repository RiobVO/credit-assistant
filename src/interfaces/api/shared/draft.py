"""POST/PUT/GET /api/manual-input/draft — черновики формы.

Auth по знанию UUID — owner-поля нет (см. ADR 0005, появится в Phase 4).
TTL = `Settings.draft_ttl_days` (30 по умолчанию). PUT продлевает,
GET — read-only (TTL не трогает). Истёкший draft возвращается как 404.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException

from config.settings import get_settings
from interfaces.api.shared.dossier_storage import StorageDep
from interfaces.api.shared.draft_schema import (
    DraftCreatedResponse,
    DraftPayloadInput,
    DraftResponse,
    DraftUpdatedResponse,
)

router = APIRouter(prefix="/api/manual-input/draft", tags=["draft"])


def _next_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=get_settings().draft_ttl_days)


@router.post("", response_model=DraftCreatedResponse, status_code=201)
async def create_draft(
    body: DraftPayloadInput,
    storage: StorageDep,
) -> DraftCreatedResponse:
    draft_id = await storage.draft.create(body.payload)
    return DraftCreatedResponse(draft_id=draft_id, expires_at=_next_expiry())


@router.put("/{draft_id}", response_model=DraftUpdatedResponse)
async def update_draft(
    draft_id: UUID,
    body: DraftPayloadInput,
    storage: StorageDep,
) -> DraftUpdatedResponse:
    found = await storage.draft.update(draft_id, body.payload)
    if not found:
        raise HTTPException(status_code=404, detail="Draft not found or expired")
    return DraftUpdatedResponse(draft_id=draft_id, expires_at=_next_expiry())


@router.get("/{draft_id}", response_model=DraftResponse)
async def get_draft(draft_id: UUID, storage: StorageDep) -> DraftResponse:
    payload = await storage.draft.get(draft_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Draft not found or expired")
    return DraftResponse(draft_id=draft_id, payload=payload)
