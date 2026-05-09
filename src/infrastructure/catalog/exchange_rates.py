"""USD/UZS rate loader (CA-DS24).

Источник в порядке приоритета:
1. Env var ``USD_UZS_RATE`` — production override без правки JSON. Source = ``env``.
2. ``config/exchange/rates.json`` — дефолт + asof. Source = ``manual``.

CBU API (cbu.uz/services/) → CA-DS24b с pre-condition legal review (по
аналогии с CA-DS28 ГНК lookup). Сейчас только static + env.

Singleton НЕТ — endpoint вызывается редко, JSON парсится дёшево, env
override должен подхватываться без рестарта (хотя в compose это всё
равно требует redeploy с новым ENV).
"""

from __future__ import annotations

import json
import os
from datetime import date as date_type
from decimal import Decimal, InvalidOperation
from pathlib import Path

from application.dto.exchange_rate import UsdUzsRate

_RATES_DIR = Path(__file__).resolve().parents[3] / "config" / "exchange"
_DEFAULT_FILE = "rates.json"
_ENV_VAR = "USD_UZS_RATE"


class ExchangeRateError(ValueError):
    """Курсы валют недоступны или повреждены."""


def load_usd_uzs_rate(path: Path | None = None) -> UsdUzsRate:
    """Резолвит USD/UZS rate. Env override > JSON file.

    Raises ``ExchangeRateError`` если ни env, ни файл не дают валидного rate.
    """
    target = path or (_RATES_DIR / _DEFAULT_FILE)
    if not target.exists():
        raise ExchangeRateError(f"exchange rates config not found: {target}")
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExchangeRateError(f"invalid JSON in {target}: {exc}") from exc

    try:
        file_rate = Decimal(str(raw["usd_uzs"]))
        file_asof = date_type.fromisoformat(raw["asof"])
        file_source = str(raw.get("source", "manual"))
    except (KeyError, InvalidOperation, ValueError) as exc:
        raise ExchangeRateError(f"invalid rate fields in {target}: {exc}") from exc

    env_value = os.getenv(_ENV_VAR)
    if env_value is not None and env_value.strip():
        try:
            env_rate = Decimal(env_value.strip())
        except InvalidOperation as exc:
            raise ExchangeRateError(
                f"invalid {_ENV_VAR}={env_value!r}: not a decimal"
            ) from exc
        # asof остаётся из файла — env не несёт даты. Source меняется на ``env``.
        return UsdUzsRate(rate=env_rate, asof=file_asof, source="env")

    return UsdUzsRate(rate=file_rate, asof=file_asof, source=file_source)
