"""FinancialReport: финансовый отчёт за период (год/квартал/месяц)."""

from dataclasses import dataclass

from domain.value_objects.date_range import DateRange
from domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class FinancialReport:
    period: DateRange
    revenue: Money
    net_profit: Money
    taxes_paid: Money
    vat_declared: Money | None = None
    assets: Money | None = None
    liabilities: Money | None = None
