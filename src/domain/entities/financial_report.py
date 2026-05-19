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

ADR-0024 (2026-05-19) добавил два cash-flow поля:
``depreciation_amortization`` — D&A для EBITDA (= profit_before_tax +
interest_expense + D&A); анонсирован в CA-037. ``operating_cash_flow`` —
числитель полноценного DSCR (Murodov O.J. 2025: cotton ginning DSCR≥1.3).
Оба nullable — FORM_2 / отчёт о движении денежных средств могут не
приходить вместе с другими формами.

ADR-0024 Session 2 (2026-05-19) добавил три off-balance-sheet поля для
правила OFF_BALANCE_COMMITMENTS (BCBS d424 §50 «Off-balance sheet items»):
``guarantees_outstanding`` — открытые банковские гарантии;
``leases_outstanding`` — лизинговые обязательства (операционные + финансовые);
``letters_of_credit_outstanding`` — открытые аккредитивы.
Все nullable — данные приходят через JSONB-загрузку (test fixtures /
future FORM_1 parser extension); UI manual-input их пока не вводит.
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
    # ADR-0024: компоненты EBITDA / DSCR / NEGATIVE_OCF_RULE backlog.
    depreciation_amortization: Money | None = None
    operating_cash_flow: Money | None = None
    # ADR-0024 Session 2: off-balance commitments для OFF_BALANCE_COMMITMENTS rule.
    guarantees_outstanding: Money | None = None
    leases_outstanding: Money | None = None
    letters_of_credit_outstanding: Money | None = None
    balance_end: BalanceSnapshot | None = None
    balance_start: BalanceSnapshot | None = None
