"""Тесты EsfCsvAdapter — парсер реального CSV из e-factura.uz.

Реальный sample (40 строк) лежит в ``tests/fixtures/esf/factura_sent_306399449_sample.csv``.
Полная выгрузка ``*_full.csv`` исключена из git (см. ``.gitignore`` и ADR 0004).
"""

from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest

from application.dto.parsed_data_chunk import EsfChunk
from domain.entities.invoice import InvoiceRole
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency
from infrastructure.adapters.esf_csv.errors import MalformedFileError, MalformedRowError
from infrastructure.adapters.esf_csv.parser import EsfCsvAdapter

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "esf" / "factura_sent_306399449_sample.csv"
SAMPLE_BORROWER_INN = INN("306399449")


def _bytes_io(text: str, encoding: str = "cp1251") -> BytesIO:
    return BytesIO(text.encode(encoding))


def _csv_with(rows: list[str], header: str | None = None) -> BytesIO:
    """Собрать минимальный CSV с правильным заголовком и переданными data-row'ами."""
    default_header = (
        "№;ID;СТАТУС;СЧЁТ-ФАКТУРА;ТИП ЭСФ;ДОГОВОР;"
        "ПРОДАВЕЦ (ИНН ИЛИ ПИНФЛ);ПРОДАВЕЦ (НАИМЕНОВАНИЕ);"
        "ПРОДАВЕЦ (КОД ФИЛИАЛА);ПРОДАВЕЦ (НАЗВАНИЕ ФИЛИАЛА);"
        "ПОКУПАТЕЛЬ (ИНН ИЛИ ПИНФЛ);ПОКУПАТЕЛЬ (НАИМЕНОВАНИЕ);"
        "ПОКУПАТЕЛЬ (КОД ФИЛИАЛА);ПОКУПАТЕЛЬ (НАЗВАНИЕ ФИЛИАЛА);"
        "СУММА К ОПЛАТЕ;ПРИМЕЧАНИЕ"
    )
    body = "\n".join([header or default_header, *rows])
    return _bytes_io(body)


def _row(
    *,
    seller_inn: str = "306399449",
    seller_name: str = 'ООО "AZ RUHDIL SAVDO"',
    buyer_inn: str = "303069092",
    buyer_name: str = 'ООО "XAYRLI SAVDO PLYUS"',
    invoice: str = "27 от 31.03.2020",
    amount: str = "3105000",
) -> str:
    return (
        f'1;deadbeef;Принят и подписан;{invoice};Стандартный;1 от 01.01.2020;'
        f'{seller_inn};"{seller_name}";;;'
        f'{buyer_inn};"{buyer_name}";;;'
        f'{amount};'
    )


@pytest.fixture
def adapter() -> EsfCsvAdapter:
    return EsfCsvAdapter()


class TestRealSample:
    def test_real_sample_parses_to_seller_invoices(self, adapter: EsfCsvAdapter) -> None:
        with SAMPLE_FIXTURE.open("rb") as f:
            chunk = adapter.parse(f, SAMPLE_BORROWER_INN)
        assert isinstance(chunk, EsfChunk)
        assert chunk.borrower_inn == SAMPLE_BORROWER_INN
        # В sent-выгрузке заёмщик всегда продавец → все Invoice — SELLER.
        assert len(chunk.invoices) >= 30
        assert all(inv.our_role == InvoiceRole.SELLER for inv in chunk.invoices)
        # Контрагент никогда не равен заёмщику.
        assert all(inv.counterparty_inn != SAMPLE_BORROWER_INN for inv in chunk.invoices)

    def test_real_sample_decodes_cp1251_cyrillic(self, adapter: EsfCsvAdapter) -> None:
        with SAMPLE_FIXTURE.open("rb") as f:
            chunk = adapter.parse(f, SAMPLE_BORROWER_INN)
        # Хотя бы одно имя содержит кириллицу — значит cp1251 декодирован верно.
        assert any(any(ch in inv.counterparty_name for ch in "АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЫЭЮЯ")
                   for inv in chunk.invoices)

    def test_real_sample_includes_pinfl_buyer(self, adapter: EsfCsvAdapter) -> None:
        with SAMPLE_FIXTURE.open("rb") as f:
            chunk = adapter.parse(f, SAMPLE_BORROWER_INN)
        pinfl = [inv for inv in chunk.invoices if len(inv.counterparty_inn.value) == 14]
        assert len(pinfl) >= 1, "sample должен содержать ≥1 ПИНФЛ-покупателя"

    def test_real_sample_includes_negative_amount(self, adapter: EsfCsvAdapter) -> None:
        with SAMPLE_FIXTURE.open("rb") as f:
            chunk = adapter.parse(f, SAMPLE_BORROWER_INN)
        assert any(inv.amount.amount < 0 for inv in chunk.invoices), \
            "sample должен содержать ≥1 корректировочный ЭСФ с отрицательной суммой"


class TestDateParsing:
    def test_extracts_date_from_combined_field(self, adapter: EsfCsvAdapter) -> None:
        chunk = adapter.parse(_csv_with([_row(invoice="42 от 15.06.2024")]), INN("306399449"))
        assert chunk.invoices[0].date == date(2024, 6, 15)

    def test_malformed_date_raises_with_row_no(self, adapter: EsfCsvAdapter) -> None:
        with pytest.raises(MalformedRowError) as exc:
            adapter.parse(_csv_with([_row(invoice="not a date")]), INN("306399449"))
        assert exc.value.row_no == 2

    def test_invalid_calendar_date_raises(self, adapter: EsfCsvAdapter) -> None:
        with pytest.raises(MalformedRowError):
            adapter.parse(_csv_with([_row(invoice="1 от 31.02.2024")]), INN("306399449"))

    def test_invoice_number_with_letter_suffix(self, adapter: EsfCsvAdapter) -> None:
        # Реальный формат "7-в от 28.02.2025" — номер с суффиксом, регекс игнорирует.
        chunk = adapter.parse(_csv_with([_row(invoice="7-в от 28.02.2025")]), INN("306399449"))
        assert chunk.invoices[0].date == date(2025, 2, 28)

    def test_invoice_number_with_two_tokens(self, adapter: EsfCsvAdapter) -> None:
        # Реальный формат "40 кп от 20.08.2025" — номер из двух токенов.
        chunk = adapter.parse(_csv_with([_row(invoice="40 кп от 20.08.2025")]), INN("306399449"))
        assert chunk.invoices[0].date == date(2025, 8, 20)


