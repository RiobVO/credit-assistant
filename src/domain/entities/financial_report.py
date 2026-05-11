"""FinancialReport: финансовый отчёт за период (год/квартал/месяц).

``taxes_paid`` опциональный (CA-044): ``None`` = «пользователь не заполнил»
(в PDF будет «—», в БД — null), ``Money(0)`` = «осознанно ноль уплат»
(red-flag сигнал для будущих правил налоговой дисциплины). До CA-044 поле
было required и пустая строка из UI превращалась в ``Money(0)``, фабрикуя
факт «уплачено 0 сум» в выходном банковском документе.

CA-037 расширил entity полями для KPI EBIT/ROE/Debt-to-EBIT:
``profit_before_tax`` + ``interest_expense`` (income statement, EBIT proxy),
плюс балансовые показатели (FORM_1) на period_end и period_start —
компоненты ROE (equity_avg) и Debt-to-EBIT.

CA-047 сгруппировал балансовые поля в ``BalanceSnapshot`` sub-entity
(``balance_end`` + ``balance_start``). До CA-047 это были 8 flat полей
(`assets/liabilities/equity/total_debt × period_end + period_start`) —
accepted tradeoff в CA-037 ради минимального blast radius. Теперь читатели
обращаются как ``latest.balance_end.equity``, mapper-ы один раз сериализуют
snapshot вместо 8 повторов.
"""

from dataclasses import dataclass

from domain.value_objects.balance_snapshot import BalanceSnapshot
from domain.value_objects.date_range import DateRange
from domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class FinancialReport:
    period: DateRange
    revenue: Money
    net_profit: Money
    taxes_paid: Money | None = None
    vat_declared: Money | None = None
    profit_before_tax: Money | None = None
    interest_expense: Money | None = None
    balance_end: BalanceSnapshot | None = None
    balance_start: BalanceSnapshot | None = None
