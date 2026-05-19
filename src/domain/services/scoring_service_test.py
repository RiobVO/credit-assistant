"""ScoringService: агрегация RedFlag → RiskScore + Recommendation."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.red_flag import RedFlag
from domain.rules.meta.insufficient_data import INSUFFICIENT_DATA_RULE_ID
from domain.services.scoring_service import Recommendation, ScoringService
from domain.value_objects.date_range import DateRange
from domain.value_objects.flag_severity import FlagSeverity
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money


def _flag(severity: FlagSeverity, *, rule_id: str | None = None) -> RedFlag:
    return RedFlag(
        rule_id=rule_id or f"R_{severity.value.upper()}",
        rule_version="v1",
        severity=severity,
        source="test",
        message="m",
        evidence={},
        detected_at=date(2026, 5, 8),
    )


def _insufficient_data_flag() -> RedFlag:
    return _flag(FlagSeverity.HIGH, rule_id=INSUFFICIENT_DATA_RULE_ID)


class TestScoringServiceEmpty:
    def test_empty_flags_returns_zero_and_approve(self) -> None:
        result = ScoringService().score([])
        assert result.score == 0
        assert result.recommendation == Recommendation.APPROVE


class TestScoringServiceWeights:
    def test_single_low_flag_weight_1(self) -> None:
        result = ScoringService().score([_flag(FlagSeverity.LOW)])
        assert result.score == 1
        assert result.recommendation == Recommendation.APPROVE

    def test_single_medium_flag_weight_3(self) -> None:
        result = ScoringService().score([_flag(FlagSeverity.MEDIUM)])
        assert result.score == 3
        assert result.recommendation == Recommendation.APPROVE

    def test_single_high_flag_weight_7(self) -> None:
        result = ScoringService().score([_flag(FlagSeverity.HIGH)])
        assert result.score == 7
        assert result.recommendation == Recommendation.APPROVE

    def test_single_critical_flag_weight_15_review(self) -> None:
        result = ScoringService().score([_flag(FlagSeverity.CRITICAL)])
        assert result.score == 15
        assert result.recommendation == Recommendation.REVIEW

    def test_score_sums_weights_across_severities(self) -> None:
        flags = [
            _flag(FlagSeverity.LOW),
            _flag(FlagSeverity.MEDIUM),
            _flag(FlagSeverity.HIGH),
        ]
        result = ScoringService().score(flags)
        assert result.score == 1 + 3 + 7


class TestScoringServiceRecommendation:
    def test_below_15_is_approve(self) -> None:
        flags = [_flag(FlagSeverity.HIGH), _flag(FlagSeverity.HIGH)]  # 14
        assert ScoringService().score(flags).recommendation == Recommendation.APPROVE

    def test_at_15_is_review(self) -> None:
        # 15 ровно — REVIEW (граница включительно)
        assert (
            ScoringService().score([_flag(FlagSeverity.CRITICAL)]).recommendation
            == Recommendation.REVIEW
        )

    def test_at_30_is_reject(self) -> None:
        # 2 CRITICAL = 30 → REJECT (граница включительно)
        flags = [_flag(FlagSeverity.CRITICAL)] * 2
        assert ScoringService().score(flags).recommendation == Recommendation.REJECT

    def test_at_29_is_review(self) -> None:
        # 29 — последнее значение REVIEW
        flags = [_flag(FlagSeverity.CRITICAL), _flag(FlagSeverity.HIGH), _flag(FlagSeverity.HIGH)]
        # 15 + 7 + 7 = 29
        assert ScoringService().score(flags).recommendation == Recommendation.REVIEW


class TestScoringServiceCap:
    def test_score_capped_at_100(self) -> None:
        # 10 critical = 150 → clamp 100
        flags = [_flag(FlagSeverity.CRITICAL)] * 10
        assert ScoringService().score(flags).score == 100


class TestScoringServiceBreakdown:
    def test_severity_breakdown_counts_by_severity(self) -> None:
        flags = [
            _flag(FlagSeverity.LOW),
            _flag(FlagSeverity.LOW),
            _flag(FlagSeverity.HIGH),
        ]
        result = ScoringService().score(flags)
        assert result.severity_breakdown[FlagSeverity.LOW] == 2
        assert result.severity_breakdown[FlagSeverity.HIGH] == 1
        assert result.severity_breakdown[FlagSeverity.MEDIUM] == 0
        assert result.severity_breakdown[FlagSeverity.CRITICAL] == 0


class TestInsufficientDataPolicy:
    """CA-016: INSUFFICIENT_DATA принудительно даёт score floor 50 + REVIEW.

    Защита от ложно-оптимистичного APPROVE (display=100) при пустом снапшоте.
    """

    def test_only_insufficient_data_forces_score_50_review(self) -> None:
        # Без policy: HIGH (=7) → APPROVE, display=93. С policy: floor 50, REVIEW.
        result = ScoringService().score([_insufficient_data_flag()])
        assert result.score == 50
        assert result.recommendation == Recommendation.REVIEW

    def test_insufficient_data_overrides_approve_low_score(self) -> None:
        # Один LOW-флаг (=1) обычно APPROVE; добавление INSUFFICIENT_DATA → REVIEW + 50.
        result = ScoringService().score([_flag(FlagSeverity.LOW), _insufficient_data_flag()])
        assert result.score == 50
        assert result.recommendation == Recommendation.REVIEW

    def test_insufficient_data_overrides_reject(self) -> None:
        # Высокий риск (2 CRITICAL = 30 → REJECT) + INSUFFICIENT_DATA → всё равно REVIEW.
        flags = [_flag(FlagSeverity.CRITICAL)] * 2 + [_insufficient_data_flag()]
        result = ScoringService().score(flags)
        # Реальный total_weight = 30+7=37, floor 50 → score=50; recommendation forced REVIEW.
        assert result.score == 50
        assert result.recommendation == Recommendation.REVIEW

    def test_insufficient_data_does_not_lower_score_above_floor(self) -> None:
        # Если других флагов хватает на >50 score, floor не уменьшает — берём max.
        flags = [_flag(FlagSeverity.CRITICAL)] * 5 + [_insufficient_data_flag()]
        # 5*15 + 7 = 82 (cap 100). max(82, 50) = 82.
        result = ScoringService().score(flags)
        assert result.score == 82
        assert result.recommendation == Recommendation.REVIEW

    def test_other_flags_without_insufficient_data_unchanged(self) -> None:
        # Контроль: без INSUFFICIENT_DATA политика не применяется.
        result = ScoringService().score([_flag(FlagSeverity.HIGH)])
        assert result.score == 7
        assert result.recommendation == Recommendation.APPROVE

    def test_empty_flags_still_zero_and_approve(self) -> None:
        # Контроль: нет ни одного флага → старое поведение (нет триггера policy).
        result = ScoringService().score([])
        assert result.score == 0
        assert result.recommendation == Recommendation.APPROVE


# ───────── ADR-0024 Commit 2: Confidence Layer integration ──────────────


def _money(amount: int) -> Money:
    return Money(Decimal(amount), Currency.UZS)


def _full_borrower() -> Borrower:
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


def _annual(year: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(start=date(year, 1, 1), end=date(year, 12, 31)),
        revenue=_money(14_000_000_000),
        net_profit=_money(1_000_000_000),
        taxes_paid=_money(0),
    )


def _partial_snapshot() -> BorrowerSnapshot:
    """Репро BR-2026-0050 TEST: только borrower + 2 annual reports."""
    from domain.value_objects.loan_request import LoanRequest

    return BorrowerSnapshot(
        borrower=_full_borrower(),
        as_of=date(2026, 5, 1),
        annual_reports=[_annual(2024), _annual(2025)],
        loan_request=LoanRequest(
            amount=_money(100_000_000),
            term_months=12,
            rate_pct=Decimal("24.5"),
            purpose="working_capital",
            category="business",
        ),
    )


class TestConfidenceLayerIntegration:
    """ADR-0024: Confidence Layer применяется когда snapshot передан в score()."""

    def test_score_without_snapshot_legacy_behavior(self) -> None:
        """Backward-compat: без snapshot Confidence Layer не активируется."""
        result = ScoringService().score([])
        assert result.score == 0
        assert result.recommendation == Recommendation.APPROVE
        assert result.confidence is None

    def test_partial_data_forces_review_floor_50(self) -> None:
        """BR-2026-0050 REPRO: 0 правил + partial data → score 50, REVIEW.

        Раньше: 0 flags + 100/Approve. После Commit 2: confidence LOW → floor 50.
        """
        result = ScoringService().score([], snapshot=_partial_snapshot())
        assert result.score == 50
        assert result.recommendation == Recommendation.REVIEW
        assert result.confidence is not None
        from domain.services.confidence_layer import ConfidenceTier

        assert result.confidence.tier == ConfidenceTier.LOW

    def test_high_confidence_full_data_no_change(self) -> None:
        """Full snapshot с большим coverage → HIGH tier → score не меняется."""
        from domain.entities.counterparty import Counterparty
        from domain.entities.monthly_turnover import MonthlyTurnover
        from domain.entities.tax_event import TaxEvent, TaxEventType
        from domain.entities.vat_period_report import VatPeriodReport
        from domain.value_objects.loan_request import LoanRequest

        snap = BorrowerSnapshot(
            borrower=_full_borrower(),
            as_of=date(2026, 5, 1),
            annual_reports=[_annual(2024), _annual(2025)],
            monthly_turnover=[
                MonthlyTurnover(
                    month_start=date(2025, m, 1),
                    revenue=_money(1_000_000_000),
                )
                for m in range(1, 13)
            ],
            vat_periods=[
                VatPeriodReport(
                    period=DateRange(start=date(2025, m, 1), end=date(2025, m, 28)),
                    vat_declared=_money(1_000_000),
                    esf_seller_vat_total=_money(1_000_000),
                )
                for m in range(1, 7)
            ],
            tax_events=[
                TaxEvent(
                    date=date(2025, m, 1),
                    type=TaxEventType.PAYMENT,
                    amount=_money(1_000_000),
                    delay_days=0,
                )
                for m in range(1, 7)
            ],
            counterparties_buyers=[
                Counterparty(inn=INN("100100100"), name="B1", registration_date=date(2020, 1, 1))
            ],
            counterparties_suppliers=[
                Counterparty(inn=INN("200200200"), name="S1", registration_date=date(2020, 1, 1))
            ],
            loan_request=LoanRequest(
                amount=_money(100_000_000),
                term_months=12,
                rate_pct=Decimal("24.5"),
                purpose="working_capital",
                category="business",
            ),
        )
        result = ScoringService().score([], snapshot=snap)
        from domain.services.confidence_layer import ConfidenceTier

        assert result.confidence is not None
        assert result.confidence.tier == ConfidenceTier.HIGH
        assert result.score == 0  # no flags + HIGH conf → no penalty
        assert result.recommendation == Recommendation.APPROVE

    def test_low_confidence_with_high_raw_score_keeps_reject(self) -> None:
        """LOW confidence + raw score уже REJECT (≥30) → остаётся REJECT, не downgrade в REVIEW."""
        flags = [_flag(FlagSeverity.CRITICAL)] * 3  # 45 → REJECT
        result = ScoringService().score(flags, snapshot=_partial_snapshot())
        # raw=45, LOW floor 50 → score=50; raw rec был REJECT (≥30) → остаётся REJECT.
        assert result.score == 50
        assert result.recommendation == Recommendation.REJECT
