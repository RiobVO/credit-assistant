"""VAT_ESF_MISMATCH: разрыв декларация НДС vs агрегат НДС из ЭСФ как продавец >15%."""

# RULE_SOURCE: НК РУз ст. 256; Soliq внутренние методики
# CONFIDENCE: HIGH (regulatory + tax authority practice)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.vat_period_report import VatPeriodReport
from domain.rules.protocol import FiringEvidence

THRESHOLD = Decimal("0.15")


def vat_esf_mismatch(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    """Сравнить декларацию НДС и агрегат ЭСФ за один и тот же налоговый период.

    Берётся latest period с обоими заполненными полями (``vat_declared`` +
    ``esf_seller_vat_total``). Без полного периода → правило молчит (degraded).
    Это поведение задокументировано в ADR 0006 — реальные данные my3.soliq.uz
    приходят помесячно, и сравнивать имеет смысл только в рамках одного периода.
    """
    complete = [p for p in snapshot.vat_periods if _is_complete(p)]
    if not complete:
        return None

    latest = max(complete, key=lambda p: p.period.end)
    # mypy narrowing: _is_complete гарантирует, что оба поля не None.
    assert latest.vat_declared is not None
    assert latest.esf_seller_vat_total is not None

    vat_declared = latest.vat_declared.amount
    if vat_declared <= 0:
        return None

    sum_seller_vat = latest.esf_seller_vat_total.amount

    diff_pct = abs(vat_declared - sum_seller_vat) / vat_declared
    if diff_pct <= THRESHOLD:
        return None

    return FiringEvidence(
        message=f"Декларация НДС vs ЭСФ расходится на {diff_pct:.0%}",
        evidence={
            "vat_declared": str(vat_declared),
            "sum_seller_esf_vat": str(sum_seller_vat),
            "diff_pct": str(diff_pct),
            "period": [latest.period.start.isoformat(), latest.period.end.isoformat()],
        },
    )


def _is_complete(period: VatPeriodReport) -> bool:
    return period.vat_declared is not None and period.esf_seller_vat_total is not None
