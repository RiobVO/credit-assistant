"""Use case: классифицировать пачку файлов → ParsedFinancials.

Принимает list[(filename, bytes)] из multipart-загрузки, прогоняет каждый через
``SoliqXltxAdapter.detect`` + специализированный парсер, собирает результаты
в ``ParsedFinancials``.

Best-effort семантика (CA-014):
* нераспознанный формат → warning, файл скипается;
* поддерживаемый формат с парсером (VAT_DECLARATION, FORM_2) → данные мерджатся,
  cell-level warnings от парсера агрегируются;
* поддерживаемый формат без парсера (FORM_1, PROFIT_TAX) → warning «парсер не
  реализован», файл скипается (TODO[CA-029]);
* file-level exception (битый xltx, openpyxl raise) → warning + skip, остальные
  файлы продолжают обработку.

Frontend гидрирует форму Step 2 и помечает поля read-only по ``source_trail``.

CA-027 scope (option b): только annual суммы. FORM_2 за Q4 → annual за текущий
и прошлый год (current_period = annual YTD, prior_year_period = annual прошлого
года). Файлы за Q1/Q2/Q3 (промежуточные YTD) пишут warning и не используются
в этой итерации — дельты будут отдельным TODO.

Конфликт источников: если два FORM_2-файла за один и тот же год покрывают
один и тот же показатель — побеждает первый (predictable). Между разными
формами конфликта быть не должно (FORM_2 даёт revenue, VAT — vat_declared).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from application.dto.parsed_financials import ParsedFinancials
from domain.value_objects.money import Money
from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
from infrastructure.adapters.soliq_xltx.form1_parser import Form1BalanceSheetData
from infrastructure.adapters.soliq_xltx.form2_parser import Form2IncomeStatementData
from infrastructure.adapters.soliq_xltx.format_detector import SoliqXltxFormat
from infrastructure.adapters.soliq_xltx.parser import SoliqXltxAdapter
from infrastructure.adapters.soliq_xltx.vat_declaration_parser import VatDeclarationData

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NamedFile:
    """Минимальное представление загруженного файла для use case."""

    name: str
    content: bytes


@dataclass(frozen=True, slots=True)
class ParseManualInputFilesUseCase:
    """Оркестратор multi-file парсинга для авто-фила формы Step 2.

    Зависит от ``SoliqXltxAdapter`` (detect + parse). ESF-CSV пока не подключён
    (CA-027 scope): для квартальной разбивки понадобится EsfCsvAdapter, но в
    option (b) фокус на годовых total из FORM_2.
    """

    adapter: SoliqXltxAdapter

    def execute(self, files: list[NamedFile]) -> ParsedFinancials:
        revenue_by_year: dict[int, Decimal] = {}
        net_profit_by_year: dict[int, Decimal] = {}
        vat_declared_by_year: dict[int, Decimal] = {}
        source_trail: dict[str, str] = {}
        warnings: list[str] = []

        for f in files:
            try:
                fmt = self.adapter.detect(f.content)
            except Exception as exc:
                warnings.append(f"{f.name}: не удалось открыть ({exc})")
                _logger.warning("parse_files.open_failed name=%s error=%s", f.name, exc)
                continue

            if fmt is SoliqXltxFormat.UNKNOWN:
                warnings.append(f"{f.name}: формат не распознан")
                continue

            try:
                parsed = self.adapter.parse(f.content)
            except UnsupportedFormatError as exc:
                # Adapter поднимает это для FORM_1 / PROFIT_TAX (CA-029)
                warnings.append(
                    f"{f.name}: формат {fmt.value} распознан, но парсер не реализован "
                    f"(см. TODO[CA-029])"
                )
                _logger.info("parse_files.unsupported name=%s fmt=%s reason=%s", f.name, fmt, exc)
                continue
            except Exception as exc:
                warnings.append(f"{f.name}: ошибка парсинга ({exc})")
                _logger.warning(
                    "parse_files.parse_failed name=%s fmt=%s error=%s", f.name, fmt, exc
                )
                continue

            if isinstance(parsed, Form2IncomeStatementData):
                _merge_form2(
                    parsed,
                    f.name,
                    revenue_by_year,
                    net_profit_by_year,
                    source_trail,
                    warnings,
                )
            elif isinstance(parsed, VatDeclarationData):
                _merge_vat_declaration(
                    parsed,
                    f.name,
                    vat_declared_by_year,
                    source_trail,
                    warnings,
                )
            elif isinstance(parsed, Form1BalanceSheetData):
                # FORM_1 парсер реализован (CA-029a), но wiring в form autofill
                # (assets/liabilities) — отдельный TODO. Эмитим явный warning,
                # чтобы фронт показал «загрузили, но не использовали».
                warnings.append(
                    f"{f.name}: FORM_1 распознан, парсер реализован, но "
                    f"автозаполнение полей активов/обязательств пока не подключено "
                    f"(см. TODO[CA-029] wiring)"
                )
            else:
                # VAT_REGISTRY_ILOVA — не несёт financials, тихо скипаем.
                continue

        return ParsedFinancials(
            revenue_by_year=revenue_by_year,
            net_profit_by_year=net_profit_by_year,
            vat_declared_by_year=vat_declared_by_year,
            taxes_paid_by_year={},
            assets_total=None,
            liabilities_total=None,
            source_trail=source_trail,
            parse_warnings=warnings,
        )


def _merge_form2(
    parsed: Form2IncomeStatementData,
    filename: str,
    revenue_by_year: dict[int, Decimal],
    net_profit_by_year: dict[int, Decimal],
    source_trail: dict[str, str],
    warnings: list[str],
) -> None:
    """Слить current_period + prior_year в annual maps. Только Q4 (option b)."""
    header = parsed.header
    year = header.period_year
    quarter = header.period_index
    if year is None:
        warnings.append(f"{filename}: FORM_2 без указания года в header")
        return
    if quarter is not None and quarter != 4:
        warnings.append(
            f"{filename}: FORM_2 за Q{quarter} {year} даёт YTD, "
            f"не годовой total — пропуск (полный год = Q4-файл)"
        )
        return

    label = f"FORM_2 Q4 {year} ({filename})"
    prior_label = f"FORM_2 Q4 {year} prior column ({filename})"

    if parsed.revenue_current_period is not None:
        _set_once(
            revenue_by_year, year, parsed.revenue_current_period,
            source_trail, "revenue", label, warnings,
        )
    if parsed.revenue_prior_year_period is not None:
        _set_once(
            revenue_by_year, year - 1, parsed.revenue_prior_year_period,
            source_trail, "revenue", prior_label, warnings,
        )
    if parsed.net_profit_current is not None:
        _set_once(
            net_profit_by_year, year, parsed.net_profit_current,
            source_trail, "net_profit", label, warnings,
        )
    if parsed.net_profit_prior_year is not None:
        _set_once(
            net_profit_by_year, year - 1, parsed.net_profit_prior_year,
            source_trail, "net_profit", prior_label, warnings,
        )

    # Прокидываем cell-level warnings парсера, если они есть.
    for w in parsed.parse_warnings:
        warnings.append(f"{filename}: {w}")


def _merge_vat_declaration(
    parsed: VatDeclarationData,
    filename: str,
    vat_declared_by_year: dict[int, Decimal],
    source_trail: dict[str, str],
    warnings: list[str],
) -> None:
    year = parsed.header.period_year
    if year is None:
        warnings.append(f"{filename}: VAT_DECLARATION без указания года")
        return
    if parsed.vat_charged_total is None:
        warnings.append(f"{filename}: VAT_DECLARATION — нет суммы НДС в G6")
        return
    label = f"VAT_DECLARATION {year} ({filename})"
    _set_once(
        vat_declared_by_year, year, parsed.vat_charged_total,
        source_trail, "vat_declared", label, warnings,
    )
    for w in parsed.parse_warnings:
        warnings.append(f"{filename}: {w}")


def _set_once(
    target: dict[int, Decimal],
    year: int,
    value: Money,
    source_trail: dict[str, str],
    field_name: str,
    source_label: str,
    warnings: list[str],
) -> None:
    """Положить amount в map[year], не перетирая. Конфликт → warning, побеждает первый."""
    if year in target:
        warnings.append(
            f"{source_label}: значение {field_name} за {year} уже было заполнено "
            f"из другого файла — оставляем первое"
        )
        return
    target[year] = value.amount
    source_trail[f"{field_name}_{year}"] = source_label
