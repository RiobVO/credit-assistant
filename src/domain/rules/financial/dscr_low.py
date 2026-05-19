"""DSCR_LOW: Debt Service Coverage Ratio ниже минимума 1.3 (ADR-0024)."""

# RULE_SOURCE: Murodov O.J. (2025). «Хлопкоочистительные предприятия Узбекистана:
#   оценка кредитоспособности и пороги DSCR» // Tashkent State University of Economics.
#   Эмпирический минимум DSCR≥1.3 для МСБ-cotton ginning. Cross-reference:
#   Investopedia DSCR formula, IFC SME Knowledge Guide chapter 4 (DSCR≥1.25
#   minimum, ≥1.5 comfort).
# CONFIDENCE: HIGH (peer-reviewed UZ-specific research + multilateral cross-check)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

DSCR_MIN_THRESHOLD = Decimal("1.3")
MONTHS_IN_YEAR = Decimal("12")


def dscr_low(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    """Срабатывает когда DSCR = OCF / annual debt service < 1.3.

    Формула: DSCR = operating_cash_flow / (interest_expense + principal_annual)
    где principal_annual ≈ loan_amount × 12 / term_months — annualized
    principal repayment (linear approximation, без амортизационного графика).

    Условия силы fire:
    * есть loan_request (нечем считать debt service иначе)
    * есть latest_annual.operating_cash_flow (числитель)
    * есть latest_annual.interest_expense (часть знаменателя)
    * DSCR < 1.3

    Если OCF отсутствует — fallback на approx через EBITDA
    (`profit_before_tax + interest_expense + depreciation_amortization`), а если
    и D&A нет — на EBIT (`profit_before_tax + interest_expense`). Аналитик
    в evidence видит, какой числитель применили (`numerator_source`).

    `term_months <= 0` или `loan_amount <= 0` → None (некорректные данные —
    Pydantic уже валидирует, но guard на всякий случай).

    Currency-агностично: сравниваем числа в одной валюте, mismatch ловит
    FX_MISMATCH_HIGH.
    """
    loan = snapshot.loan_request
    if loan is None:
        return None
    if loan.term_months <= 0:
        return None
    loan_amount = loan.amount.amount
    if loan_amount <= Decimal(0):
        return None

    if not snapshot.annual_reports:
        return None
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)
    interest = latest.interest_expense
    if interest is None:
        return None

    # Числитель: OCF → EBITDA → EBIT (best-effort).
    numerator_source: str
    numerator: Decimal
    if latest.operating_cash_flow is not None:
        numerator = latest.operating_cash_flow.amount
        numerator_source = "OCF"
    elif latest.profit_before_tax is not None and latest.depreciation_amortization is not None:
        numerator = (
            latest.profit_before_tax.amount
            + interest.amount
            + latest.depreciation_amortization.amount
        )
        numerator_source = "EBITDA"
    elif latest.profit_before_tax is not None:
        numerator = latest.profit_before_tax.amount + interest.amount
        numerator_source = "EBIT"
    else:
        return None

    # Знаменатель: interest + annualized principal.
    principal_annual = loan_amount * MONTHS_IN_YEAR / Decimal(loan.term_months)
    debt_service = interest.amount + principal_annual
    if debt_service <= Decimal(0):
        return None

    dscr = numerator / debt_service
    if dscr >= DSCR_MIN_THRESHOLD:
        return None

    dscr_rounded = dscr.quantize(Decimal("0.01"))
    dscr_pct_str = str(dscr_rounded).replace(".", ",")
    return FiringEvidence(
        message=(
            f"DSCR = {dscr_pct_str} (минимум 1,3) при покрытии через "
            f"{numerator_source}; обслуживание долга не обеспечено"
        ),
        message_uz=(
            f"DSCR = {dscr_pct_str} (minimum 1,3), {numerator_source} "
            f"orqali qoplash; qarz xizmati taʼminlanmagan"
        ),
        evidence={
            "dscr": str(dscr_rounded),
            "numerator_source": numerator_source,
            "numerator": str(numerator.quantize(Decimal("1"))),
            "debt_service_annual": str(debt_service.quantize(Decimal("1"))),
            "interest_expense": str(interest.amount),
            "principal_annual_approx": str(principal_annual.quantize(Decimal("1"))),
        },
    )
