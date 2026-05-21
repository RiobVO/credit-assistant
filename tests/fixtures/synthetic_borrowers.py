"""5 синтетических снапшотов с разными профилями риска для integration-тестов.

Каждая фабрика возвращает BorrowerSnapshot, который при прогоне через registry
v1 даёт ожидаемый набор сработавших правил. См. tests/domain/test_rules_engine_integration.py.
"""

from datetime import date, timedelta
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice, InvoiceRole
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.entities.vat_period_report import VatPeriodReport
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money


def _loan(amount: int, *, term_months: int = 24, rate_pct: str = "22.5") -> LoanRequest:
    """Хелпер для тестовых LoanRequest — все обязательные поля с разумными дефолтами."""
    return LoanRequest(
        amount=Money(Decimal(amount), UZS),
        term_months=term_months,
        rate_pct=Decimal(rate_pct),
        purpose="working_capital",
        category="standard",
    )

UZS = Currency.UZS
AS_OF = date(2026, 5, 8)
B = 1_000_000_000  # 1 млрд сум


def _borrower(
    inn: str = "100000001",
    director_appointed_at: date = date(2020, 1, 1),
    okved_changed_at: date | None = None,
    oked_changed_by_owner: bool = False,
) -> Borrower:
    return Borrower(
        inn=INN(inn),
        name=f'ООО "Фирма {inn}"',
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="Иванов И.И.",
        director_appointed_at=director_appointed_at,
        okved_main="62.01",
        okved_main_changed_at=okved_changed_at,
        registered_address="г. Ташкент",
        # ADR-0024 Session 3: OKVED_CHANGED_12M теперь fires только если
        # `oked_changed_by_owner=True`. fixtures, передающие
        # `okved_changed_at`, должны явно ставить флаг для срабатывания.
        oked_changed_by_owner=oked_changed_by_owner,
    )


def _annual(
    year: int,
    revenue: int,
    profit: int,
    vat_declared: int | None = None,
) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=Money(Decimal(revenue), UZS),
        net_profit=Money(Decimal(profit), UZS),
        taxes_paid=Money(Decimal(profit // 5 if profit > 0 else 0), UZS),
        vat_declared=Money(Decimal(vat_declared), UZS) if vat_declared is not None else None,
    )


def _quarter(year: int, q: int, revenue: int, profit: int) -> FinancialReport:
    starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
    ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    return FinancialReport(
        period=DateRange(date(year, *starts[q]), date(year, *ends[q])),
        revenue=Money(Decimal(revenue), UZS),
        net_profit=Money(Decimal(profit), UZS),
        taxes_paid=Money(0, UZS),
    )


def _month(year: int, month: int, revenue: int, vat: int | None = None) -> MonthlyTurnover:
    return MonthlyTurnover(
        month_start=date(year, month, 1),
        revenue=Money(Decimal(revenue), UZS),
        vat_obligations=Money(Decimal(vat), UZS) if vat is not None else None,
    )


# ---------------------------------------------------------------------------
# Профиль 1 — чистый заёмщик. Должен сгенерировать 0 флагов.


def clean_borrower() -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=_borrower(inn="100000001"),
        as_of=AS_OF,
        annual_reports=[
            _annual(2024, 4 * B, 600 * 1_000_000),
            _annual(2025, 5 * B, 800 * 1_000_000),
        ],
        quarterly_reports=[
            _quarter(2025, 3, B, 200 * 1_000_000),
            _quarter(2025, 4, B, 250 * 1_000_000),
            _quarter(2026, 1, B, 220 * 1_000_000),
        ],
        monthly_turnover=[
            _month(2026, 2, 400_000_000),
            _month(2026, 3, 410_000_000),
            _month(2026, 4, 420_000_000),
        ],
        loan_request=_loan(500_000_000),  # 10% revenue
        buyer_revenue_share={"200000001": Decimal("0.30"), "200000002": Decimal("0.40")},
        supplier_purchase_share={"300000001": Decimal("0.50")},
    )


# ---------------------------------------------------------------------------
# Профиль 2 — средний риск: single buyer concentration + okved changed.


def medium_risk_borrower() -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=_borrower(
            inn="100000002",
            okved_changed_at=AS_OF - timedelta(days=200),
            # ADR-0024 Session 3: фикстура полагается на OKVED_CHANGED_12M
            # firing — флаг явно True (смена ОКЭД инициирована собственником).
            oked_changed_by_owner=True,
        ),
        as_of=AS_OF,
        annual_reports=[_annual(2025, 3 * B, 300 * 1_000_000)],
        buyer_revenue_share={"200000010": Decimal("0.80"), "200000011": Decimal("0.20")},
    )


