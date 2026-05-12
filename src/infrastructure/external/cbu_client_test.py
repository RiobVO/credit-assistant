"""Тесты cbu_client — HTTP-клиент CBU API."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest

from infrastructure.external.cbu_client import CbuFetchError, fetch_usd_rate


def _mock_transport(handler: Any) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


@pytest.fixture
def _patch_client(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Подменяем httpx.AsyncClient на версию с MockTransport-handler из теста."""

    def _factory(handler: Any) -> None:
        original = httpx.AsyncClient

        def _patched(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
            kwargs["transport"] = httpx.MockTransport(handler)
            return original(*args, **kwargs)

        monkeypatch.setattr("infrastructure.external.cbu_client.httpx.AsyncClient", _patched)

    return _factory


def _good_payload() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "Code": "840",
            "Ccy": "USD",
            "Nominal": "1",
            "Rate": "12575.36",
            "Diff": "-12.04",
            "Date": "15.05.2026",
        }
    ]


async def test_fetch_success_returns_parsed_rate(_patch_client: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_good_payload())

    _patch_client(handler)
    rate = await fetch_usd_rate()
    assert rate.rate == Decimal("12575.36")
    assert rate.asof == date(2026, 5, 15)
    assert rate.nominal == 1
    assert rate.raw["Code"] == "840"


async def test_non_200_raises_cbu_fetch_error(_patch_client: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    _patch_client(handler)
    with pytest.raises(CbuFetchError, match=r"all .* CBU fetch attempts failed"):
        await fetch_usd_rate()


async def test_empty_array_raises(_patch_client: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    _patch_client(handler)
    with pytest.raises(CbuFetchError):
        await fetch_usd_rate()


async def test_malformed_date_raises(_patch_client: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        bad = _good_payload()
        bad[0]["Date"] = "2026-05-15"  # ISO, not DD.MM.YYYY
        return httpx.Response(200, json=bad)

    _patch_client(handler)
    with pytest.raises(CbuFetchError, match="invalid Date"):
        await fetch_usd_rate()


async def test_non_array_payload_raises(_patch_client: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"not": "an array"})

    _patch_client(handler)
    with pytest.raises(CbuFetchError, match="expected JSON array"):
        await fetch_usd_rate()


async def test_retry_recovers_on_second_attempt(
    _patch_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ускоряем sleep чтобы тест не висел секундами на backoff.
    monkeypatch.setattr("infrastructure.external.cbu_client.asyncio.sleep", _no_sleep)
    calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        calls[0] += 1
        if calls[0] == 1:
            return httpx.Response(500)
        return httpx.Response(200, json=_good_payload())

    _patch_client(handler)
    rate = await fetch_usd_rate()
    assert calls[0] == 2
    assert rate.rate == Decimal("12575.36")


async def _no_sleep(_seconds: float) -> None:
    return None
