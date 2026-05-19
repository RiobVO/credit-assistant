"""ScoringService: агрегирует RedFlag-ги в risk score 0-100 + recommendation.

Веса severity (LOW=1, MEDIUM=3, HIGH=7, CRITICAL=15) — экспоненциальный рост,
выровнено по Базель III IRB intuition. Финальная калибровка — после прогона на
реальных папиных фирмах в Phase 2 (см. ADR 0003).

**Layered overrides** (ADR-0024 / Commit 2):

1. **INSUFFICIENT_DATA** floor (CA-016 / Phase 1 legacy): rule срабатывает только
   при полном вакууме (0 annual + 0 quarterly + 0 monthly). Применяет defensive
   floor score=50, recommendation=REVIEW.
2. **Confidence Layer** (Commit 2): расширение для partial-data случаев. Если
   передан snapshot, считаем coverage 0-100 и применяем tier-aware penalty:
   * HIGH (≥75): no change.
   * MEDIUM (50-74): mild penalty +5 к raw score.
   * LOW (30-49): force REVIEW, floor 50.
   * CRITICAL (<30): force REVIEW, floor 50 (overlaps с INSUFFICIENT_DATA).

Snapshot — optional parameter для backward-compat existing tests / call-sites.
В production `dossier.py` всегда передаёт snapshot после Commit 2.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.red_flag import RedFlag
from domain.rules.meta.insufficient_data import INSUFFICIENT_DATA_RULE_ID
from domain.services.confidence_layer import (
    ConfidenceResult,
    ConfidenceTier,
    compute_confidence,
)
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
    # ADR-0024 Commit 2: данные о data-quality оценке, если snapshot был передан.
    # None если ScoringService.score() вызван без snapshot (legacy call-sites).
    confidence: ConfidenceResult | None = None


class ScoringService:
    # Калибровка v1: <15 APPROVE, 15-29 REVIEW, ≥30 REJECT.
    # Один CRITICAL (15) = REVIEW; CRITICAL + ~2 HIGH (32) = REJECT.
    # Перекалибровка — после Phase 2 на реальных кейсах (см. ADR 0003).
    APPROVE_BELOW = 15
    REVIEW_BELOW = 30
    MAX_SCORE = 100

    # CA-016: defensive floor при срабатывании INSUFFICIENT_DATA — display ≤ 50,
    # recommendation = REVIEW. См. domain/rules/meta/insufficient_data.py.
    INSUFFICIENT_DATA_FLOOR = 50

    # ADR-0024 / Commit 2: Confidence Layer floor + penalty.
    LOW_CONFIDENCE_FLOOR = 50
    MEDIUM_CONFIDENCE_PENALTY = 5

    def score(
        self, flags: list[RedFlag], *, snapshot: BorrowerSnapshot | None = None
    ) -> RiskScore:
        breakdown = {sev: 0 for sev in FlagSeverity}
        total_weight = 0
        for flag in flags:
            breakdown[flag.severity] += 1
            total_weight += flag.severity.weight

        score = min(total_weight, self.MAX_SCORE)
        recommendation = self._resolve_recommendation(score)

        # INSUFFICIENT_DATA legacy floor (полный вакуум).
        if any(f.rule_id == INSUFFICIENT_DATA_RULE_ID for f in flags):
            score = max(score, self.INSUFFICIENT_DATA_FLOOR)
            recommendation = Recommendation.REVIEW

        # ADR-0024 Commit 2: Confidence Layer (partial data).
        confidence: ConfidenceResult | None = None
        if snapshot is not None:
            confidence = compute_confidence(snapshot)
            score, recommendation = self._apply_confidence(
                score, recommendation, confidence
            )

        return RiskScore(
            score=score,
            recommendation=recommendation,
            severity_breakdown=breakdown,
            confidence=confidence,
        )

    def _resolve_recommendation(self, score: int) -> Recommendation:
        if score < self.APPROVE_BELOW:
            return Recommendation.APPROVE
        if score < self.REVIEW_BELOW:
            return Recommendation.REVIEW
        return Recommendation.REJECT

    def _apply_confidence(
        self,
        score: int,
        recommendation: Recommendation,
        confidence: ConfidenceResult,
    ) -> tuple[int, Recommendation]:
        """ADR-0024: tier-aware floor + penalty."""
        if confidence.tier == ConfidenceTier.HIGH:
            return score, recommendation
        if confidence.tier == ConfidenceTier.MEDIUM:
            new_score = min(score + self.MEDIUM_CONFIDENCE_PENALTY, self.MAX_SCORE)
            new_recommendation = self._resolve_recommendation(new_score)
            # MEDIUM: penalty applied к score, но не force REVIEW (mild signal).
            return new_score, new_recommendation
        # LOW / CRITICAL — force REVIEW + floor 50.
        new_score = max(score, self.LOW_CONFIDENCE_FLOOR)
        # Если raw score уже выше threshold REJECT (≥30) — оставляем REJECT;
        # иначе principle conservatism: REVIEW.
        if new_score >= self.REVIEW_BELOW:
            new_recommendation = (
                Recommendation.REVIEW
                if recommendation != Recommendation.REJECT
                else Recommendation.REJECT
            )
        else:
            new_recommendation = Recommendation.REVIEW
        return new_score, new_recommendation
