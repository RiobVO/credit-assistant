"""ConfidenceLayer: data-quality-aware floor над risk score.

ADR-0024 / Commit 2: расширение defensive INSUFFICIENT_DATA-policy.

**Проблема**. ``INSUFFICIENT_DATA`` срабатывает только при **полном** вакууме
(0 annual + 0 quarterly + 0 monthly). Borrower с заполнившими borrower-карточку
(ИНН/ОПФ/ОКЭД/директор) + 2 годовыми отчётами, но БЕЗ ЭСФ / VAT / monthly /
counterparty / tax_events получает в правилах 0 срабатываний → итоговый score
0/100 «Одобрить». Это clinically misleading.

**Решение** (per FRB SR 11-7 / Basel III IRB partial-data conservatism):
параллельный confidence score 0-100, derived из coverage data sources,
применяется как **floor** на risk score + force REVIEW при low coverage.

**Tier'ы** (cumulative coverage 0-100):

* HIGH (≥75): no change to score / recommendation.
* MEDIUM (50-74): mild penalty (+5 к raw score), recommendation unchanged.
* LOW (30-49): force REVIEW, ``score = max(raw + 15, 50)``.
* CRITICAL (<30): force REVIEW, ``score = max(raw + 25, 50)``.

Coverage formula (max 100):

| Источник | Weight | Полностью при |
|---|---|---|
| Borrower core (ИНН/ОПФ/ОКЭД/директор) | 10 | заполнены 4/4 |
| Annual reports | 15 | ≥2 годовых |
| VAT periods | 12 | ≥6 периодов |
| Monthly turnover | 10 | ≥12 месяцев |
| Quarterly reports | 8 | ≥4 кварталов |
| Counterparties (buyers + suppliers) | 10 | оба заполнены |
| Tax events | 10 | ≥6 событий |
| Invoices (ESF) | 10 | ≥10 счетов |
| Loan request | 5 | задан |
| Base (всегда) | 10 | присутствует всегда |

Подбирается под typical UZ-MSB банк-онбординг: ≥75 ≈ «банк собрал большую
часть документов»; 30-49 ≈ «только borrower-карточка + годовая отчётность»;
<30 ≈ INSUFFICIENT_DATA territory (но `INSUFFICIENT_DATA` rule fires только
если **нет ни одной** точки выручки — partial случаи покрываются здесь).

Pure-domain функция, без I/O. Veight'ы захардкожены — после Phase 2
калибровки на реальных случаях переносим в `config/rules/confidence.yaml`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from domain.entities.borrower_snapshot import BorrowerSnapshot


class ConfidenceTier(StrEnum):
    HIGH = "high"  # ≥75
    MEDIUM = "medium"  # 50-74
    LOW = "low"  # 30-49
    CRITICAL = "critical"  # <30


@dataclass(frozen=True, slots=True)
class ConfidenceResult:
    """Метрика data-quality для borrower snapshot."""

    coverage_pct: int  # 0-100
    tier: ConfidenceTier
    sources_present: tuple[str, ...]  # для аудита: какие источники вкладываются
    sources_missing: tuple[str, ...]


# Weights (sum = 100).
_W_BASE = 10
_W_BORROWER_CORE = 10
_W_ANNUAL = 15
_W_VAT = 12
_W_MONTHLY = 10
_W_QUARTERLY = 8
_W_COUNTERPARTIES = 10
_W_TAX_EVENTS = 10
_W_INVOICES = 10
_W_LOAN_REQUEST = 5


def compute_confidence(snapshot: BorrowerSnapshot) -> ConfidenceResult:
    """Считает confidence 0-100 по присутствию ключевых data sources."""
    present: list[str] = []
    missing: list[str] = []
    score = _W_BASE
    present.append("base")

    # Borrower core: ИНН + ОПФ + ОКЭД + директор.
    borrower = snapshot.borrower
    core_filled = sum(
        [
            bool(borrower.inn),
            bool(borrower.legal_form),
            bool(borrower.oked_main),
            bool(borrower.director_name),
        ]
    )
    if core_filled == 4:
        score += _W_BORROWER_CORE
        present.append("borrower_core")
    elif core_filled >= 2:
        score += _W_BORROWER_CORE * core_filled // 4
        present.append(f"borrower_core_partial_{core_filled}/4")
    else:
        missing.append("borrower_core")

    # Annual reports.
    annual_count = len(snapshot.annual_reports)
    if annual_count >= 2:
        score += _W_ANNUAL
        present.append("annual_reports")
    elif annual_count == 1:
        score += _W_ANNUAL // 2
        present.append("annual_reports_partial")
    else:
        missing.append("annual_reports")

    # VAT periods.
    vat_count = len(snapshot.vat_periods)
    if vat_count >= 6:
        score += _W_VAT
        present.append("vat_periods")
    elif vat_count >= 1:
        score += _W_VAT * vat_count // 6
        present.append(f"vat_periods_partial_{vat_count}")
    else:
        missing.append("vat_periods")

    # Monthly turnover.
    monthly_count = len(snapshot.monthly_turnover)
    if monthly_count >= 12:
        score += _W_MONTHLY
        present.append("monthly_turnover")
    elif monthly_count >= 1:
        score += _W_MONTHLY * monthly_count // 12
        present.append(f"monthly_turnover_partial_{monthly_count}")
    else:
        missing.append("monthly_turnover")

    # Quarterly reports.
    quarterly_count = len(snapshot.quarterly_reports)
    if quarterly_count >= 4:
        score += _W_QUARTERLY
        present.append("quarterly_reports")
    elif quarterly_count >= 1:
        score += _W_QUARTERLY * quarterly_count // 4
        present.append(f"quarterly_reports_partial_{quarterly_count}")
    else:
        missing.append("quarterly_reports")

    # Counterparties (both sides).
    has_buyers = bool(snapshot.counterparties_buyers)
    has_suppliers = bool(snapshot.counterparties_suppliers)
    if has_buyers and has_suppliers:
        score += _W_COUNTERPARTIES
        present.append("counterparties")
    elif has_buyers or has_suppliers:
        score += _W_COUNTERPARTIES // 2
        present.append("counterparties_partial")
    else:
        missing.append("counterparties")

    # Tax events.
    tax_count = len(snapshot.tax_events)
    if tax_count >= 6:
        score += _W_TAX_EVENTS
        present.append("tax_events")
    elif tax_count >= 1:
        score += _W_TAX_EVENTS * tax_count // 6
        present.append(f"tax_events_partial_{tax_count}")
    else:
        missing.append("tax_events")

    # Invoices (ESF register).
    invoice_count = len(snapshot.invoices)
    if invoice_count >= 10:
        score += _W_INVOICES
        present.append("invoices")
    elif invoice_count >= 1:
        score += _W_INVOICES * invoice_count // 10
        present.append(f"invoices_partial_{invoice_count}")
    else:
        missing.append("invoices")

    # Loan request — sanity check, не data source.
    if snapshot.loan_request is not None:
        score += _W_LOAN_REQUEST
        present.append("loan_request")
    else:
        missing.append("loan_request")

    coverage = min(score, 100)
    tier = _resolve_tier(coverage)
    return ConfidenceResult(
        coverage_pct=coverage,
        tier=tier,
        sources_present=tuple(present),
        sources_missing=tuple(missing),
    )


def _resolve_tier(coverage: int) -> ConfidenceTier:
    if coverage >= 75:
        return ConfidenceTier.HIGH
    if coverage >= 50:
        return ConfidenceTier.MEDIUM
    if coverage >= 30:
        return ConfidenceTier.LOW
    return ConfidenceTier.CRITICAL
