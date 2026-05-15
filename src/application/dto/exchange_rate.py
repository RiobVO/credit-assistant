"""ExchangeRate DTO: курс валютной пары на дату (CA-DS24).

Чистый dataclass без I/O. Loader живёт в
``infrastructure.catalog.exchange_rates``. Source — ``config/exchange/rates.json``
с env override ``USD_UZS_RATE`` для production-deploy без правки JSON.

Decimal вместо float — UZS-суммы (миллиарды) теряют точность во float-арифметике.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class UsdUzsRate:
    rate: Decimal  # сколько UZS за 1 USD
    asof: date
    source: str  # ``manual`` | ``env`` | ``cbu`` (last для CA-DS24b)
