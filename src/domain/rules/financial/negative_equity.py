"""NEGATIVE_EQUITY: отрицательный или нулевой собственный капитал (CA-049)."""

# RULE_SOURCE: Базель III IRB (capital adequacy); внутренние методики банков-партнёров
# CONFIDENCE: HIGH (regulatory)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence


def negative_equity(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    """Срабатывает когда `latest_annual.equity ≤ 0`.

    * `annual_reports` пуст → None (нет данных, не red flag).
    * latest annual.`equity is None` → None (FORM_1 не загружен).
    * `equity ≤ 0` → fires (boundary inclusive: technical insolvency на грани
      — банк хочет видеть строго positive equity). Симметрично NEGATIVE_PROFIT_3Q.

    ROE-карточка при `equity_avg ≤ 0` возвращает None (математически не
    определена); это правило даёт явный финансовый сигнал в Разделе F досье.
    """
    if not snapshot.annual_reports:
        return None
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)
    if latest.equity is None:
        return None
    equity = latest.equity.amount
    if equity > Decimal(0):
        return None
    # CA-021: округляем evidence до 2 знаков — Decimal-хвост ломает PDF/UI.
    return FiringEvidence(
        message="Отрицательный или нулевой собственный капитал в последнем годовом отчёте",
        evidence={
            "equity": str(equity.quantize(Decimal("0.01"))),
            "year": str(latest.period.end.year),
        },
    )
