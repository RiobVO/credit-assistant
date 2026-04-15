"""VAT_ESF_MISMATCH: расхождение НДС-декларация vs сумма ЭСФ как продавец >15%."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice, InvoiceRole
from domain.rules.financial.vat_esf_mismatch import vat_esf_mismatch
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS
PERIOD = DateRange(date(2025, 1, 1), date(2025, 12, 31))


def _annual(vat_declared: int | None) -> FinancialReport:
    return FinancialReport(
        period=PERIOD,
        revenue=Money(1, UZS),
        net_profit=Money(0, UZS),
        taxes_paid=Money(0, UZS),
        vat_declared=Money(Decimal(vat_declared), UZS) if vat_declared is not None else None,
    )


def _esf(vat: int, role: InvoiceRole = InvoiceRole.SELLER) -> Invoice:
    return Invoice(
        date=date(2025, 6, 15),
        amount=Money(0, UZS),
        vat_amount=Money(Decimal(vat), UZS),
        our_role=role,
        counterparty_inn=INN("987654321"),
        counterparty_name="ООО",
    )


def _snapshot(annual: FinancialReport, invoices: list[Invoice]) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=Borrower(
            inn=INN("123456789"),
            name="ООО",
            legal_form=LegalForm.LLC,
            registration_date=date(2020, 1, 1),
            director_name="Иванов",
            director_appointed_at=date(2020, 1, 1),
            okved_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 8),
        annual_reports=[annual],
        invoices=invoices,
    )


class TestVatEsfMismatch:
    def test_fires_at_20pct_mismatch(self) -> None:
        # Декларация=100, ЭСФ=80, разрыв 20%
        ev = vat_esf_mismatch(_snapshot(_annual(100), [_esf(80)]))
        assert ev is not None

    def test_silent_at_5pct_mismatch(self) -> None:
        assert vat_esf_mismatch(_snapshot(_annual(100), [_esf(95)])) is None

    def test_silent_at_exactly_15pct(self) -> None:
        # 100 vs 85 = 15% разрыв, граница — silent
        assert vat_esf_mismatch(_snapshot(_annual(100), [_esf(85)])) is None

    def test_silent_when_vat_declared_missing(self) -> None:
        assert vat_esf_mismatch(_snapshot(_annual(None), [_esf(80)])) is None

    def test_ignores_buyer_invoices(self) -> None:
        # Покупательские ЭСФ не считаем (вход VAT)
        s = _snapshot(_annual(100), [_esf(80, InvoiceRole.BUYER)])
        # Тогда seller_vat=0, разрыв 100% → fires
        ev = vat_esf_mismatch(s)
        assert ev is not None

    def test_silent_when_no_invoices_and_zero_declared(self) -> None:
        # Если декларация = 0 — деление на 0 → silent (нечего сравнивать)
        assert vat_esf_mismatch(_snapshot(_annual(0), [])) is None
