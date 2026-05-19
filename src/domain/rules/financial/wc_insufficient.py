"""WC_INSUFFICIENT: Working Capital < 0 ИЛИ Current Ratio < 1.0 (ADR-0024)."""

# RULE_SOURCE: IFC SME Knowledge Guide, chapter 4 «Liquidity & Working Capital»
#   (ifc.org/SME-toolkit). Current Ratio < 1.0 = краткосрочные обязательства
#   превышают текущие активы → дефицит ликвидности. Murodov O.J. 2025
#   также фиксирует WC<0 как leading default indicator в UZ-cotton.
# CONFIDENCE: HIGH (multilateral SME methodology)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

CURRENT_RATIO_MIN = Decimal("1.0")


def wc_insufficient(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    """Срабатывает когда current_ratio = current_assets / current_liabilities < 1.0.

    Эквивалентно условию Working Capital = current_assets - current_liabilities < 0
    (если current_liabilities > 0). Используем current_ratio как primary
    метрику — она дисциплинирует evidence в безразмерной форме и устойчива
    к outlier-абсолютам.

    * `annual_reports` пуст → None
    * `latest_annual.balance_end` пуст или нет current_assets/current_liabilities → None
      (FORM_1 best-effort — IFC чек не проводится без обеих компонент)
    * `current_liabilities ≤ 0` → None (нет краткосрочного долга — формально WC OK,
      но также защита от деления на ноль)
    * `current_ratio ≥ 1.0` → None
    * `current_ratio < 1.0` → fires

    Currency-агностично: сравниваем raw amounts. Currency mismatch внутри
    одного report — это инвариант парсера FORM_1, отдельная проверка не
    нужна.
    """
    if not snapshot.annual_reports:
        return None
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)
    if latest.balance_end is None:
        return None
    ca = latest.balance_end.current_assets
    cl = latest.balance_end.current_liabilities
    if ca is None or cl is None:
        return None
    if cl.amount <= Decimal(0):
        return None

    current_ratio = ca.amount / cl.amount
    if current_ratio >= CURRENT_RATIO_MIN:
        return None

    working_capital = ca.amount - cl.amount
    ratio_rounded = current_ratio.quantize(Decimal("0.01"))
    ratio_str = str(ratio_rounded).replace(".", ",")
    return FiringEvidence(
        message=(
            f"Current Ratio = {ratio_str} (норма ≥1,0) — краткосрочные "
            "обязательства превышают оборотные активы"
        ),
        message_uz=(
            f"Current Ratio = {ratio_str} (norma ≥1,0) — qisqa muddatli "
            "majburiyatlar joriy aktivlardan ortiq"
        ),
        evidence={
            "current_ratio": str(ratio_rounded),
            "working_capital": str(working_capital.quantize(Decimal("1"))),
            "current_assets": str(ca.amount),
            "current_liabilities": str(cl.amount),
            "year": str(latest.period.end.year),
        },
    )
