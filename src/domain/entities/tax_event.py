"""TaxEvent: оплата налога, пеня или блокировка счёта от Soliq."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from domain.value_objects.money import Money


class TaxEventType(StrEnum):
    PAYMENT = "payment"
    PENALTY = "penalty"
    ACCOUNT_FREEZE = "account_freeze"
    ACCOUNT_UNFREEZE = "account_unfreeze"


@dataclass(frozen=True, slots=True)
class TaxEvent:
    date: date
    type: TaxEventType
    amount: Money | None = None
    delay_days: int | None = None
    duration_days: int | None = None
