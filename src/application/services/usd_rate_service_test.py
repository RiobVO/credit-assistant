"""Тесты UsdRateService — fallback chain env → DB today → CBU → DB latest → JSON."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from application.dto.exchange_rate import UsdUzsRate
from application.services.usd_rate_service import UsdRateService
from infrastructure.catalog.exchange_rates import ExchangeRateError
from infrastructure.external.cbu_client import CbuFetchError, CbuRate


class FakeRepo:
    """Stub без зависимости от Postgres — для unit-уровня."""

    def __init__(
        self,
        *,
        today_row: UsdUzsRate | None = None,
        latest_row: UsdUzsRate | None = None,
    ) -> None:
        self.today_row = today_row
        self.latest_row = latest_row
        self.saved: list[UsdUzsRate] = []

    async def get_for_date(self, target: date) -> UsdUzsRate | None:
        return self.today_row

    async def get_latest(self) -> UsdUzsRate | None:
        return self.latest_row

    async def save(self, **kwargs: Any) -> None:
        self.saved.append(kwargs["rate"])


_TODAY = date(2026, 5, 17)


def _make_service(**repo_kwargs: Any) -> tuple[UsdRateService, FakeRepo]:
    repo = FakeRepo(**repo_kwargs)
    return UsdRateService(repo), repo  # type: ignore[arg-type]


async def test_env_override_highest_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USD_UZS_RATE", "13500")
    svc, _ = _make_service(today_row=UsdUzsRate(Decimal("99999"), _TODAY, "cbu_live"))
    rate = await svc.get_current_rate(today=_TODAY)
    assert rate.rate == Decimal("13500")
    assert rate.source == "env"


async def test_db_today_used_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USD_UZS_RATE", raising=False)
    cached = UsdUzsRate(Decimal("12575"), _TODAY, "cbu_live")
    svc, _ = _make_service(today_row=cached)
    rate = await svc.get_current_rate(today=_TODAY)
    assert rate == cached


async def test_cbu_live_fetched_and_saved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USD_UZS_RATE", raising=False)

    async def fake_fetch() -> CbuRate:
        return CbuRate(
            rate=Decimal("12575.36"),
            asof=_TODAY,
            nominal=1,
            raw={"Rate": "12575.36"},
        )

    monkeypatch.setattr(
        "application.services.usd_rate_service.fetch_usd_rate", fake_fetch
    )
    svc, repo = _make_service()
    rate = await svc.get_current_rate(today=_TODAY)
    assert rate.source == "cbu_live"
    assert rate.rate == Decimal("12575.36")
    assert len(repo.saved) == 1
    assert repo.saved[0].source == "cbu_live"


async def test_db_cached_fallback_when_cbu_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USD_UZS_RATE", raising=False)

    async def failing_fetch() -> CbuRate:
        raise CbuFetchError("CBU down")

    monkeypatch.setattr(
        "application.services.usd_rate_service.fetch_usd_rate", failing_fetch
    )
    latest = UsdUzsRate(Decimal("12500"), date(2026, 5, 10), "cbu_live")
    svc, _ = _make_service(latest_row=latest)
    rate = await svc.get_current_rate(today=_TODAY)
    assert rate.source == "db_cached"
    assert rate.rate == Decimal("12500")
    assert rate.asof == date(2026, 5, 10)


async def test_json_bootstrap_when_db_empty_and_cbu_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USD_UZS_RATE", raising=False)

    async def failing_fetch() -> CbuRate:
        raise CbuFetchError("CBU down")

    monkeypatch.setattr(
        "application.services.usd_rate_service.fetch_usd_rate", failing_fetch
    )
    svc, _ = _make_service()  # repo пустой
    rate = await svc.get_current_rate(today=_TODAY)
    # Cold-start fallback на config/exchange/rates.json
    assert rate.source == "manual"
    assert rate.rate > 0


async def test_all_sources_exhausted_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.delenv("USD_UZS_RATE", raising=False)

    async def failing_fetch() -> CbuRate:
        raise CbuFetchError("CBU down")

    monkeypatch.setattr(
        "application.services.usd_rate_service.fetch_usd_rate", failing_fetch
    )

    # Подменяем load_usd_uzs_rate чтобы он тоже падал — имитация corrupt JSON.
    def fake_load() -> UsdUzsRate:
        raise ExchangeRateError("JSON corrupt")

    monkeypatch.setattr(
        "application.services.usd_rate_service.load_usd_uzs_rate", fake_load
    )

    svc, _ = _make_service()
    with pytest.raises(ExchangeRateError, match="all USD rate sources exhausted"):
        await svc.get_current_rate(today=_TODAY)


async def test_env_invalid_value_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USD_UZS_RATE", "not-a-decimal")
    cached = UsdUzsRate(Decimal("12500"), _TODAY, "cbu_live")
    svc, _ = _make_service(today_row=cached)
    rate = await svc.get_current_rate(today=_TODAY)
    # Env невалидный → пропустить → fallback на DB today.
    assert rate == cached