# ---------------------------------------------------------------------------
# Профиль 3 — высокий риск: revenue drop MoM + new counterparties + tax delays.


def high_risk_borrower() -> BorrowerSnapshot:
    new_buyer = Counterparty(
        inn=INN("200000020"),
        name="ООО Новый",
        registration_date=AS_OF - timedelta(days=60),
    )
    return BorrowerSnapshot(
        borrower=_borrower(inn="100000003"),
        as_of=AS_OF,
        annual_reports=[
            _annual(2024, 4 * B, 400 * 1_000_000),
            _annual(2025, 4 * B, 100 * 1_000_000),
        ],
        # ADR-0024: окно март–май, вне seasonal filter (12, 1, 2). Раньше
        # февраль попадал в filter и блокировал MoM-fire.
        monthly_turnover=[
            _month(2026, 3, 1_000_000_000),
            _month(2026, 4, 600_000_000),  # -40%
            _month(2026, 5, 350_000_000),  # -42%
        ],
        counterparties_buyers=[new_buyer],
        buyer_revenue_share={"200000020": Decimal("0.50")},
        tax_events=[
            TaxEvent(date=date(2026, 3, 1), type=TaxEventType.PAYMENT, delay_days=45),
            TaxEvent(date=date(2026, 4, 1), type=TaxEventType.PAYMENT, delay_days=60),
        ],
    )


# ---------------------------------------------------------------------------
# Профиль 4 — критический: VAT-ESF mismatch + shell company partners + penalties.


def critical_borrower() -> BorrowerSnapshot:
    shell = Counterparty(
        inn=INN("200000030"),
        name="ООО Однодневка",
        registration_date=AS_OF - timedelta(days=60),
    )
    return BorrowerSnapshot(
        borrower=_borrower(inn="100000004"),
        as_of=AS_OF,
        annual_reports=[
            _annual(2025, 2 * B, 100 * 1_000_000, vat_declared=300_000_000),
        ],
        invoices=[
            Invoice(
                date=date(2025, 6, 1),
                amount=Money(Decimal(500_000_000), UZS),
                our_role=InvoiceRole.SELLER,
                counterparty_inn=INN("200000030"),
                counterparty_name="ООО Однодневка",
            ),
        ],
        # Месячный VAT-период с расхождением: декларация 300 млн vs ЭСФ 60 млн
        # → VAT_ESF_MISMATCH fires (latest полный период).
        vat_periods=[
            VatPeriodReport(
                period=DateRange(date(2026, 3, 1), date(2026, 3, 31)),
                vat_declared=Money(Decimal(300_000_000), UZS),
                esf_seller_vat_total=Money(Decimal(60_000_000), UZS),
            ),
        ],
        counterparties_buyers=[shell],
        counterparties_suppliers=[shell],
        tax_events=[
            TaxEvent(
                date=date(2026, 2, 1),
                type=TaxEventType.PENALTY,
                amount=Money(Decimal(50_000_000), UZS),
                # ADR-0024 Session 3: фикстура полагается на
                # TAX_PENALTIES_CURRENT_YEAR firing — пеня материальная
                # (ст.223 НК РУз, сокрытие, штраф 20% от суммы).
                material=True,
            ),
            TaxEvent(date=date(2025, 11, 1), type=TaxEventType.ACCOUNT_FREEZE, duration_days=30),
        ],
    )


# ---------------------------------------------------------------------------
# Профиль 5 — overcredit: запрос >50% выручки + 3 квартала убытков.


def loan_oversize_borrower() -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=_borrower(
            inn="100000005",
            okved_changed_at=AS_OF - timedelta(days=200),  # +medium для REVIEW
            # ADR-0024 Session 3: explicit owner flag — фикстура полагается
            # на OKVED_CHANGED_12M firing для подъёма score до REVIEW.
            oked_changed_by_owner=True,
        ),
        as_of=AS_OF,
        annual_reports=[_annual(2025, 1 * B, -50_000_000)],
        quarterly_reports=[
            _quarter(2025, 3, 200_000_000, -10_000_000),
            _quarter(2025, 4, 200_000_000, -20_000_000),
            _quarter(2026, 1, 200_000_000, -30_000_000),
        ],
        loan_request=_loan(800_000_000),  # 80% от B годовой
    )
