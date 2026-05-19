"""OFF_BALANCE_COMMITMENTS: off-balance commitments >50% активов (ADR-0024 Session 2)."""

# RULE_SOURCE: BCBS d424 «Basel III: Finalising post-crisis reforms» §50
#   «Off-balance sheet items» (bis.org/bcbs/publ/d424.pdf); внутренние методики
#   UZ-банков по портфельному risk weighting гарантий, лизинговых
#   обязательств и аккредитивов.
# CONFIDENCE: HIGH (Basel III regulatory standard)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

OFF_BALANCE_RATIO_THRESHOLD = Decimal("0.50")


def off_balance_commitments(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    """Срабатывает когда (guarantees + leases + LoC) / total_assets > 0.50.

    Off-balance-sheet commitments — обязательства, которые не отражены в
    балансе, но создают будущий cash-outflow при наступлении триггера
    (выплата по гарантии, экспирация аккредитива, лизинговый платёж).
    Когда их сумма превышает 50% балансовых активов — у заёмщика leveraged
    exposure, невидимый в традиционных Debt/Assets и Current Ratio.

    * `annual_reports` пуст → None.
    * у latest нет `balance_end` или `balance_end.assets` None → None
      (нет знаменателя — FORM_1 не загружен).
    * `total_assets ≤ 0` → None (деление на ≤0 не определено).
    * все 3 off-balance поля None → None (silent: данных нет, не сигнал).
    * `ratio ≤ 0.50` → None.
    * `ratio > 0.50` → fires.

    Partial data: считаем сумму как «None → 0», если хотя бы одно из трёх
    полей не None. Это worst-case-known оценка — банк увидит сигнал даже
    когда часть полей не загружена через manual-input.
    """
    if not snapshot.annual_reports:
        return None
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)
    if latest.balance_end is None or latest.balance_end.assets is None:
        return None
    assets = latest.balance_end.assets.amount
    if assets <= Decimal(0):
        return None

    guarantees = latest.guarantees_outstanding
    leases = latest.leases_outstanding
    letters_of_credit = latest.letters_of_credit_outstanding
    if guarantees is None and leases is None and letters_of_credit is None:
        return None

    total_off = (
        (guarantees.amount if guarantees is not None else Decimal(0))
        + (leases.amount if leases is not None else Decimal(0))
        + (letters_of_credit.amount if letters_of_credit is not None else Decimal(0))
    )
    ratio = total_off / assets
    if ratio <= OFF_BALANCE_RATIO_THRESHOLD:
        return None

    ratio_pct = (ratio * 100).quantize(Decimal("0.1"))
    return FiringEvidence(
        message=(
            f"Off-balance обязательства ({ratio_pct}% активов) превышают 50% "
            "балансовых активов — leveraged exposure вне баланса"
        ),
        message_uz=(
            f"Balansdan tashqari majburiyatlar ({ratio_pct}% aktivlar) balans "
            "aktivlarining 50% dan ortiq — balansdan tashqari yuqori levered tavakkalligi"
        ),
        evidence={
            "off_balance_total": str(total_off.quantize(Decimal("1"))),
            "total_assets": str(assets.quantize(Decimal("1"))),
            "ratio_pct": str(ratio_pct),
            "guarantees_outstanding": (
                str(guarantees.amount) if guarantees is not None else "null"
            ),
            "leases_outstanding": (
                str(leases.amount) if leases is not None else "null"
            ),
            "letters_of_credit_outstanding": (
                str(letters_of_credit.amount) if letters_of_credit is not None else "null"
            ),
            "year": str(latest.period.end.year),
        },
    )
