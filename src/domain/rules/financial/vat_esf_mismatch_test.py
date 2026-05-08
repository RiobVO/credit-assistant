"""VAT_ESF_MISMATCH: расхождение НДС-декларация vs агрегат НДС из ЭСФ как продавец >15%."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
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


def _snapshot(annual: FinancialReport, esf_seller_vat: int | None) -> BorrowerSnapshot:
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
        esf_seller_vat_total=(
            Money(Decimal(esf_seller_vat), UZS) if esf_seller_vat is not None else None
        ),
    )


class TestVatEsfMismatch:
    def test_fires_at_20pct_mismatch(self) -> None:
        # Декларация=100, агрегат ЭСФ=80, разрыв 20%
        ev = vat_esf_mismatch(_snapshot(_annual(100), 80))
        assert ev is not None

    def test_silent_at_5pct_mismatch(self) -> None:
        assert vat_esf_mismatch(_snapshot(_annual(100), 95)) is None

    def test_silent_at_exactly_15pct(self) -> None:
        # 100 vs 85 = 15% разрыв, граница — silent
        assert vat_esf_mismatch(_snapshot(_annual(100), 85)) is None

    def test_silent_when_vat_declared_missing(self) -> None:
        assert vat_esf_mismatch(_snapshot(_annual(None), 80)) is None

    def test_silent_when_esf_aggregate_missing(self) -> None:
        # Без VAT-адаптера агрегат отсутствует — degraded режим, правило молчит.
        assert vat_esf_mismatch(_snapshot(_annual(100), None)) is None

    def test_fires_when_zero_seller_esf_vs_positive_declared(self) -> None:
        # Агрегат ЭСФ = 0, декларация = 100 → разрыв 100%, fires.
        ev = vat_esf_mismatch(_snapshot(_annual(100), 0))
        assert ev is not None

    def test_silent_when_zero_declared(self) -> None:
        # Декларация = 0 — деление на 0 → silent (нечего сравнивать)
        assert vat_esf_mismatch(_snapshot(_annual(0), 0)) is None
