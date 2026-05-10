"""ScoringService: агрегация RedFlag → RiskScore + Recommendation."""

from datetime import date

from domain.entities.red_flag import RedFlag
from domain.rules.meta.insufficient_data import INSUFFICIENT_DATA_RULE_ID
from domain.services.scoring_service import Recommendation, ScoringService
from domain.value_objects.flag_severity import FlagSeverity


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
