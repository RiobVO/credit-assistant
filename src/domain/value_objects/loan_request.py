"""LoanRequest: запрашиваемая сумма + параметры кредита.

Заменяет одиночное поле `BorrowerSnapshot.loan_request_amount` на полный VO,
чтобы будущие правила (DSCR, rate-vs-market) могли использовать срок и ставку
без дополнительных DTO. Поля purpose/category — строки, потому что справочник
банков отличается; нормализацию в enum отложим до унификации с первым банком.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from domain.value_objects.money import Money


class InvalidLoanRequestError(ValueError):
    """Параметры запроса вне допустимых границ."""


@dataclass(frozen=True, slots=True)
class LoanRequest:
    amount: Money
    term_months: int
    rate_pct: Decimal  # годовая ставка в процентах, напр. 24.5
    purpose: str
    category: str

    def __post_init__(self) -> None:
        if self.term_months <= 0:
            raise InvalidLoanRequestError(
                f"term_months must be positive, got {self.term_months}",
            )
        if self.rate_pct < 0:
            raise InvalidLoanRequestError(
                f"rate_pct cannot be negative, got {self.rate_pct}",
            )
