"""VAT_ESF_MISMATCH: расхождение НДС-декларация vs агрегат НДС из ЭСФ как продавец >15%."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.vat_period_report import VatPeriodReport
from domain.rules.financial.vat_esf_mismatch import vat_esf_mismatch
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS
PERIOD = DateRange(date(2026, 3, 1), date(2026, 3, 31))


def _period(
    vat_declared: int | None,
    esf_seller_vat: int | None,
    *,
    range_: DateRange = PERIOD,
) -> VatPeriodReport:
    return VatPeriodReport(
        period=range_,
        vat_declared=Money(Decimal(vat_declared), UZS) if vat_declared is not None else None,
        esf_seller_vat_total=(
            Money(Decimal(esf_seller_vat), UZS) if esf_seller_vat is not None else None
        ),
    )


def _snapshot(*periods: VatPeriodReport) -> BorrowerSnapshot:
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
        vat_periods=list(periods),
    )


class TestVatEsfMismatch:
    def test_fires_at_20pct_mismatch(self) -> None:
        # Декларация=100, агрегат ЭСФ=80, разрыв 20%
        ev = vat_esf_mismatch(_snapshot(_period(100, 80)))
        assert ev is not None

    def test_silent_at_5pct_mismatch(self) -> None:
        assert vat_esf_mismatch(_snapshot(_period(100, 95))) is None

    def test_silent_at_exactly_15pct(self) -> None:
        # 100 vs 85 = 15% разрыв, граница — silent
        assert vat_esf_mismatch(_snapshot(_period(100, 85))) is None

    def test_silent_when_vat_declared_missing(self) -> None:
        # Только реестр ЭСФ, без декларации — period неполный, правило молчит.
        assert vat_esf_mismatch(_snapshot(_period(None, 80))) is None

    def test_silent_when_esf_aggregate_missing(self) -> None:
        # Декларация без ilova-реестра — degraded режим, правило молчит.
        assert vat_esf_mismatch(_snapshot(_period(100, None))) is None

    def test_silent_when_no_periods(self) -> None:
        assert vat_esf_mismatch(_snapshot()) is None

    def test_fires_when_zero_seller_esf_vs_positive_declared(self) -> None:
        # Агрегат ЭСФ = 0, декларация = 100 → разрыв 100%, fires.
        ev = vat_esf_mismatch(_snapshot(_period(100, 0)))
        assert ev is not None

    def test_silent_when_zero_declared(self) -> None:
        # Декларация = 0 — деление на 0 → silent (нечего сравнивать).
        assert vat_esf_mismatch(_snapshot(_period(0, 0))) is None

    def test_picks_latest_period_by_end_date(self) -> None:
        # Старый период чистый, последний — расхождение → fires на последнем.
        old_clean = _period(
            100,
            98,
            range_=DateRange(date(2026, 1, 1), date(2026, 1, 31)),
        )
        latest_dirty = _period(
            100,
            50,
            range_=DateRange(date(2026, 3, 1), date(2026, 3, 31)),
        )
        ev = vat_esf_mismatch(_snapshot(old_clean, latest_dirty))
        assert ev is not None
        assert ev.evidence["period"] == ["2026-03-01", "2026-03-31"]

    def test_skips_incomplete_periods_when_choosing_latest(self) -> None:
        # Latest по end-date — неполный (только декларация); предыдущий полный с
        # расхождением → правило выбирает полный, fires.
        complete_dirty = _period(
            100,
            50,
            range_=DateRange(date(2026, 2, 1), date(2026, 2, 28)),
        )
        latest_incomplete = _period(
            100,
            None,
            range_=DateRange(date(2026, 3, 1), date(2026, 3, 31)),
        )
        ev = vat_esf_mismatch(_snapshot(complete_dirty, latest_incomplete))
        assert ev is not None
        assert ev.evidence["period"] == ["2026-02-01", "2026-02-28"]
