"""Use case: классифицировать пачку файлов → ParsedFinancials.

Принимает list[(filename, bytes)] из multipart-загрузки, прогоняет каждый через
``SoliqXltxAdapter.detect`` + специализированный парсер, собирает результаты
в ``ParsedFinancials``.

Best-effort семантика (CA-014):
* нераспознанный формат → warning, файл скипается;
* поддерживаемый формат с парсером (VAT_DECLARATION, FORM_2, FORM_1) — данные
  мерджатся, cell-level warnings от парсера агрегируются;
* поддерживаемый формат без парсера (PROFIT_TAX) → warning «парсер не
  реализован», файл скипается (TODO[CA-029b]);
* file-level exception (битый xltx, openpyxl raise) → warning + skip, остальные
  файлы продолжают обработку.

Frontend гидрирует форму Step 2 и помечает поля read-only по ``source_trail``.

CA-027 scope (option b): только annual суммы. FORM_2 за Q4 → annual за текущий
и прошлый год (current_period = annual YTD, prior_year_period = annual прошлого
года). Файлы за Q1/Q2/Q3 (промежуточные YTD) пишут warning и не используются
в этой итерации — дельты будут отдельным TODO.

Конфликт источников:
* FORM_2 / VAT_DECLARATION — first wins per year (TODO[CA-042] заменит на
  latest-period priority);
* FORM_1 (CA-041) — latest-period wins: balance sheet это срез на дату,
  для autofill «текущее состояние заёмщика» свежий снимок authoritative.
  Snapshot-целиком: победивший файл даёт все 4 поля; не дополняем None'ы из
  старых. Тот же (year, quarter) → first wins + conflict warning.
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
        # FORM_1 dispatch — latest-period wins (см. модульный docstring).
        # Откладываем merge до конца цикла: храним кандидат + (year, quarter).
        form1_winner: _Form1Candidate | None = None

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
                form1_winner = _consider_form1(
                    parsed, f.name, form1_winner, warnings,
                )
            else:
                # VAT_REGISTRY_ILOVA — не несёт financials, тихо скипаем.
                continue

        assets_end: Decimal | None = None
        liab_end: Decimal | None = None
        assets_start: Decimal | None = None
        liab_start: Decimal | None = None
        if form1_winner is not None:
            assets_end, liab_end, assets_start, liab_start = _apply_form1(
                form1_winner, source_trail, warnings,
            )

        return ParsedFinancials(
            revenue_by_year=revenue_by_year,
            net_profit_by_year=net_profit_by_year,
            vat_declared_by_year=vat_declared_by_year,
            taxes_paid_by_year={},
            assets_total=assets_end,
            liabilities_total=liab_end,
            assets_total_period_start=assets_start,
            liabilities_total_period_start=liab_start,
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


@dataclass(frozen=True, slots=True)
class _Form1Candidate:
    """Победитель в гонке latest-period для FORM_1. Snapshot-целиком."""

    parsed: Form1BalanceSheetData
    filename: str
    period: tuple[int, int]  # (year, quarter); неизвестные значения → (-1, 0)


def _form1_period_key(parsed: Form1BalanceSheetData) -> tuple[int, int]:
    """(year, quarter) для сравнения свежести снимка. None → минимум.

    None'ы возможны при битой шапке xltx; они проигрывают любому файлу с
    распознанным периодом. При равенстве (включая «оба None») победитель
    выбирается first-wins выше.
    """
    year = parsed.header.period_year if parsed.header.period_year is not None else -1
    quarter = parsed.header.period_index if parsed.header.period_index is not None else 0
    return year, quarter


def _consider_form1(
    parsed: Form1BalanceSheetData,
    filename: str,
    current: _Form1Candidate | None,
    warnings: list[str],
) -> _Form1Candidate:
    """Latest-period dispatch. Возвращает обновлённого победителя.

    Свежий снимок (большее (year, quarter)) вытесняет старого без warning —
    это ожидаемое поведение для balance sheet. Если периоды равны — first wins
    + warning (дубликат отчёта). Если новый старее — игнор + warning «пропуск
    более старого среза».
    """
    new_period = _form1_period_key(parsed)
    candidate = _Form1Candidate(parsed=parsed, filename=filename, period=new_period)
    if current is None:
        return candidate

    if new_period > current.period:
        return candidate
    if new_period == current.period:
        warnings.append(
            f"{filename}: FORM_1 за тот же период {new_period[0]} Q{new_period[1]} "
            f"уже был загружен ({current.filename}) — оставляем первый"
        )
        return current
    # new_period < current.period: старее → пропуск
    warnings.append(
        f"{filename}: FORM_1 за {new_period[0]} Q{new_period[1]} старее "
        f"свежего снимка {current.period[0]} Q{current.period[1]} — пропуск"
    )
    return current


def _apply_form1(
    winner: _Form1Candidate,
    source_trail: dict[str, str],
    warnings: list[str],
) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
    """Развернуть победителя в (assets_end, liab_end, assets_start, liab_start).

    Source_trail обогащается ключами ``form1.*`` — согласовано с CA-035
    ``assess_draft_readiness`` префикс-mapper'ом. Cell-level warnings парсера
    прокидываются с указанием filename.
    """
    parsed = winner.parsed
    label = _form1_label(parsed, winner.filename)

    assets_end = _money_amount(parsed.total_assets_period_end)
    liab_end = _money_amount(parsed.total_liabilities_period_end)
    assets_start = _money_amount(parsed.total_assets_period_start)
    liab_start = _money_amount(parsed.total_liabilities_period_start)

    if assets_end is not None:
        source_trail["form1.assets_total"] = label
    if liab_end is not None:
        source_trail["form1.liabilities_total"] = label
    if assets_start is not None:
        source_trail["form1.assets_total_period_start"] = label
    if liab_start is not None:
        source_trail["form1.liabilities_total_period_start"] = label

    for w in parsed.parse_warnings:
        warnings.append(f"{winner.filename}: {w}")

    return assets_end, liab_end, assets_start, liab_start


def _form1_label(parsed: Form1BalanceSheetData, filename: str) -> str:
    year = parsed.header.period_year
    quarter = parsed.header.period_index
    if year is not None and quarter is not None:
        return f"FORM_1 Q{quarter} {year} ({filename})"
    if year is not None:
        return f"FORM_1 {year} ({filename})"
    return f"FORM_1 ({filename})"


def _money_amount(value: Money | None) -> Decimal | None:
    return value.amount if value is not None else None
