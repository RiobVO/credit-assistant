"""UsdRateService — fallback chain для GET /api/system/usd-rate (T0.2).

Priority order (highest → lowest):
1. **env USD_UZS_RATE** — ops override без redeploy. ``source="env"``.
2. **DB today's row** — уже есть актуальный курс. ``source`` из БД (cbu_live |
   manual | …).
3. **CBU live fetch** → save в БД → return. ``source="cbu_live"``.
4. **DB latest (любая дата)** — CBU down, но есть кэш. ``source="db_cached"``.
5. **JSON bootstrap** — `config/exchange/rates.json` для cold-start. ``source="manual"``.
6. **ExchangeRateError** — всё легло.

Env override остаётся highest для backward compat с legacy
``default_usd_uzs_rate()`` semantic. Step 4 (DB latest) — это, технически,
ситуация когда CBU не отдал, но last-known точно validен (даже если не
сегодняшний). Step 5 — последний бастион перед exception.

Repository conflict-handling (ON CONFLICT DO NOTHING) делает save идемпотентным —
параллельные requests не сломают index.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from datetime import date as date_type
from decimal import Decimal, InvalidOperation

from application.dto.exchange_rate import UsdUzsRate
from infrastructure.catalog.exchange_rates import (
    ExchangeRateError,
    load_usd_uzs_rate,
)
from infrastructure.external.cbu_client import CbuFetchError, fetch_usd_rate
from infrastructure.persistence.repositories.usd_rate_repository import (
    SqlAlchemyUsdRateRepository,
)

_logger = logging.getLogger(__name__)
_ENV_VAR = "USD_UZS_RATE"


class UsdRateService:
    def __init__(self, repository: SqlAlchemyUsdRateRepository) -> None:
        self._repo = repository

    async def get_current_rate(self, today: date_type | None = None) -> UsdUzsRate:
        actual_today = today or datetime.now(tz=UTC).date()

        env_rate = _try_env_override(actual_today)
        if env_rate is not None:
            return env_rate

        db_today = await self._repo.get_for_date(actual_today)
        if db_today is not None:
            return db_today

        cbu_rate = await self._try_cbu_live(actual_today)
        if cbu_rate is not None:
            return cbu_rate

        db_latest = await self._repo.get_latest()
        if db_latest is not None:
            _logger.info("usd_rate.fallback_db_cached asof=%s", db_latest.asof)
            return UsdUzsRate(
                rate=db_latest.rate, asof=db_latest.asof, source="db_cached"
            )

        # Last bastion — bootstrap JSON.
        try:
            json_rate = load_usd_uzs_rate()
        except ExchangeRateError as exc:
            raise ExchangeRateError(
                f"all USD rate sources exhausted (env/DB today/CBU live/DB latest/JSON): {exc}"
            ) from exc
        _logger.warning("usd_rate.fallback_json_bootstrap asof=%s", json_rate.asof)
        return json_rate

    async def _try_cbu_live(self, today: date_type) -> UsdUzsRate | None:
        try:
            cbu = await fetch_usd_rate()
        except CbuFetchError as exc:
            # exc_info=exc сохраняет цепочку (ConnectionResetError → SSLError → CbuFetchError),
            # без этого оператор видит только финальное сообщение без traceback.
            _logger.warning("usd_rate.cbu_unavailable", exc_info=exc)
            return None
        rate = UsdUzsRate(rate=cbu.rate, asof=cbu.asof, source="cbu_live")
        await self._repo.save(
            rate=rate,
            raw_response=cbu.raw,
            fetched_at=datetime.now(tz=UTC),
            nominal=cbu.nominal,
        )
        _logger.info("usd_rate.cbu_fetched_and_saved asof=%s rate=%s", cbu.asof, cbu.rate)
        return rate


def _try_env_override(today: date_type) -> UsdUzsRate | None:
    raw = os.getenv(_ENV_VAR)
    if raw is None or not raw.strip():
        return None
    try:
        rate = Decimal(raw.strip())
    except InvalidOperation:
        _logger.warning("usd_rate.env_invalid value=%r", raw)
        return None
    # asof = today — env override фиксирует курс на «сейчас», не на исторический день.
    return UsdUzsRate(rate=rate, asof=today, source="env")
