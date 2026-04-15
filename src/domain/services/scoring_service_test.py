"""ScoringService: агрегация RedFlag → RiskScore + Recommendation."""

from datetime import date

from domain.entities.red_flag import RedFlag
from domain.services.scoring_service import Recommendation, ScoringService
from domain.value_objects.flag_severity import FlagSeverity


def _flag(severity: FlagSeverity) -> RedFlag:
    return RedFlag(
        rule_id=f"R_{severity.value.upper()}",
        rule_version="v1",
        severity=severity,
        source="test",
        message="m",
        evidence={},
        detected_at=date(2026, 5, 8),
    )


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

    def test_above_50_is_reject(self) -> None:
        # 4 critical = 60 → REJECT
        flags = [_flag(FlagSeverity.CRITICAL)] * 4
        assert ScoringService().score(flags).recommendation == Recommendation.REJECT


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
