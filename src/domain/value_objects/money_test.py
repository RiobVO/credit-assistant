"""Money: Decimal + Currency, операции внутри валюты, ошибка при кросс-валютных."""

from decimal import Decimal

import pytest

from domain.value_objects.money import Currency, IncompatibleCurrencyError, Money

UZS = Currency.UZS
USD = Currency.USD


class TestMoneyConstruction:
    def test_creates_from_decimal(self) -> None:
        m = Money(Decimal("1000.50"), UZS)
        assert m.amount == Decimal("1000.50")
        assert m.currency == UZS

    def test_creates_from_string_amount(self) -> None:
        m = Money("1000.50", UZS)
        assert m.amount == Decimal("1000.50")

    def test_creates_from_int_amount(self) -> None:
        m = Money(1000, UZS)
        assert m.amount == Decimal("1000")

    def test_rejects_float_amount(self) -> None:
        # float теряет точность — для денег запрещаем
        with pytest.raises(TypeError, match="float"):
            Money(1000.50, UZS)  # type: ignore[arg-type]


class TestMoneyEquality:
    def test_same_amount_and_currency_are_equal(self) -> None:
        assert Money(100, UZS) == Money(100, UZS)

    def test_different_currency_not_equal(self) -> None:
        assert Money(100, UZS) != Money(100, USD)

    def test_money_is_hashable(self) -> None:
        bag = {Money(100, UZS), Money(100, UZS), Money(100, USD)}
        assert len(bag) == 2


class TestMoneyArithmetic:
    def test_addition_same_currency(self) -> None:
        assert Money(100, UZS) + Money(50, UZS) == Money(150, UZS)

    def test_subtraction_same_currency(self) -> None:
        assert Money(100, UZS) - Money(30, UZS) == Money(70, UZS)

    def test_multiplication_by_int(self) -> None:
        assert Money(100, UZS) * 3 == Money(300, UZS)

    def test_multiplication_by_decimal(self) -> None:
        assert Money(100, UZS) * Decimal("1.5") == Money(150, UZS)

    def test_addition_cross_currency_raises(self) -> None:
        with pytest.raises(IncompatibleCurrencyError):
            _ = Money(100, UZS) + Money(50, USD)

    def test_subtraction_cross_currency_raises(self) -> None:
        with pytest.raises(IncompatibleCurrencyError):
            _ = Money(100, UZS) - Money(50, USD)


class TestMoneyComparison:
    def test_less_than_same_currency(self) -> None:
        assert Money(50, UZS) < Money(100, UZS)

    def test_greater_than_same_currency(self) -> None:
        assert Money(100, UZS) > Money(50, UZS)

    def test_comparison_cross_currency_raises(self) -> None:
        with pytest.raises(IncompatibleCurrencyError):
            _ = Money(100, UZS) < Money(50, USD)


class TestMoneyImmutability:
    def test_amount_cannot_be_reassigned(self) -> None:
        m = Money(100, UZS)
        with pytest.raises((AttributeError, TypeError)):
            m.amount = Decimal("999")  # type: ignore[misc]
