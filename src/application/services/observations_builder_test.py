"""Unit-тест observations_builder (Phase 10 cover rationale)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from application.dto.kpi_bundle import (
    KpiBundle,
    KpiLevelTone,
    KpiUnit,
    KpiValue,
)
from application.dto.pdf_messages import PdfMessages
from application.services.observations_builder import (
    MAX_OBSERVATIONS_PER_SIDE,
    build_observations,
)
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.red_flag import RedFlag
from domain.rules.rule import Rule, RuleRegistry
from domain.value_objects.date_range import DateRange
from domain.value_objects.flag_severity import FlagSeverity
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money
from infrastructure.i18n.pdf_messages import load_pdf_messages


def _ru_messages() -> PdfMessages:
    return load_pdf_messages("ru")


def _uz_messages() -> PdfMessages:
    return load_pdf_messages("uz")


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("306399449"),
        name="ООО Тест",
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="И.И.",
        director_appointed_at=date(2018, 1, 1),
        okved_main="46.39",
        registered_address="г. Ташкент",
    )


def _money(amount: int) -> Money:
    return Money(Decimal(amount), Currency.UZS)


def _annual(year: int, revenue: int, profit: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(start=date(year, 1, 1), end=date(year, 12, 31)),
        revenue=_money(revenue),
        net_profit=_money(profit),
        taxes_paid=_money(0),
    )


def _kpi(value: str, *, yoy: str | None = None, tone: KpiLevelTone | None = None) -> KpiValue:
    return KpiValue(
        value=Decimal(value),
        unit=KpiUnit.PCT,
        yoy_pct=Decimal(yoy) if yoy is not None else None,
        sparkline=(),
        level_tone=tone,
    )


def _snapshot(reports: list[FinancialReport] | None = None) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 1),
        annual_reports=reports or [],
    )


def _empty_kpis() -> KpiBundle:
    return KpiBundle(revenue_ltm=None, ebit=None, roe=None, debt_to_ebit=None)


def _registry(*pairs: tuple[str, str]) -> RuleRegistry:
    return RuleRegistry(
        rules=[
            Rule(
                id=rid,
                version="v1",
                severity=FlagSeverity.HIGH,
                source="test",
                category="financial",
                fn=lambda s: None,
                name=name,
            )
            for rid, name in pairs
        ],
    )


def _flag(rule_id: str, severity: FlagSeverity, message: str = "msg") -> RedFlag:
    return RedFlag(
        rule_id=rule_id,
        rule_version="v1",
        severity=severity,
        source="src",
        message=message,
        evidence={"share": Decimal("38.7")},
    )


class TestStrengths:
    def test_revenue_growth_strength(self) -> None:
        kpis = KpiBundle(
            revenue_ltm=_kpi("21500", yoy="18.2"),
            ebit=None,
            roe=None,
            debt_to_ebit=None,
        )
        obs = build_observations(_snapshot(), kpis, (), _registry(), _ru_messages())
        assert len(obs.strengths) >= 1
        assert "Рост выручки" in obs.strengths[0].head
        assert "18,2" in obs.strengths[0].num

    def test_roe_good_strength(self) -> None:
        kpis = KpiBundle(
            revenue_ltm=None,
            ebit=None,
            roe=_kpi("18.2", tone=KpiLevelTone.GOOD),
            debt_to_ebit=None,
        )
        obs = build_observations(_snapshot(), kpis, (), _registry(), _ru_messages())
        assert any("ROE" in s.head for s in obs.strengths)

    def test_negative_yoy_not_strength(self) -> None:
        kpis = KpiBundle(
            revenue_ltm=_kpi("10000", yoy="-5.0"),
            ebit=None,
            roe=None,
            debt_to_ebit=None,
        )
        obs = build_observations(_snapshot(), kpis, (), _registry(), _ru_messages())
        assert not any("Рост выручки" in s.head for s in obs.strengths)

    def test_warn_roe_not_strength(self) -> None:
        kpis = KpiBundle(
            revenue_ltm=None,
            ebit=None,
            roe=_kpi("10.5", tone=KpiLevelTone.WARN),
            debt_to_ebit=None,
        )
        obs = build_observations(_snapshot(), kpis, (), _registry(), _ru_messages())
        assert not any("ROE" in s.head for s in obs.strengths)

    def test_capped_at_max(self) -> None:
        kpis = KpiBundle(
            revenue_ltm=_kpi("21500", yoy="18.2"),
            ebit=None,
            roe=_kpi("18.2", tone=KpiLevelTone.GOOD),
            debt_to_ebit=_kpi("0", tone=KpiLevelTone.GOOD),
        )
        snap = _snapshot(
            reports=[
                _annual(2023, 14_820_000_000, 1_185_000_000),
                _annual(2024, 17_640_000_000, 1_590_000_000),
            ],
        )
        obs = build_observations(snap, kpis, (), _registry(), _ru_messages())
        assert len(obs.strengths) <= MAX_OBSERVATIONS_PER_SIDE


class TestRisks:
    def test_no_flags_no_risks(self) -> None:
        obs = build_observations(_snapshot(), _empty_kpis(), (), _registry(), _ru_messages())
        assert obs.risks == ()

    def test_risks_sorted_by_severity(self) -> None:
        flags = (
            _flag("LOW_RULE", FlagSeverity.LOW),
            _flag("CRIT_RULE", FlagSeverity.CRITICAL),
            _flag("MED_RULE", FlagSeverity.MEDIUM),
            _flag("HIGH_RULE", FlagSeverity.HIGH),
        )
        registry = _registry(
            ("CRIT_RULE", "Критическое нарушение"),
            ("HIGH_RULE", "Высокий риск"),
            ("MED_RULE", "Средний риск"),
            ("LOW_RULE", "Низкий риск"),
        )
        obs = build_observations(_snapshot(), _empty_kpis(), flags, registry, _ru_messages())
        assert len(obs.risks) == MAX_OBSERVATIONS_PER_SIDE
        # Порядок critical → high → medium (top-3, low отрезан)
        assert obs.risks[0].head == "Критическое нарушение"
        assert obs.risks[1].head == "Высокий риск"
        assert obs.risks[2].head == "Средний риск"

    def test_risk_falls_back_to_rule_id_if_unregistered(self) -> None:
        flags = (_flag("UNKNOWN_RULE", FlagSeverity.HIGH),)
        obs = build_observations(_snapshot(), _empty_kpis(), flags, _registry(), _ru_messages())
        assert obs.risks[0].head == "UNKNOWN_RULE"


class TestLocalization:
    """T0.4 / ADR-0015: head/num/ctx локализуются через PdfMessages."""

    def test_revenue_growth_head_uses_uz_template(self) -> None:
        kpis = KpiBundle(
            revenue_ltm=_kpi("21500", yoy="18.2"),
            ebit=None,
            roe=None,
            debt_to_ebit=None,
        )
        obs = build_observations(_snapshot(), kpis, (), _registry(), _uz_messages())
        # UZ: "Tushum oʻsishi +18,2% YoY" — RU prefix "Рост" не должно встретиться.
        assert "Tushum oʻsishi" in obs.strengths[0].head
        assert "Рост" not in obs.strengths[0].head
        assert "18,2" in obs.strengths[0].num

    def test_roe_head_uses_uz_template(self) -> None:
        kpis = KpiBundle(
            revenue_ltm=None,
            ebit=None,
            roe=_kpi("18.2", tone=KpiLevelTone.GOOD),
            debt_to_ebit=None,
        )
        obs = build_observations(_snapshot(), kpis, (), _registry(), _uz_messages())
        assert any("tarmoq medianasidan" in s.head for s in obs.strengths)

    def test_profit_head_year_placeholder_resolved_uz(self) -> None:
        snap = _snapshot(
            reports=[
                _annual(2023, 14_820_000_000, 1_185_000_000),
                _annual(2024, 17_640_000_000, 1_590_000_000),
            ],
        )
        obs = build_observations(snap, _empty_kpis(), (), _registry(), _uz_messages())
        # UZ template: "{year} yilda sof foyda {num} soʻm"
        assert any("2024 yilda" in s.head for s in obs.strengths)
        assert any("sof foyda" in s.head for s in obs.strengths)

    def test_no_debt_observation_uz_static(self) -> None:
        kpis = KpiBundle(
            revenue_ltm=None,
            ebit=None,
            roe=None,
            debt_to_ebit=_kpi("0", tone=KpiLevelTone.GOOD),
        )
        obs = build_observations(_snapshot(), kpis, (), _registry(), _uz_messages())
        assert any("Qarz yuki yoʻq" in s.head for s in obs.strengths)
