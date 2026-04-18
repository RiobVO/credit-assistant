"""VAT_ESF_MISMATCH: разрыв декларация НДС vs агрегат НДС из ЭСФ как продавец >15%."""

# RULE_SOURCE: НК РУз ст. 256; Soliq внутренние методики
# CONFIDENCE: HIGH (regulatory + tax authority practice)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

THRESHOLD = Decimal("0.15")


def vat_esf_mismatch(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    # Агрегат НДС из ЭСФ заполняет отдельный VAT-адаптер (см. ADR 0004).
    # CSV-выгрузка e-factura.uz его не содержит — правило молчит (degraded).
    if snapshot.esf_seller_vat_total is None:
        return None

    annual_with_vat = [r for r in snapshot.annual_reports if r.vat_declared is not None]
    if not annual_with_vat:
        return None
    latest = max(annual_with_vat, key=lambda r: r.period.end)
    assert latest.vat_declared is not None  # mypy narrowing

    vat_declared = latest.vat_declared.amount
    if vat_declared <= 0:
        return None

    sum_seller_vat = snapshot.esf_seller_vat_total.amount

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
