"""ScoringService: агрегирует RedFlag-ги в risk score 0-100 + recommendation.

Веса severity (LOW=1, MEDIUM=3, HIGH=7, CRITICAL=15) — экспоненциальный рост,
выровнено по Базель III IRB intuition. Финальная калибровка — после прогона на
реальных папиных фирмах в Phase 2 (см. ADR 0003).
"""

from dataclasses import dataclass, field
from enum import StrEnum

from domain.entities.red_flag import RedFlag
from domain.value_objects.flag_severity import FlagSeverity


class Recommendation(StrEnum):
    APPROVE = "approve"
    REVIEW = "review"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class RiskScore:
    score: int  # 0-100, clamped
    recommendation: Recommendation
    severity_breakdown: dict[FlagSeverity, int] = field(default_factory=dict)


class ScoringService:
    APPROVE_BELOW = 15
    REVIEW_BELOW = 51  # т.е. REVIEW = [15, 50], REJECT = >50
    MAX_SCORE = 100

    def score(self, flags: list[RedFlag]) -> RiskScore:
        breakdown = {sev: 0 for sev in FlagSeverity}
        total_weight = 0
        for flag in flags:
            breakdown[flag.severity] += 1
            total_weight += flag.severity.weight

        score = min(total_weight, self.MAX_SCORE)
        if score < self.APPROVE_BELOW:
            recommendation = Recommendation.APPROVE
        elif score < self.REVIEW_BELOW:
            recommendation = Recommendation.REVIEW
        else:
            recommendation = Recommendation.REJECT

        return RiskScore(
            score=score,
            recommendation=recommendation,
            severity_breakdown=breakdown,
        )
