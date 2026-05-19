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


# ----------- ADR-0024 Session 4: fx_exposure_ratio mapping --------------------


def test_kpi_value_to_output_fx_exposure_ratio_pct_no_level_tone() -> None:
    """fx_exposure_ratio: PCT-юнит, level_tone остаётся None (пороги ЦБ РУз
    отложены до verified §). Pydantic-output value сериализуется как str."""
    kv = KpiValue(
        value=Decimal(40),
        unit=KpiUnit.PCT,
        yoy_pct=None,
        sparkline=(),
    )
    out = _kpi_value_to_output(kv)
    assert out is not None
    assert out.value == "40"
    assert out.unit == "PCT"
    assert out.level_tone is None


def test_kpi_bundle_to_output_propagates_fx_exposure_ratio() -> None:
    """KpiBundle.fx_exposure_ratio → KpiBundleOutput.fx_exposure_ratio через
    _kpi_bundle_to_output, без потери поля.
    """
    from application.dto.kpi_bundle import KpiBundle

    from interfaces.api.shared.dossier_mapper import _kpi_bundle_to_output

    bundle = KpiBundle(
        revenue_ltm=None,
        ebit=None,
        roe=None,
        debt_to_ebit=None,
        fx_exposure_ratio=KpiValue(
            value=Decimal(40),
            unit=KpiUnit.PCT,
            yoy_pct=None,
            sparkline=(),
        ),
    )
    out = _kpi_bundle_to_output(bundle)
    assert out.fx_exposure_ratio is not None
    assert out.fx_exposure_ratio.value == "40"
    assert out.fx_exposure_ratio.unit == "PCT"


def test_pydantic_financial_report_input_accepts_liabilities_fx() -> None:
    """FinancialReportInput принимает liabilities_fx как MoneyInput.
    Маппинг через _to_financial_report пробрасывает в BalanceSnapshot.liabilities_fx.
    """
    from interfaces.api.shared.dossier_mapper import _to_financial_report
    from interfaces.api.shared.dossier_schema import FinancialReportInput

    payload = FinancialReportInput.model_validate({
        "period": {"start": "2025-01-01", "end": "2025-12-31"},
        "revenue": {"amount": "5000000000", "currency": "UZS"},
        "net_profit": {"amount": "500000000", "currency": "UZS"},
        "liabilities": {"amount": "2000000000", "currency": "UZS"},
        "liabilities_fx": {"amount": "800000000", "currency": "UZS"},
    })
    assert payload.liabilities_fx is not None
    assert payload.liabilities_fx.amount == Decimal("800000000")

    domain = _to_financial_report(payload)
    assert domain.balance_end is not None
    assert domain.balance_end.liabilities_fx is not None
    assert domain.balance_end.liabilities_fx.amount == Decimal("800000000")
