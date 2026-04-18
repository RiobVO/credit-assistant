"""LoanRequest: валидация term/rate, frozen-семантика."""

from __future__ import annotations

from decimal import Decimal

import pytest

from domain.value_objects.loan_request import InvalidLoanRequestError, LoanRequest
from domain.value_objects.money import Currency, Money


def _money(amount: int) -> Money:
    return Money(Decimal(amount), Currency.UZS)


def test_loan_request_valid() -> None:
    lr = LoanRequest(
        amount=_money(500_000_000),
        term_months=24,
        rate_pct=Decimal("22.5"),
        purpose="working_capital",
        category="standard",
    )
    assert lr.term_months == 24


def test_loan_request_term_must_be_positive() -> None:
    with pytest.raises(InvalidLoanRequestError):
        LoanRequest(
            amount=_money(100_000_000),
            term_months=0,
            rate_pct=Decimal("20"),
            purpose="x",
            category="y",
        )


def test_loan_request_rate_cannot_be_negative() -> None:
    with pytest.raises(InvalidLoanRequestError):
        LoanRequest(
            amount=_money(100_000_000),
            term_months=12,
            rate_pct=Decimal("-1"),
            purpose="x",
            category="y",
        )


def test_loan_request_is_frozen() -> None:
    lr = LoanRequest(
        amount=_money(100_000_000),
        term_months=12,
        rate_pct=Decimal("20"),
        purpose="x",
        category="y",
    )
    with pytest.raises(AttributeError):
        lr.term_months = 24  # type: ignore[misc]
