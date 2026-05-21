"""LoanRequest: запрашиваемая сумма + параметры кредита.

Заменяет одиночное поле `BorrowerSnapshot.loan_request_amount` на полный VO,
чтобы будущие правила (DSCR, rate-vs-market) могли использовать срок и ставку
без дополнительных DTO. Поля purpose/category — строки, потому что справочник
банков отличается; нормализацию в enum отложим до унификации с первым банком.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from domain.value_objects.money import Money

# ADR-0024 Session 3: secured-variant порог 0.70 для LOAN_TO_REVENUE_RATIO.
# 'none' = unsecured (порог 0.40), остальные = secured (порог 0.70). None в
# самом поле — для legacy / data sources без явного collateral_type.
CollateralType = Literal["none", "real_estate", "movable", "guarantee", "other"]


class InvalidLoanRequestError(ValueError):
    """Параметры запроса вне допустимых границ."""


@dataclass(frozen=True, slots=True)
class LoanRequest:
    amount: Money
    term_months: int
    rate_pct: Decimal  # годовая ставка в процентах, напр. 24.5
    purpose: str
    category: str
    # ADR-0024 Session 3: тип обеспечения для secured-variant порога
    # LOAN_TO_REVENUE_RATIO. None = legacy data (трактуется conservatively
    # как unsecured, порог 0.40). 'none' = явно без обеспечения. Любой
    # secured-вариант (real_estate / movable / guarantee / other) поднимает
    # порог до 0.70.
    collateral_type: CollateralType | None = None

    def __post_init__(self) -> None:
        if self.term_months <= 0:
            raise InvalidLoanRequestError(
                f"term_months must be positive, got {self.term_months}",
            )
        if self.rate_pct < 0:
            raise InvalidLoanRequestError(
                f"rate_pct cannot be negative, got {self.rate_pct}",
            )