class TestAmountParsing:
    def test_decimal_with_comma_parsed(self, adapter: EsfCsvAdapter) -> None:
        chunk = adapter.parse(_csv_with([_row(amount="6000000,01")]), INN("306399449"))
        assert chunk.invoices[0].amount.amount == Decimal("6000000.01")
        assert chunk.invoices[0].amount.currency == Currency.UZS

    def test_negative_amount_accepted(self, adapter: EsfCsvAdapter) -> None:
        chunk = adapter.parse(_csv_with([_row(amount="-4999500")]), INN("306399449"))
        assert chunk.invoices[0].amount.amount == Decimal("-4999500")

    def test_empty_amount_raises(self, adapter: EsfCsvAdapter) -> None:
        with pytest.raises(MalformedRowError, match="СУММА К ОПЛАТЕ"):
            adapter.parse(_csv_with([_row(amount="")]), INN("306399449"))

    def test_garbage_amount_raises(self, adapter: EsfCsvAdapter) -> None:
        with pytest.raises(MalformedRowError):
            adapter.parse(_csv_with([_row(amount="abc")]), INN("306399449"))


class TestCounterpartyName:
    def test_trailing_slash_trimmed(self, adapter: EsfCsvAdapter) -> None:
        chunk = adapter.parse(
            _csv_with([_row(buyer_name="ИВАНОВ И.И. / ")]),
            INN("306399449"),
        )
        assert chunk.invoices[0].counterparty_name == "ИВАНОВ И.И."


class TestPinflAccepted:
    def test_14_digit_pinfl_buyer_creates_invoice(self, adapter: EsfCsvAdapter) -> None:
        chunk = adapter.parse(
            _csv_with([_row(buyer_inn="12345678901234")]),
            INN("306399449"),
        )
        assert chunk.invoices[0].counterparty_inn.value == "12345678901234"


class TestDirection:
    def test_role_seller_when_borrower_is_seller(self, adapter: EsfCsvAdapter) -> None:
        chunk = adapter.parse(
            _csv_with([_row(seller_inn="306399449", buyer_inn="303069092")]),
            INN("306399449"),
        )
        assert chunk.invoices[0].our_role == InvoiceRole.SELLER

    def test_role_buyer_when_borrower_is_buyer(self, adapter: EsfCsvAdapter) -> None:
        chunk = adapter.parse(
            _csv_with([_row(seller_inn="303069092", buyer_inn="306399449")]),
            INN("306399449"),
        )
        assert chunk.invoices[0].our_role == InvoiceRole.BUYER
        assert chunk.invoices[0].counterparty_inn.value == "303069092"

    def test_row_unrelated_to_borrower_is_skipped(self, adapter: EsfCsvAdapter) -> None:
        # Одна строка по заёмщику, одна — нет; чужая молча пропускается.
        chunk = adapter.parse(
            _csv_with([
                _row(seller_inn="306399449", buyer_inn="303069092"),
                _row(seller_inn="999999999", buyer_inn="888888888"),
            ]),
            INN("306399449"),
        )
        assert len(chunk.invoices) == 1


class TestFileLevelErrors:
    def test_borrower_inn_not_in_any_row_raises(self, adapter: EsfCsvAdapter) -> None:
        with pytest.raises(MalformedFileError, match="не встречается"):
            adapter.parse(_csv_with([_row()]), INN("999999999"))

    def test_empty_file_raises(self, adapter: EsfCsvAdapter) -> None:
        with pytest.raises(MalformedFileError, match="пустой"):
            adapter.parse(_bytes_io(""), INN("306399449"))

    def test_missing_required_column_raises(self, adapter: EsfCsvAdapter) -> None:
        broken_header = "№;ID;СТАТУС;СЧЁТ-ФАКТУРА"  # нет ИНН/сумм
        with pytest.raises(MalformedFileError, match="отсутствуют"):
            adapter.parse(
                _csv_with(["1;a;b;c"], header=broken_header),
                INN("306399449"),
            )

    def test_blank_data_rows_are_skipped(self, adapter: EsfCsvAdapter) -> None:
        chunk = adapter.parse(
            _csv_with(["", _row(), ";;;;;;;;;;;;;;;"]),
            INN("306399449"),
        )
        assert len(chunk.invoices) == 1


class TestEmptyCounterpartyInn:
    def test_empty_counterparty_inn_is_skipped(self, adapter: EsfCsvAdapter) -> None:
        # Реальные данные: ЭСФ физлицу без ПИНФЛ, кассовые операции.
        # Строка пропускается молча — без ИНН её нельзя агрегировать.
        chunk = adapter.parse(
            _csv_with([
                _row(seller_inn="306399449", buyer_inn="303069092"),
                _row(seller_inn="306399449", buyer_inn=""),
            ]),
            INN("306399449"),
        )
        assert len(chunk.invoices) == 1
        assert chunk.invoices[0].counterparty_inn.value == "303069092"
