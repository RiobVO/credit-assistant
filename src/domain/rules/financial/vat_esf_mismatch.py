"""VAT_ESF_MISMATCH: разрыв декларация НДС vs агрегат НДС из ЭСФ как продавец >15%."""

# RULE_SOURCE: НК РУз ст. 256; Soliq внутренние методики
# CONFIDENCE: HIGH (regulatory + tax authority practice)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.vat_period_report import VatPeriodReport
from domain.rules.protocol import FiringEvidence

THRESHOLD = Decimal("0.15")
# ADR-0024: minimum vat_declared, ниже которого rule молчит. 10 млн UZS
# отделяет рабочие декларации от технических микро-периодов (закрытие
# квартала, единичные ввозы). Без minimum'а правило фолсит на крошечных
# абсолютах (например, 50 000 vs 70 000 → 40% mismatch). Per Claude Q0.B
# audit, источник: НК РУз ст. 47 + 257, материальность декларации.
VAT_DECLARED_MIN_THRESHOLD = Decimal("10000000")


def vat_esf_mismatch(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    """Сравнить декларацию НДС и агрегат ЭСФ за один и тот же налоговый период.

    Берётся latest period с обоими заполненными полями (``vat_declared`` +
    ``esf_seller_vat_total``). Без полного периода → правило молчит (degraded).
    Это поведение задокументировано в ADR 0006 — реальные данные my3.soliq.uz
    приходят помесячно, и сравнивать имеет смысл только в рамках одного периода.

    ADR-0024: при ``vat_declared`` ≤ 10 млн сум правило молчит — материальность
    декларации недостаточна для regulatory red flag.
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
    # ADR-0024 materiality threshold.
    if vat_declared < VAT_DECLARED_MIN_THRESHOLD:
        return None

    sum_seller_vat = latest.esf_seller_vat_total.amount

    diff_pct = abs(vat_declared - sum_seller_vat) / vat_declared
    if diff_pct <= THRESHOLD:
        return None

    return FiringEvidence(
        message=f"Декларация НДС vs ЭСФ расходится на {diff_pct:.0%}",
        message_uz=f"QQS deklaratsiyasi va EHF {diff_pct:.0%} ga farqlanadi",
        evidence={
            "vat_declared": str(vat_declared),
            "sum_seller_esf_vat": str(sum_seller_vat),
            "diff_pct": str(diff_pct),
            "period": [latest.period.start.isoformat(), latest.period.end.isoformat()],
        },
    )


def _is_complete(period: VatPeriodReport) -> bool:
    return period.vat_declared is not None and period.esf_seller_vat_total is not None
