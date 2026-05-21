"""SINGLE_SUPPLIER_CONCENTRATION: концентрация закупок у одного поставщика.

ADR-0024 Session 3: dual-severity escalation.
- >0.50 закупок + поставщик иностранный → severity=HIGH (FATF R.10 CDD,
  foreign supplier risk + supply-chain currency/sanctions exposure).
- >0.60 закупок (domestic или unknown) → severity=MEDIUM (Basel III
  concentration risk baseline).
- ≤0.50 либо ≤0.60-без-foreign-флага → silent.

Severity high возвращается через `FiringEvidence.severity` override
поверх YAML severity=medium (Commit 0 infrastructure).
"""

# RULE_SOURCE: Basel III concentration risk; FATF Recommendation 10 (CDD —
# foreign-counterparty enhanced due diligence); supply-chain risk practice
# CONFIDENCE: HIGH (regulatory + industry-standard)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.rules.protocol import FiringEvidence
from domain.value_objects.flag_severity import FlagSeverity

THRESHOLD_FOREIGN_HIGH = Decimal("0.50")
THRESHOLD_DOMESTIC_MEDIUM = Decimal("0.60")


def single_supplier_concentration(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    if not snapshot.supplier_purchase_share:
        return None
    max_inn, max_share = max(snapshot.supplier_purchase_share.items(), key=lambda x: x[1])

    # Lookup is_foreign по INN — линейный поиск, поставщиков обычно <100.
    max_supplier: Counterparty | None = next(
        (cp for cp in snapshot.counterparties_suppliers if cp.inn.value == max_inn),
        None,
    )
    is_foreign = max_supplier.is_foreign if max_supplier is not None else False

    if is_foreign and max_share > THRESHOLD_FOREIGN_HIGH:
        return FiringEvidence(
            message=(
                f"Иностранный поставщик = {max_share:.0%} закупок "
                f"(>50%, повышенный риск supply-chain)"
            ),
            message_uz=(
                f"Chet ellik yetkazib beruvchi = xaridlarning {max_share:.0%} "
                f"(50% dan ortiq, supply-chain tavakkalligi)"
            ),
            evidence={
                "max_supplier_inn": max_inn,
                "max_supplier_share": str(max_share),
                "max_supplier_is_foreign": True,
            },
            severity=FlagSeverity.HIGH,
        )
    if max_share > THRESHOLD_DOMESTIC_MEDIUM:
        return FiringEvidence(
            message=f"Один поставщик = {max_share:.0%} закупок",
            message_uz=f"Bitta yetkazib beruvchi = xaridlarning {max_share:.0%}",
            evidence={
                "max_supplier_inn": max_inn,
                "max_supplier_share": str(max_share),
                "max_supplier_is_foreign": is_foreign,
            },
        )
    return None
