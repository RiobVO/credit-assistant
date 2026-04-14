"""FlagSeverity: 4 уровня + сравнение + weight для scoring."""

import pytest

from domain.value_objects.flag_severity import FlagSeverity


class TestFlagSeverityValues:
    def test_has_four_levels(self) -> None:
        assert {s.value for s in FlagSeverity} == {"low", "medium", "high", "critical"}

    def test_creates_from_string(self) -> None:
        assert FlagSeverity("high") == FlagSeverity.HIGH

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError):
            FlagSeverity("urgent")


class TestFlagSeverityWeights:
    # Weights калибруем после Phase 2 — пока экспоненциальный рост
    def test_low_weight_is_1(self) -> None:
        assert FlagSeverity.LOW.weight == 1

    def test_medium_weight_is_3(self) -> None:
        assert FlagSeverity.MEDIUM.weight == 3

    def test_high_weight_is_7(self) -> None:
        assert FlagSeverity.HIGH.weight == 7

    def test_critical_weight_is_15(self) -> None:
        assert FlagSeverity.CRITICAL.weight == 15


class TestFlagSeverityOrdering:
    def test_low_less_than_medium(self) -> None:
        assert FlagSeverity.LOW < FlagSeverity.MEDIUM

    def test_medium_less_than_high(self) -> None:
        assert FlagSeverity.MEDIUM < FlagSeverity.HIGH

    def test_high_less_than_critical(self) -> None:
        assert FlagSeverity.HIGH < FlagSeverity.CRITICAL

    def test_sorts_ascending_by_severity(self) -> None:
        unsorted = [
            FlagSeverity.HIGH,
            FlagSeverity.LOW,
            FlagSeverity.CRITICAL,
            FlagSeverity.MEDIUM,
        ]
        result = sorted(unsorted)
        assert result == [
            FlagSeverity.LOW,
            FlagSeverity.MEDIUM,
            FlagSeverity.HIGH,
            FlagSeverity.CRITICAL,
        ]

    def test_critical_greater_than_low(self) -> None:
        assert FlagSeverity.CRITICAL > FlagSeverity.LOW
