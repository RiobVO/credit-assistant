"""HTTP-клиент для CBU API — USD/UZS курс с cbu.uz (T0.2).

Endpoint: ``https://cbu.uz/oz/arkhiv-kursov-valyut/json/USD/`` — publicly
доступен (robots.txt не disallow, нет crawl-delay). Response: JSON array из
1 элемента для конкретной валюты. См. ADR-0014 для pattern.

Tight retry budget: timeout 3s + 2 retries (0.5s + 1s backoff) = max ~7.5s.
Endpoint user-facing — service после Failure сразу fallback на DB cached.

Per-call ``async with httpx.AsyncClient`` — никаких global singletons.
Endpoint вызывается редко (DB-cache hits в 99% случаев), connection-pool
overhead vs lifecycle complexity — не выгоден.

User-Agent identity: ``credit-assistant/1.0 (+contact:eleru340@gmail.com)``.
Polite-identification для CBU operations team, если возникнут вопросы.

``CBU_API_URL`` env override — на случай DR/migration URL.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

_logger = logging.getLogger(__name__)

_DEFAULT_URL = "https://cbu.uz/oz/arkhiv-kursov-valyut/json/USD/"
_USER_AGENT = "credit-assistant/1.0 (+contact:eleru340@gmail.com)"
_TIMEOUT_S = 3.0
_RETRY_BACKOFFS_S = (0.5, 1.0)  # 2 retries: после первого fail спим 0.5s, второго 1s


class CbuFetchError(RuntimeError):
    """Любая ошибка при получении/парсинге CBU response — timeout, не-200, malformed JSON."""


@dataclass(frozen=True, slots=True)
class CbuRate:
    """Сырой ответ от CBU — нормализован и валидирован, но domain DTO не он."""

    rate: Decimal
    asof: date_type
    nominal: int
    raw: dict[str, Any]


async def fetch_usd_rate() -> CbuRate:
    """Получить актуальный USD/UZS курс. Raise CbuFetchError на любую ошибку.

    Retry policy: 3 попытки общим bedget'ом ~7.5s. Логи на каждую попытку.
    """
    url = os.getenv("CBU_API_URL", _DEFAULT_URL)
    last_exc: Exception | None = None

    attempts = (0.0, *_RETRY_BACKOFFS_S)
    for attempt, backoff in enumerate(attempts):
        if backoff > 0:
            await asyncio.sleep(backoff)
        try:
            return await _fetch_once(url)
        except Exception as exc:
            last_exc = exc
            _logger.warning(
                "cbu.fetch_attempt_failed attempt=%d url=%s error=%r",
                attempt + 1,
                url,
                exc,
            )

    raise CbuFetchError(f"all {len(attempts)} CBU fetch attempts failed: {last_exc!r}")


async def _fetch_once(url: str) -> CbuRate:
    async with httpx.AsyncClient(
        timeout=_TIMEOUT_S, headers={"User-Agent": _USER_AGENT}
    ) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise CbuFetchError(f"non-200 status: {resp.status_code}")
    try:
        payload = resp.json()
    except ValueError as exc:
        raise CbuFetchError(f"malformed JSON: {exc}") from exc
    return _parse_payload(payload)


def _parse_payload(payload: Any) -> CbuRate:
    if not isinstance(payload, list):
        raise CbuFetchError(f"expected JSON array, got {type(payload).__name__}")
    if len(payload) == 0:
        raise CbuFetchError("empty rates array")
    raw = payload[0]
    if not isinstance(raw, dict):
        raise CbuFetchError(f"expected dict element, got {type(raw).__name__}")

    try:
        rate = Decimal(str(raw["Rate"]))
    except (KeyError, InvalidOperation) as exc:
        raise CbuFetchError(f"invalid Rate field: {exc}") from exc

    try:
        nominal = int(str(raw["Nominal"]))
    except (KeyError, ValueError) as exc:
        raise CbuFetchError(f"invalid Nominal field: {exc}") from exc

    try:
        asof = datetime.strptime(str(raw["Date"]), "%d.%m.%Y").date()
    except (KeyError, ValueError) as exc:
        raise CbuFetchError(f"invalid Date field: {exc}") from exc

    return CbuRate(rate=rate, asof=asof, nominal=nominal, raw=raw)
