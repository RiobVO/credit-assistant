"""BorrowerSnapshot: агрегат данных, который подаётся всем правилам как input."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("123456789"),
        name="ООО Test",
        legal_form=LegalForm.LLC,
        registration_date=date(2020, 3, 15),
        director_name="Иванов И.И.",
        director_appointed_at=date(2024, 1, 10),
        oked_main="62.01",
        registered_address="Ташкент",
    )


class TestBorrowerSnapshotConstruction:
    def test_creates_with_minimum_required(self) -> None:
        s = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 8),
        )
        assert s.borrower.inn.value == "123456789"
        assert s.as_of == date(2026, 5, 8)

    def test_collection_fields_default_empty(self) -> None:
        s = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 8),
        )
        assert s.annual_reports == []
        assert s.monthly_turnover == []
        assert s.invoices == []
        assert s.tax_events == []
        assert s.buyer_revenue_share == {}
        assert s.supplier_purchase_share == {}
        assert s.loan_request is None

    def test_carries_loan_request(self) -> None:
        s = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 8),
            loan_request=LoanRequest(
                amount=Money(Decimal("2000000000"), UZS),
                term_months=24,
                rate_pct=Decimal("22.5"),
                purpose="working_capital",
                category="standard",
            ),
        )
        assert s.loan_request is not None
        assert s.loan_request.amount.amount == Decimal("2000000000")

    def test_holds_annual_reports(self) -> None:
        report = FinancialReport(
            period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
            revenue=Money(Decimal("5000000000"), UZS),
            net_profit=Money(Decimal("400000000"), UZS),
            taxes_paid=Money(Decimal("250000000"), UZS),
        )
        s = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 8),
            annual_reports=[report],
        )
        assert len(s.annual_reports) == 1

    def test_holds_monthly_turnover(self) -> None:
        m = MonthlyTurnover(
            month_start=date(2026, 4, 1),
            revenue=Money(Decimal("100000000"), UZS),
        )
        s = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 8),
            monthly_turnover=[m],
        )
        assert s.monthly_turnover[0].month_start == date(2026, 4, 1)

    def test_holds_buyer_share_map(self) -> None:
        s = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 8),
            buyer_revenue_share={"987654321": Decimal("0.75")},
        )
        assert s.buyer_revenue_share["987654321"] == Decimal("0.75")
