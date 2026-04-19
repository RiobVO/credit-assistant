"""Извлечение шапки из xltx-форм my3.soliq.uz: ИНН, организация, период.

Координаты шапки разные для каждой формы — диспатч по ``SoliqXltxFormat``.
Ilova-реестр (Приложение №4) собственной шапки не имеет, parse_header его не
обслуживает — она прилагается к декларации, к которой и относится файл.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from domain.value_objects.inn import INN, InvalidInnError
from infrastructure.adapters.soliq_xltx.errors import (
    MalformedXltxError,
    UnsupportedFormatError,
)
from infrastructure.adapters.soliq_xltx.format_detector import SoliqXltxFormat

PeriodKind = Literal["month", "quarter", "annual"]


@dataclass(frozen=True, slots=True)
class SoliqXltxHeader:
    """Унифицированная шапка xltx-формы.

    ``period_index`` — номер месяца (1-12) либо квартала (1-4); ``None``, если
    форма годовая или конкретный номер не указан в шапке (для VAT-декларации
    номер месяца не лежит в фиксированной cell — он проявляется через
    ``submitted_at`` или имя файла).
    """

    borrower_inn: INN
    organization_name: str
    period_year: int
    period_kind: PeriodKind
    period_index: int | None
    submitted_at: date | None


def parse_header(wb: Workbook, fmt: SoliqXltxFormat) -> SoliqXltxHeader:
    """Прочитать шапку формы по правилам ``fmt``."""
    if "list01" not in wb.sheetnames:
        raise UnsupportedFormatError(wb.sheetnames, "no list01")
    ws = wb["list01"]

    if fmt is SoliqXltxFormat.VAT_DECLARATION:
        return _parse_vat_declaration_header(ws)
    if fmt is SoliqXltxFormat.FORM_2_INCOME_STATEMENT:
        return _parse_form2_header(ws)
    if fmt is SoliqXltxFormat.FORM_1_BALANCE_SHEET:
        return _parse_form1_header(ws)
    if fmt is SoliqXltxFormat.PROFIT_TAX:
        return _parse_profit_tax_header(ws)
    raise UnsupportedFormatError(wb.sheetnames, f"parse_header не определён для {fmt}")


def _parse_vat_declaration_header(ws: Worksheet) -> SoliqXltxHeader:
    inn = _read_inn(ws, "D3")
    org = _read_text(ws, "H9", reason="organization name missing")
    year = _read_int(ws, "O5", reason="period_year missing")
    kind = _read_period_kind(ws, "K5")
    submitted = _read_date(ws, "H17")
    return SoliqXltxHeader(
        borrower_inn=inn,
        organization_name=org,
        period_year=year,
        period_kind=kind,
        period_index=None,  # для месячной декларации номер не лежит в фиксированной cell
        submitted_at=submitted,
    )


def _parse_form2_header(ws: Worksheet) -> SoliqXltxHeader:
    inn = _read_inn(ws, "I18")
    org = _read_text(ws, "C8", reason="organization name missing")
    year = _read_int(ws, "C5", reason="period_year missing")
    quarter = _read_optional_int(ws, "E5")
    return SoliqXltxHeader(
        borrower_inn=inn,
        organization_name=org,
        period_year=year,
        period_kind="quarter" if quarter is not None else "annual",
        period_index=quarter,
        submitted_at=None,
    )


def _parse_form1_header(ws: Worksheet) -> SoliqXltxHeader:
    inn = _read_inn(ws, "I17")
    org = _read_text(ws, "C7", reason="organization name missing")
    year = _read_int(ws, "C4", reason="period_year missing")
    quarter = _read_optional_int(ws, "E4")
    return SoliqXltxHeader(
        borrower_inn=inn,
        organization_name=org,
        period_year=year,
        period_kind="quarter" if quarter is not None else "annual",
        period_index=quarter,
        submitted_at=None,
    )


def _parse_profit_tax_header(ws: Worksheet) -> SoliqXltxHeader:
    inn = _read_inn(ws, "C4")
    org = _read_text(ws, "G8", reason="organization name missing")
    year = _read_int(ws, "K6", reason="period_year missing")
    quarter = _read_optional_int(ws, "G6")
    return SoliqXltxHeader(
        borrower_inn=inn,
        organization_name=org,
        period_year=year,
        period_kind="quarter" if quarter is not None else "annual",
        period_index=quarter,
        submitted_at=None,
    )


def _read_inn(ws: Worksheet, coord: str) -> INN:
    raw = ws[coord].value
    if raw is None:
        raise MalformedXltxError(sheet=ws.title, coord=coord, reason="INN cell is empty")
    if isinstance(raw, float):
        # 306399449.0 → "306399449". Поддерживаем только integer-подобные float.
        if not raw.is_integer():
            raise MalformedXltxError(
                sheet=ws.title, coord=coord, reason=f"INN must be integer, got {raw}"
            )
        text = str(int(raw))
    else:
        text = str(raw).strip()
    try:
        return INN(text)
    except InvalidInnError as exc:
        raise MalformedXltxError(sheet=ws.title, coord=coord, reason=f"invalid INN: {exc}") from exc


def _read_text(ws: Worksheet, coord: str, *, reason: str) -> str:
    raw = ws[coord].value
    if raw is None:
        raise MalformedXltxError(sheet=ws.title, coord=coord, reason=reason)
    text = str(raw).strip()
    if not text:
        raise MalformedXltxError(sheet=ws.title, coord=coord, reason=reason)
    return text


def _read_int(ws: Worksheet, coord: str, *, reason: str) -> int:
    raw = ws[coord].value
    if raw is None:
        raise MalformedXltxError(sheet=ws.title, coord=coord, reason=reason)
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except ValueError as exc:
            raise MalformedXltxError(
                sheet=ws.title, coord=coord, reason=f"{reason}: not int"
            ) from exc
    raise MalformedXltxError(sheet=ws.title, coord=coord, reason=f"{reason}: type {type(raw)}")


def _read_optional_int(ws: Worksheet, coord: str) -> int | None:
    raw = ws[coord].value
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None


def _read_period_kind(ws: Worksheet, coord: str) -> PeriodKind:
    raw = ws[coord].value
    if raw is None:
        return "annual"
    text = str(raw).strip().lower()
    if "месяц" in text:
        return "month"
    if "кварт" in text:
        return "quarter"
    if "год" in text:
        return "annual"
    raise MalformedXltxError(
        sheet=ws.title, coord=coord, reason=f"unrecognized period kind: {raw!r}"
    )


def _read_date(ws: Worksheet, coord: str) -> date | None:
    raw = ws[coord].value
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.strptime(raw.strip(), "%d.%m.%Y").date()
        except ValueError:
            return None
    return None
