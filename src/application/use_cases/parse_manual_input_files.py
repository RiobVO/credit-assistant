"""Use case: классифицировать пачку файлов → ParsedFinancials.

Принимает list[(filename, bytes)] из multipart-загрузки, прогоняет каждый через
``SoliqXltxAdapter.detect`` + специализированный парсер, собирает результаты
в ``ParsedFinancials``.

Best-effort семантика (CA-014):
* нераспознанный формат → warning, файл скипается;
* поддерживаемый формат (VAT_DECLARATION, VAT_REGISTRY_ILOVA, FORM_2, FORM_1,
  PROFIT_TAX) — данные мерджатся, cell-level warnings от парсера агрегируются;
* UnsupportedFormatError (теоретически — если в будущем появится новый формат
  без парсера) → warning + skip, остальные файлы продолжают обработку;
* file-level exception (битый xltx, openpyxl raise) → warning + skip.

Frontend гидрирует форму Step 2 и помечает поля read-only по ``source_trail``.

CA-027 scope (option b): только annual суммы. FORM_2 за Q4 → annual за текущий
и прошлый год (current_period = annual YTD, prior_year_period = annual прошлого
года). Файлы за Q1/Q2/Q3 (промежуточные YTD) пишут warning и не используются
в этой итерации — дельты будут отдельным TODO.

Конфликт источников:
* FORM_2 (CA-042) — tier priority per (field, year): `header.period_year == Y`
  даёт **current column** для года Y (authoritative, закрытый отчёт);
  `header.period_year == Y + 1` даёт **prior column** для года Y
  (колонка-сравнение). CURRENT silently перезаписывает PRIOR; same-tier
  конфликт → first wins + warning. Реализация через `_Form2SourceTier`
  IntEnum + локальный `tier_by_field_year` map в `execute`.
* VAT_DECLARATION — first wins per year (`_set_once`).
* FORM_1 (CA-041) — latest-period wins: balance sheet это срез на дату,
  для autofill «текущее состояние заёмщика» свежий снимок authoritative.
  Snapshot-целиком: победивший файл даёт все 4 поля; не дополняем None'ы из
  старых. Тот же (year, quarter) → first wins + conflict warning.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import IntEnum

from application.dto.parsed_financials import ParsedFinancials
from domain.value_objects.money import Money
from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
from infrastructure.adapters.soliq_xltx.form1_parser import Form1BalanceSheetData
from infrastructure.adapters.soliq_xltx.form2_parser import Form2IncomeStatementData
from infrastructure.adapters.soliq_xltx.format_detector import SoliqXltxFormat
from infrastructure.adapters.soliq_xltx.parser import SoliqXltxAdapter
from infrastructure.adapters.soliq_xltx.profit_tax_parser import ProfitTaxData
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
        # CA-037: income-statement расширения для EBIT-прокси.
        profit_before_tax_by_year: dict[int, Decimal] = {}
        interest_expense_by_year: dict[int, Decimal] = {}
        source_trail: dict[str, str] = {}
        warnings: list[str] = []
        # T2.3: taxes_paid_by_year заполняется только из PROFIT_TAX (L39).
        # Инициализируем явно — раньше это был hardcoded `{}` в return.
        taxes_paid_by_year: dict[int, Decimal] = {}
        # FORM_1 dispatch — latest-period wins (см. модульный docstring).
        # Откладываем merge до конца цикла: храним кандидат + (year, quarter).
        form1_winner: _Form1Candidate | None = None
        # CA-042: tier бухгалтерия для FORM_2 dispatch'а — CURRENT > PRIOR
        # per (field_name, year). Локально к execute, расходный после return.
        tier_by_field_year: dict[tuple[str, int], _Form2SourceTier] = {}

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
                # T3.3: counter cell-level warnings per format. Inc по
                # количеству warnings, label = lower-case format name
                # (vat_declaration / form_2 / ...). Spike signal на
                # регрессию layout Soliq.
                if parsed.parse_warnings:
                    from infrastructure.observability.metrics import (
                        parser_warnings_total,
                    )

                    parser_warnings_total.labels(format=fmt.value).inc(
                        len(parsed.parse_warnings)
                    )
            except UnsupportedFormatError as exc:
                # Reachable теоретически если detect_format вернёт новый формат
                # без соответствующего парсера (все 5 поддержаны: VAT_DECLARATION,
                # VAT_REGISTRY_ILOVA, FORM_2, FORM_1, PROFIT_TAX).
                warnings.append(
                    f"{f.name}: формат {fmt.value} распознан, но парсер не реализован"
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
                    profit_before_tax_by_year,
                    interest_expense_by_year,
                    source_trail,
                    warnings,
                    tier_by_field_year,
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
            elif isinstance(parsed, ProfitTaxData):
                _merge_profit_tax(
                    parsed, f.name, taxes_paid_by_year, source_trail, warnings,
                )
            else:
                # VAT_REGISTRY_ILOVA — не несёт financials, тихо скипаем.
                continue

        form1_unpack = _Form1Unpacked()
        if form1_winner is not None:
            form1_unpack = _apply_form1(form1_winner, source_trail, warnings)

        return ParsedFinancials(
            revenue_by_year=revenue_by_year,
            net_profit_by_year=net_profit_by_year,
            vat_declared_by_year=vat_declared_by_year,
            taxes_paid_by_year=taxes_paid_by_year,
            profit_before_tax_by_year=profit_before_tax_by_year,
            interest_expense_by_year=interest_expense_by_year,
            assets_total=form1_unpack.assets_end,
            liabilities_total=form1_unpack.liabilities_end,
            assets_total_period_start=form1_unpack.assets_start,
            liabilities_total_period_start=form1_unpack.liabilities_start,
            equity_period_end=form1_unpack.equity_end,
            equity_period_start=form1_unpack.equity_start,
            total_debt_period_end=form1_unpack.total_debt_end,
            total_debt_period_start=form1_unpack.total_debt_start,
            source_trail=source_trail,
            parse_warnings=warnings,
        )


def _merge_form2(
    parsed: Form2IncomeStatementData,
    filename: str,
    revenue_by_year: dict[int, Decimal],
    net_profit_by_year: dict[int, Decimal],
    profit_before_tax_by_year: dict[int, Decimal],
    interest_expense_by_year: dict[int, Decimal],
    source_trail: dict[str, str],
    warnings: list[str],
    tier_by_field_year: dict[tuple[str, int], _Form2SourceTier],
) -> None:
    """Слить current_period + prior_year в annual maps. Только Q4 (option b).

    CA-037: дополнительно мерджит profit_before_tax / interest_expense из тех
    же двух колонок (current/prior) — компоненты EBIT-прокси.

    CA-042: tier priority через `_set_with_tier_priority`. CURRENT (current
    column данного года) перебивает PRIOR (prior column из FORM_2 следующего
    года) silent; same-tier дубликат → first wins + warning.
    """
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
        _set_with_tier_priority(
            revenue_by_year, year, parsed.revenue_current_period,
            _Form2SourceTier.CURRENT,
            source_trail, "revenue", label, warnings, tier_by_field_year,
        )
    if parsed.revenue_prior_year_period is not None:
        _set_with_tier_priority(
            revenue_by_year, year - 1, parsed.revenue_prior_year_period,
            _Form2SourceTier.PRIOR,
            source_trail, "revenue", prior_label, warnings, tier_by_field_year,
        )
    if parsed.net_profit_current is not None:
        _set_with_tier_priority(
            net_profit_by_year, year, parsed.net_profit_current,
            _Form2SourceTier.CURRENT,
            source_trail, "net_profit", label, warnings, tier_by_field_year,
        )
    if parsed.net_profit_prior_year is not None:
        _set_with_tier_priority(
            net_profit_by_year, year - 1, parsed.net_profit_prior_year,
            _Form2SourceTier.PRIOR,
            source_trail, "net_profit", prior_label, warnings, tier_by_field_year,
        )
    # CA-037: PBT и interest expense — обе колонки, поведение совпадает с revenue.
    if parsed.profit_before_tax_current is not None:
        _set_with_tier_priority(
            profit_before_tax_by_year, year, parsed.profit_before_tax_current,
            _Form2SourceTier.CURRENT,
            source_trail, "profit_before_tax", label, warnings, tier_by_field_year,
        )
    if parsed.profit_before_tax_prior_year is not None:
        _set_with_tier_priority(
            profit_before_tax_by_year, year - 1, parsed.profit_before_tax_prior_year,
            _Form2SourceTier.PRIOR,
            source_trail, "profit_before_tax", prior_label, warnings, tier_by_field_year,
        )
    if parsed.interest_expense_current is not None:
        _set_with_tier_priority(
            interest_expense_by_year, year, parsed.interest_expense_current,
            _Form2SourceTier.CURRENT,
            source_trail, "interest_expense", label, warnings, tier_by_field_year,
        )
    if parsed.interest_expense_prior_year is not None:
        _set_with_tier_priority(
            interest_expense_by_year, year - 1, parsed.interest_expense_prior_year,
            _Form2SourceTier.PRIOR,
            source_trail, "interest_expense", prior_label, warnings, tier_by_field_year,
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


def _merge_profit_tax(
    parsed: ProfitTaxData,
    filename: str,
    taxes_paid_by_year: dict[int, Decimal],
    source_trail: dict[str, str],
    warnings: list[str],
) -> None:
    """T2.3: PROFIT_TAX Q4 → taxes_paid_by_year[year] из L39 (gross computed).

    Семантика (mirror FORM_2 CA-027 option b):
    * year отсутствует в header → warning + return.
    * Quarterly (period_index != 4 и не None) → warning «промежуточный YTD,
      не годовой total — пропуск», `taxes_paid_by_year` не трогается.
    * profit_tax_total пуст → warning «нет суммы налога в L39».
    * Single source per year — `_set_once` (FORM_2 G30 в use-case не мерджится,
      PROFIT_TAX единственный writer). Конфликт → first wins + warning.
    """
    header = parsed.header
    year = header.period_year
    quarter = header.period_index
    if year is None:
        warnings.append(f"{filename}: PROFIT_TAX без указания года в header")
        return
    if quarter is not None and quarter != 4:
        warnings.append(
            f"{filename}: PROFIT_TAX за Q{quarter} {year} даёт промежуточный YTD, "
            f"не годовой total — пропуск (полный год = Q4-файл)"
        )
        return
    if parsed.profit_tax_total is None:
        warnings.append(
            f"{filename}: PROFIT_TAX за {year} — нет суммы налога в L39 (код 080)"
        )
        return

    label = f"PROFIT_TAX {year} ({filename})"
    _set_once(
        taxes_paid_by_year, year, parsed.profit_tax_total,
        source_trail, "taxes_paid", label, warnings,
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


class _Form2SourceTier(IntEnum):
    """CA-042: иерархия источников значения per (field, year) для FORM_2.

    ``CURRENT`` — `header.period_year == year` (закрытый отчётный год,
    authoritative). ``PRIOR`` — `header.period_year == year + 1`
    (колонка-сравнение в FORM_2 следующего года). CURRENT > PRIOR.
    """

    PRIOR = 0
    CURRENT = 1


def _set_with_tier_priority(
    target: dict[int, Decimal],
    year: int,
    value: Money,
    new_tier: _Form2SourceTier,
    source_trail: dict[str, str],
    field_name: str,
    source_label: str,
    warnings: list[str],
    tier_by_field_year: dict[tuple[str, int], _Form2SourceTier],
) -> None:
    """CA-042: положить amount в map[year] с учётом tier-приоритета.

    * key отсутствует → set + record tier.
    * new_tier > stored_tier → перезаписать silent (CURRENT перебивает PRIOR;
      согласовано с CA-041 latest_period_wins_silently — иерархия известна,
      warning размывал бы важные сигналы).
    * new_tier == stored_tier → first wins + warning (same-tier дубликат).
    * new_tier < stored_tier → silent skip (PRIOR после CURRENT — нормальная
      иерархия, не информативное сообщение для аналитика).
    """
    key = (field_name, year)
    stored_tier = tier_by_field_year.get(key)
    if stored_tier is None:
        target[year] = value.amount
        source_trail[f"{field_name}_{year}"] = source_label
        tier_by_field_year[key] = new_tier
        return
    if new_tier > stored_tier:
        target[year] = value.amount
        source_trail[f"{field_name}_{year}"] = source_label
        tier_by_field_year[key] = new_tier
        return
    if new_tier == stored_tier:
        warnings.append(
            f"{source_label}: значение {field_name} за {year} уже было заполнено "
            f"из другого файла того же приоритета — оставляем первое"
        )
        return
    # new_tier < stored_tier — silent skip.
    return


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


@dataclass(slots=True)
class _Form1Unpacked:
    """Развёрнутый FORM_1-победитель: balance values + period_start снимки.

    Default-фабрика (все None) используется когда FORM_1 не пришёл —
    исполняемый код выше не разветвляется лишний раз.
    """

    assets_end: Decimal | None = None
    liabilities_end: Decimal | None = None
    assets_start: Decimal | None = None
    liabilities_start: Decimal | None = None
    # CA-037 расширения.
    equity_end: Decimal | None = None
    equity_start: Decimal | None = None
    total_debt_end: Decimal | None = None
    total_debt_start: Decimal | None = None


def _apply_form1(
    winner: _Form1Candidate,
    source_trail: dict[str, str],
    warnings: list[str],
) -> _Form1Unpacked:
    """Развернуть победителя в snapshot-целиком (assets/liab/equity/total_debt
    × period_end + period_start).

    Source_trail обогащается ключами ``form1.*`` — согласовано с CA-035
    ``assess_draft_readiness`` префикс-mapper'ом. Cell-level warnings парсера
    прокидываются с указанием filename.

    CA-037: добавлены equity_period_end/start, total_debt_period_end/start.
    Все 8 полей независимо None-aware — частичный FORM_1 (битые ячейки) даёт
    частичное заполнение, не all-or-nothing.
    """
    parsed = winner.parsed
    label = _form1_label(parsed, winner.filename)

    out = _Form1Unpacked(
        assets_end=_money_amount(parsed.total_assets_period_end),
        liabilities_end=_money_amount(parsed.total_liabilities_period_end),
        assets_start=_money_amount(parsed.total_assets_period_start),
        liabilities_start=_money_amount(parsed.total_liabilities_period_start),
        equity_end=_money_amount(parsed.equity_period_end),
        equity_start=_money_amount(parsed.equity_period_start),
        total_debt_end=_money_amount(parsed.total_debt_period_end),
        total_debt_start=_money_amount(parsed.total_debt_period_start),
    )

    if out.assets_end is not None:
        source_trail["form1.assets_total"] = label
    if out.liabilities_end is not None:
        source_trail["form1.liabilities_total"] = label
    if out.assets_start is not None:
        source_trail["form1.assets_total_period_start"] = label
    if out.liabilities_start is not None:
        source_trail["form1.liabilities_total_period_start"] = label
    if out.equity_end is not None:
        source_trail["form1.equity"] = label
    if out.equity_start is not None:
        source_trail["form1.equity_period_start"] = label
    if out.total_debt_end is not None:
        source_trail["form1.total_debt"] = label
    if out.total_debt_start is not None:
        source_trail["form1.total_debt_period_start"] = label

    for w in parsed.parse_warnings:
        warnings.append(f"{winner.filename}: {w}")

    return out


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
