"""MonthlyTurnover: помесячная выручка + НДС-обязательства."""

from dataclasses import dataclass
from datetime import date

from domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class MonthlyTurnover:
    month_start: date
    revenue: Money
    vat_obligations: Money | None = None

    def __post_init__(self) -> None:
        if self.month_start.day != 1:
            raise ValueError(
                f"month_start must be the first day of the month, got {self.month_start}",
            )
