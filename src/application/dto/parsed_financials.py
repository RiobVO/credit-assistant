"""ParsedFinancials: agregating результат парсинга набора xltx/CSV-выгрузок.

Use case ``parse_manual_input_files`` берёт несколько файлов (FORM_2,
VAT_DECLARATION, ESF CSV, etc.), классифицирует каждый, парсит специализированным
парсером и сливает в один ``ParsedFinancials``. Frontend гидрирует форму Шага 2
manual-input wizard и помечает заполненные поля как read-only с подписью «из <источник>».

Best-effort семантика (CA-014): для нераспознанных или битых файлов — warning
в ``parse_warnings``; остальные файлы обрабатываются. Парсеры FORM_1/PROFIT_TAX
не реализованы (TODO[CA-029]) — их распознавание тоже падает в warning.

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

    ``taxes_paid_by_year`` / ``assets_total`` / ``liabilities_total`` — пока None,
    пока не написаны парсеры PROFIT_TAX/FORM_1 (TODO[CA-029]). Сохранены в DTO
    чтобы frontend мог не менять контракт после их появления.

    ``source_trail`` — field_name → human-readable source ("FORM_2 Q4 2025
    form2_q4_2025.xltx"). UI читает для chip-подписей под read-only fields.

    ``parse_warnings`` — best-effort cell-level и file-level замечания.
    """

    revenue_by_year: dict[int, Decimal] = field(default_factory=dict)
    net_profit_by_year: dict[int, Decimal] = field(default_factory=dict)
    vat_declared_by_year: dict[int, Decimal] = field(default_factory=dict)
    taxes_paid_by_year: dict[int, Decimal] = field(default_factory=dict)
    assets_total: Decimal | None = None
    liabilities_total: Decimal | None = None
    source_trail: dict[str, str] = field(default_factory=dict)
    parse_warnings: list[str] = field(default_factory=list)
