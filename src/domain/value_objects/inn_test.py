"""Тесты ИНН Узбекистана: 9 цифр для юрлиц, 14 — для ИП/физлиц."""

import pytest

from domain.value_objects.inn import INN, InvalidInnError


class TestInnLengthValidation:
    def test_accepts_9_digit_legal_entity_inn(self) -> None:
        inn = INN("123456789")
        assert inn.value == "123456789"

    def test_accepts_14_digit_individual_inn(self) -> None:
        inn = INN("12345678901234")
        assert inn.value == "12345678901234"

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(InvalidInnError, match="length"):
            INN("")

    def test_rejects_8_digit_string(self) -> None:
        with pytest.raises(InvalidInnError, match="length"):
            INN("12345678")

    def test_rejects_10_digit_string(self) -> None:
        with pytest.raises(InvalidInnError, match="length"):
            INN("1234567890")


class TestInnContentValidation:
    def test_rejects_letters(self) -> None:
        with pytest.raises(InvalidInnError, match="digits"):
            INN("12345678a")

    def test_rejects_whitespace_inside(self) -> None:
        with pytest.raises(InvalidInnError, match="digits"):
            INN("12345 789")

    def test_strips_surrounding_whitespace(self) -> None:
        inn = INN("  123456789  ")
        assert inn.value == "123456789"


class TestInnEquality:
    def test_two_inns_with_same_value_are_equal(self) -> None:
        assert INN("123456789") == INN("123456789")

    def test_inns_with_different_values_are_not_equal(self) -> None:
        assert INN("123456789") != INN("987654321")

    def test_inn_is_hashable(self) -> None:
        bag = {INN("123456789"), INN("123456789"), INN("987654321")}
        assert len(bag) == 2


class TestInnImmutability:
    def test_value_cannot_be_reassigned(self) -> None:
        inn = INN("123456789")
        with pytest.raises((AttributeError, TypeError)):
            inn.value = "999999999"  # type: ignore[misc]


class TestInnMasking:
    def test_masks_all_but_last_4_digits_for_legal_entity(self) -> None:
        # Section 8: ИНН не должен попадать в логи в открытом виде
        assert INN("123456789").masked == "XXXXX6789"

    def test_masks_all_but_last_4_digits_for_individual(self) -> None:
        assert INN("12345678901234").masked == "XXXXXXXXXX1234"
