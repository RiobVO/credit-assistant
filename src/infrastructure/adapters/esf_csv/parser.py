"""EsfCsvAdapter: парсер выгрузки ``factura_*_<inn>_*.csv`` из e-factura.uz.

Формат CSV (cp1251, разделитель ``;``):

    №; ID; СТАТУС; СЧЁТ-ФАКТУРА; ТИП ЭСФ; ДОГОВОР;
    ПРОДАВЕЦ (ИНН ИЛИ ПИНФЛ); ПРОДАВЕЦ (НАИМЕНОВАНИЕ);
    ПРОДАВЕЦ (КОД ФИЛИАЛА); ПРОДАВЕЦ (НАЗВАНИЕ ФИЛИАЛА);
    ПОКУПАТЕЛЬ (ИНН ИЛИ ПИНФЛ); ПОКУПАТЕЛЬ (НАИМЕНОВАНИЕ);
    ПОКУПАТЕЛЬ (КОД ФИЛИАЛА); ПОКУПАТЕЛЬ (НАЗВАНИЕ ФИЛИАЛА);
    СУММА К ОПЛАТЕ; ПРИМЕЧАНИЕ

Особенности реальных данных:
- ``СЧЁТ-ФАКТУРА`` склеена: ``"27 от 31.03.2020"`` → дата извлекается regex.
- ``СУММА К ОПЛАТЕ`` бывает с запятой как десятичный разделитель и отрицательной
  (корректировочные ЭСФ).
- ``ПОКУПАТЕЛЬ (ИНН)`` может быть 14-значным ПИНФЛ (физлицо).
- В ``НАИМЕНОВАНИЕ`` физлица бывает trailing ``" / "`` — обрезаем.
- ``СТАТУС`` и ``ТИП ЭСФ`` парсер пока **не** фильтрует: на 2.2 включаются все
  строки, где заёмщик совпадает с продавцом или покупателем. Аннулирование
  и корректировки — отдельное правило, добавим по реальному кейсу.
- Пустой ИНН контрагента — встречается в реальных данных (ЭСФ физлицу без
  ПИНФЛ, кассовые операции). Такие строки пропускаются молча; для домена они
  бесполезны (нет ключа для агрегации по контрагенту).

Direction (``InvoiceRole``) определяется через сравнение ИНН заёмщика с
ПРОДАВЕЦ/ПОКУПАТЕЛЬ. Строки, не относящиеся к заёмщику, тихо пропускаются:
такое случается, если выгрузка содержит данные нескольких юрлиц одного
владельца, а парсер вызывается для одного. Если ни одна строка не относится
к заёмщику — это аномалия (загрузили чужой файл), ``MalformedFileError``.
"""

import csv
import io
import re
from collections.abc import Iterator
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import BinaryIO

from application.dto.parsed_data_chunk import EsfChunk
from domain.entities.invoice import Invoice, InvoiceRole
from domain.value_objects.inn import INN, InvalidInnError
from domain.value_objects.money import Currency, Money
from infrastructure.adapters.esf_csv.errors import MalformedFileError, MalformedRowError

ENCODING = "cp1251"
DELIMITER = ";"

COL_INVOICE = "СЧЁТ-ФАКТУРА"
COL_SELLER_INN = "ПРОДАВЕЦ (ИНН ИЛИ ПИНФЛ)"
COL_SELLER_NAME = "ПРОДАВЕЦ (НАИМЕНОВАНИЕ)"
COL_BUYER_INN = "ПОКУПАТЕЛЬ (ИНН ИЛИ ПИНФЛ)"
COL_BUYER_NAME = "ПОКУПАТЕЛЬ (НАИМЕНОВАНИЕ)"
COL_AMOUNT = "СУММА К ОПЛАТЕ"

REQUIRED_COLUMNS: frozenset[str] = frozenset({
    COL_INVOICE,
    COL_SELLER_INN,
    COL_SELLER_NAME,
    COL_BUYER_INN,
    COL_BUYER_NAME,
    COL_AMOUNT,
})

# Номер счёта-фактуры в реальных данных бывает в разных форматах:
# "27 от 31.03.2020", "7-в от 28.02.2025", "40 кп от 20.08.2025",
# "А-12/03 от ...". Извлекаем только дату из хвоста "от ДД.ММ.ГГГГ".
INVOICE_DATE_RE = re.compile(r"\bот\s+(\d{2})\.(\d{2})\.(\d{4})\s*$")


