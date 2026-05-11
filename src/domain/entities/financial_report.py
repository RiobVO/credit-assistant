"""FinancialReport: финансовый отчёт за период (год/квартал/месяц).

``taxes_paid`` опциональный (CA-044): ``None`` = «пользователь не заполнил»
(в PDF будет «—», в БД — null), ``Money(0)`` = «осознанно ноль уплат»
(red-flag сигнал для будущих правил налоговой дисциплины). До CA-044 поле
было required и пустая строка из UI превращалась в ``Money(0)``, фабрикуя
факт «уплачено 0 сум» в выходном банковском документе.

CA-037 расширил entity 8 nullable полями для KPI EBIT/ROE/Debt-to-EBIT:
``profit_before_tax`` + ``interest_expense`` (income statement, EBIT proxy),
``equity`` + ``total_debt`` (balance period_end, components ROE/Debt-to-EBIT),
``*_period_start`` × 4 (balance на начало того же периода — FORM_1 даёт обе
колонки; используется в ROE для equity_avg = (start+end)/2). Plain-flat вместо
``BalanceSnapshot`` sub-entity для минимального blast radius CA-037; рефактор
в sub-entity — TODO[CA-XXX].
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
    profit_before_tax: Money | None = None
    interest_expense: Money | None = None
    equity: Money | None = None
    total_debt: Money | None = None
    assets_period_start: Money | None = None
    liabilities_period_start: Money | None = None
    equity_period_start: Money | None = None
    total_debt_period_start: Money | None = None
