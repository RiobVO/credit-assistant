"""Money: Decimal-precision сумма + Currency. Никаких float."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Currency(StrEnum):
    UZS = "UZS"
    USD = "USD"


class IncompatibleCurrencyError(ValueError):
    """Попытка операции между Money разной валюты."""


@dataclass(frozen=True, slots=True, init=False)
class Money:
    amount: Decimal
    currency: Currency

    def __init__(self, amount: Decimal | int | str, currency: Currency) -> None:
        if isinstance(amount, float):
            raise TypeError("Money amount cannot be float (precision loss)")
        decimal_amount = amount if isinstance(amount, Decimal) else Decimal(amount)
        object.__setattr__(self, "amount", decimal_amount)
        object.__setattr__(self, "currency", currency)

    def _ensure_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise IncompatibleCurrencyError(
                f"cannot mix {self.currency.value} and {other.currency.value}",
            )

    def __add__(self, other: "Money") -> "Money":
        self._ensure_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._ensure_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: int | Decimal) -> "Money":
        if isinstance(factor, float):
            raise TypeError("multiplier cannot be float")
        scalar = factor if isinstance(factor, Decimal) else Decimal(factor)
        return Money(self.amount * scalar, self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._ensure_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._ensure_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        self._ensure_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        self._ensure_same_currency(other)
        return self.amount >= other.amount
