"""Unit-тесты `_kpi_value_to_output` mapper'а (CA-048).

Проверяем round-trip Domain-DTO → Pydantic-output для нового опционального
поля ``level_tone``. Остальной маппинг (Borrower, FinancialReport и т.п.)
покрыт integration-тестами на endpoint'ы.
"""

from __future__ import annotations

from decimal import Decimal

from application.dto.kpi_bundle import KpiLevelTone, KpiUnit, KpiValue
from interfaces.api.shared.dossier_mapper import _kpi_value_to_output


def test_kpi_value_to_output_level_tone_warn() -> None:
    """KpiLevelTone.WARN → "warn" в Pydantic-output (StrEnum value совпадает
    с KpiLevelToneCode Literal)."""
    kv = KpiValue(
        value=Decimal("10.7"),
        unit=KpiUnit.PCT,
        yoy_pct=None,
        sparkline=(),
        level_tone=KpiLevelTone.WARN,
    )
    out = _kpi_value_to_output(kv)
    assert out is not None
    assert out.level_tone == "warn"


def test_kpi_value_to_output_level_tone_good() -> None:
    kv = KpiValue(
        value=Decimal("0"),
        unit=KpiUnit.RATIO,
        yoy_pct=None,
        sparkline=(),
        level_tone=KpiLevelTone.GOOD,
    )
    out = _kpi_value_to_output(kv)
    assert out is not None
    assert out.level_tone == "good"


def test_kpi_value_to_output_level_tone_bad() -> None:
    kv = KpiValue(
        value=Decimal("5.80"),
        unit=KpiUnit.RATIO,
        yoy_pct=None,
        sparkline=(),
        level_tone=KpiLevelTone.BAD,
    )
    out = _kpi_value_to_output(kv)
    assert out is not None
    assert out.level_tone == "bad"


def test_kpi_value_to_output_no_level_tone_is_none() -> None:
    """Default None для KPI без universal threshold (revenue_ltm, ebit) —
    Pydantic-output остаётся None, не превращается в строку."""
    kv = KpiValue(
        value=Decimal("12000000000"),
        unit=KpiUnit.UZS,
        yoy_pct=None,
        sparkline=(Decimal("100"), Decimal("200")),
    )
    out = _kpi_value_to_output(kv)
    assert out is not None
    assert out.level_tone is None


def test_kpi_value_to_output_returns_none_for_none_input() -> None:
    """None-KpiValue (degraded mode) проходит насквозь как None."""
    assert _kpi_value_to_output(None) is None
