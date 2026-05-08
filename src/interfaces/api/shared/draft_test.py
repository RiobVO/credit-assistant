"""Integration-тесты POST/PUT/GET /api/manual-input/draft.

In-memory dummy DraftRepo сохраняет state в словаре — проверяем поведение
endpoint'ов (404, последовательность create→update→get) без поднятой БД.
TTL-логика (истечение по времени) проверится в 2.5.7 testcontainers.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from interfaces.api.app import create_app
from interfaces.api.shared.dossier_storage import DossierStorage, get_dossier_storage


class _StatefulDraftRepo:
    """In-memory CRUD: сохраняет payload по UUID; expired не моделируем."""

    def __init__(self) -> None:
        self._store: dict[UUID, dict[str, Any]] = {}

    async def create(self, payload: dict[str, Any]) -> UUID:
        new_id = uuid4()
        self._store[new_id] = dict(payload)
        return new_id

    async def update(self, draft_id: UUID, payload: dict[str, Any]) -> bool:
        if draft_id not in self._store:
            return False
        self._store[draft_id] = dict(payload)
        return True

    async def get(self, draft_id: UUID) -> dict[str, Any] | None:
        stored = self._store.get(draft_id)
        return dict(stored) if stored is not None else None

    async def purge_expired(self) -> int:
        return 0


class _NoopRepo:
    """Заглушка для borrower/snapshot/dossier — draft-тесты их не дёргают."""

    async def upsert(self, *_: Any, **__: Any) -> UUID:
        return uuid4()

    async def save(self, *_: Any, **__: Any) -> UUID:
        return uuid4()

    async def get_by_id(self, *_: Any, **__: Any) -> None:
        return None

    async def get_by_inn(self, *_: Any, **__: Any) -> None:
        return None


@pytest.fixture
def client() -> Iterator[TestClient]:
    draft_repo = _StatefulDraftRepo()
    noop = _NoopRepo()
    storage = DossierStorage(borrower=noop, snapshot=noop, dossier=noop, draft=draft_repo)
    app = create_app()
    app.dependency_overrides[get_dossier_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


ENDPOINT = "/api/manual-input/draft"


def _payload(name: str = "ООО Test") -> dict[str, Any]:
    return {"step1": {"inn": "123456789", "name": name}}


class TestCreateDraft:
    def test_create_returns_201_with_id_and_expiry(self, client: TestClient) -> None:
        r = client.post(ENDPOINT, json={"payload": _payload()})
        assert r.status_code == 201, r.text
        body = r.json()
        # UUID валидный — конструктор не должен бросить
        UUID(body["draft_id"])
        assert body["expires_at"]

    def test_payload_is_required(self, client: TestClient) -> None:
        r = client.post(ENDPOINT, json={})
        assert r.status_code == 422


class TestGetDraft:
    def test_get_returns_payload_after_create(self, client: TestClient) -> None:
        created = client.post(ENDPOINT, json={"payload": _payload("ООО A")})
        draft_id = created.json()["draft_id"]
        r = client.get(f"{ENDPOINT}/{draft_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["draft_id"] == draft_id
        assert body["payload"] == _payload("ООО A")

    def test_get_unknown_id_returns_404(self, client: TestClient) -> None:
        r = client.get(f"{ENDPOINT}/{uuid4()}")
        assert r.status_code == 404

    def test_get_invalid_uuid_returns_422(self, client: TestClient) -> None:
        r = client.get(f"{ENDPOINT}/not-a-uuid")
        assert r.status_code == 422


class TestUpdateDraft:
    def test_update_replaces_payload(self, client: TestClient) -> None:
        created = client.post(ENDPOINT, json={"payload": _payload("v1")})
        draft_id = created.json()["draft_id"]
        upd = client.put(f"{ENDPOINT}/{draft_id}", json={"payload": _payload("v2")})
        assert upd.status_code == 200
        got = client.get(f"{ENDPOINT}/{draft_id}")
        assert got.json()["payload"] == _payload("v2")

    def test_update_unknown_id_returns_404(self, client: TestClient) -> None:
        r = client.put(f"{ENDPOINT}/{uuid4()}", json={"payload": _payload()})
        assert r.status_code == 404