class EsfCsvAdapter:
    """Реализация ``DataSourcePort`` для CSV-выгрузок e-factura.uz."""

    def parse(self, source: BinaryIO, borrower_inn: INN) -> EsfChunk:
        text = io.TextIOWrapper(source, encoding=ENCODING, newline="")
        reader = csv.reader(text, delimiter=DELIMITER, quotechar='"')

        header = self._read_header(reader)
        col_idx = self._build_column_index(header)

        invoices: list[Invoice] = []
        any_match = False
        # row_no = 2 для первой строки данных (1 — заголовок), удобно для пользователя
        for row_no, row in enumerate(reader, start=2):
            if not row or all(not cell.strip() for cell in row):
                continue
            invoice = self._parse_row(row, col_idx, borrower_inn, row_no)
            if invoice is not None:
                any_match = True
                invoices.append(invoice)

        if not any_match:
            raise MalformedFileError(
                f"INN {borrower_inn.masked} не встречается ни в одной строке файла",
            )

        return EsfChunk(borrower_inn=borrower_inn, invoices=invoices)

    @staticmethod
    def _read_header(reader: Iterator[list[str]]) -> list[str]:
        try:
            return next(reader)
        except StopIteration:
            raise MalformedFileError("файл пустой") from None

    @staticmethod
    def _build_column_index(header: list[str]) -> dict[str, int]:
        idx: dict[str, int] = {}
        for i, name in enumerate(header):
            cleaned = name.strip()
            # Не перетираем дубль (на всякий случай — в формате колонки уникальны)
            idx.setdefault(cleaned, i)
        missing = REQUIRED_COLUMNS - idx.keys()
        if missing:
            raise MalformedFileError(
                f"отсутствуют обязательные колонки: {sorted(missing)}",
            )
        return idx

    @staticmethod
    def _parse_row(
        row: list[str],
        col_idx: dict[str, int],
        borrower_inn: INN,
        row_no: int,
    ) -> Invoice | None:
        seller_inn_raw = _cell(row, col_idx, COL_SELLER_INN, row_no).strip()
        buyer_inn_raw = _cell(row, col_idx, COL_BUYER_INN, row_no).strip()

        if seller_inn_raw == borrower_inn.value:
            our_role = InvoiceRole.SELLER
            cp_inn_raw = buyer_inn_raw
            cp_name = _cell(row, col_idx, COL_BUYER_NAME, row_no)
        elif buyer_inn_raw == borrower_inn.value:
            our_role = InvoiceRole.BUYER
            cp_inn_raw = seller_inn_raw
            cp_name = _cell(row, col_idx, COL_SELLER_NAME, row_no)
        else:
            return None

        if not cp_inn_raw:
            # Пустой ИНН контрагента — кассовый ЭСФ или физлицо без ПИНФЛ.
            # Без ключа агрегации строка бесполезна для правил → skip.
            return None

        invoice_date = _parse_invoice_date(
            _cell(row, col_idx, COL_INVOICE, row_no), row_no,
        )
        amount = _parse_amount(_cell(row, col_idx, COL_AMOUNT, row_no), row_no)

        try:
            cp_inn = INN(cp_inn_raw)
        except InvalidInnError as e:
            raise MalformedRowError(
                row_no, f"невалидный ИНН контрагента '{cp_inn_raw}': {e}",
            ) from e

        return Invoice(
            date=invoice_date,
            amount=Money(amount, Currency.UZS),
            our_role=our_role,
            counterparty_inn=cp_inn,
            counterparty_name=_clean_counterparty_name(cp_name),
        )


def _cell(row: list[str], col_idx: dict[str, int], col: str, row_no: int) -> str:
    i = col_idx[col]
    if i >= len(row):
        raise MalformedRowError(row_no, f"в строке нет колонки '{col}'")
    return row[i]


def _parse_invoice_date(raw: str, row_no: int) -> date:
    match = INVOICE_DATE_RE.search(raw)
    if not match:
        raise MalformedRowError(
            row_no, f"не удалось извлечь дату из 'СЧЁТ-ФАКТУРА' = {raw!r}",
        )
    dd, mm, yyyy = match.groups()
    try:
        return date(int(yyyy), int(mm), int(dd))
    except ValueError as e:
        raise MalformedRowError(row_no, f"некорректная дата: {e}") from e


def _parse_amount(raw: str, row_no: int) -> Decimal:
    cleaned = raw.strip().replace(",", ".")
    if not cleaned:
        raise MalformedRowError(row_no, "пустая 'СУММА К ОПЛАТЕ'")
    try:
        return Decimal(cleaned)
    except InvalidOperation as e:
        raise MalformedRowError(
            row_no, f"некорректная сумма {raw!r}: {e}",
        ) from e


def _clean_counterparty_name(raw: str) -> str:
    # Физлицо часто приходит как "ИВАНОВ И.И. / " — убираем хвостовой слэш.
    return raw.strip().rstrip("/").strip()
