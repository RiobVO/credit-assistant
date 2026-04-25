"""FinancialReport: финансовый отчёт за период (год/квартал/месяц).

``taxes_paid`` опциональный (CA-044): ``None`` = «пользователь не заполнил»
(в PDF будет «—», в БД — null), ``Money(0)`` = «осознанно ноль уплат»
(red-flag сигнал для будущих правил налоговой дисциплины). До CA-044 поле
было required и пустая строка из UI превращалась в ``Money(0)``, фабрикуя
факт «уплачено 0 сум» в выходном банковском документе.
"""

from dataclasses import dataclass

from domain.value_objects.date_range import DateRange
from domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class FinancialReport:
    period: DateRange
    revenue: Money
    net_profit: Money
    taxes_paid: Money | None = None
    vat_declared: Money | None = None
    assets: Money | None = None
    liabilities: Money | None = None
