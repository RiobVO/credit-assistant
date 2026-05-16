"""ParsedFinancials: agregating результат парсинга набора xltx/CSV-выгрузок.

Use case ``parse_manual_input_files`` берёт несколько файлов (FORM_2,
VAT_DECLARATION, ESF CSV, etc.), классифицирует каждый, парсит специализированным
парсером и сливает в один ``ParsedFinancials``. Frontend гидрирует форму Шага 2
manual-input wizard и помечает заполненные поля как read-only с подписью «из <источник>».

Best-effort семантика (CA-014): для нераспознанных или битых файлов — warning
в ``parse_warnings``; остальные файлы обрабатываются. Все 5 xltx-форматов
(VAT_DECLARATION, VAT_REGISTRY_ILOVA, FORM_2, FORM_1, PROFIT_TAX) подключены
через специализированные парсеры.

CA-027 scope (option b): только годовые суммы. Квартальная разбивка через
дельты YTD-периодов — отдельный TODO. Из Q4-FORM_2 файла парсер получает annual
за текущий и прошлый год (column F vs D).
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ParsedFinancials:
    """Агрегат финансовых полей, извлечённых из набора выгрузок.

    Все суммы — Decimal в UZS.

    ``revenue_by_year`` / ``net_profit_by_year`` — annual итого по годам
    (из FORM_2: F-column for current year, D-column for prior year при quarter=4).

    ``vat_declared_by_year`` — НДС начисленный за период (vat_charged_total из
    VAT_DECLARATION). Если файл — Q4 deklaratsiya, period_year полагается на header.

    ``taxes_paid_by_year`` — заполняется из PROFIT_TAX list01 L39 (код 080
    «Сумма налога на прибыль – всего», gross computed). Только Q4 (CA-027
    option b); quarterly skip с warning.

    ``assets_total`` / ``liabilities_total`` — Итого по активу/пассиву на
    конец отчётного периода (column E xltx — «На конец отчётного периода»).
    Заполняются FORM_1 wiring'ом (CA-041).

    ``assets_total_period_start`` / ``liabilities_total_period_start`` —
    те же показатели на начало периода (column D xltx). Frontend пока не
    использует, но нужны для будущего CA-037 (ROE с average_equity =
    (BoY+EoY)/2 — стандарт финансового анализа: усреднённый equity).

    ``source_trail`` — field_name → human-readable source ("FORM_2 Q4 2025
    form2_q4_2025.xltx"). UI читает для chip-подписей под read-only fields.
    FORM_1 ключи используют префикс ``form1.*`` — согласовано с CA-035
    ``assess_draft_readiness`` mapper'ом.

    ``parse_warnings`` — best-effort cell-level и file-level замечания.
    """

    revenue_by_year: dict[int, Decimal] = field(default_factory=dict)
    net_profit_by_year: dict[int, Decimal] = field(default_factory=dict)
    vat_declared_by_year: dict[int, Decimal] = field(default_factory=dict)
    taxes_paid_by_year: dict[int, Decimal] = field(default_factory=dict)
    # CA-037: income-statement расширения для EBIT-прокси
    # (EBIT = profit_before_tax + interest_expense, current+prior из FORM_2).
    profit_before_tax_by_year: dict[int, Decimal] = field(default_factory=dict)
    interest_expense_by_year: dict[int, Decimal] = field(default_factory=dict)
    assets_total: Decimal | None = None
    liabilities_total: Decimal | None = None
    assets_total_period_start: Decimal | None = None
    liabilities_total_period_start: Decimal | None = None
    # CA-037: balance-sheet расширения для ROE и Debt-to-EBIT.
    # equity_avg = (period_start + period_end) / 2 — стандарт финанализа.
    equity_period_end: Decimal | None = None
    equity_period_start: Decimal | None = None
    total_debt_period_end: Decimal | None = None
    total_debt_period_start: Decimal | None = None
    source_trail: dict[str, str] = field(default_factory=dict)
    parse_warnings: list[str] = field(default_factory=list)
