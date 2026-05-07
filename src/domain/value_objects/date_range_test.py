"""DateRange: closed interval [start, end] с инвариантом start <= end."""

from datetime import date

import pytest

from domain.value_objects.date_range import DateRange, InvalidDateRangeError


class TestDateRangeConstruction:
    def test_creates_with_valid_dates(self) -> None:
        r = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        assert r.start == date(2026, 1, 1)
        assert r.end == date(2026, 12, 31)

    def test_creates_single_day_range(self) -> None:
        d = date(2026, 5, 8)
        r = DateRange(d, d)
        assert r.length_days == 1

    def test_rejects_start_after_end(self) -> None:
        with pytest.raises(InvalidDateRangeError):
            DateRange(date(2026, 12, 31), date(2026, 1, 1))


class TestDateRangeLength:
    def test_year_range_length(self) -> None:
        r = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        assert r.length_days == 365

    def test_one_week_range(self) -> None:
        r = DateRange(date(2026, 5, 1), date(2026, 5, 7))
        assert r.length_days == 7


class TestDateRangeContains:
    def test_contains_date_inside(self) -> None:
        r = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        assert r.contains(date(2026, 5, 8))

    def test_contains_start_boundary(self) -> None:
        r = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        assert r.contains(date(2026, 1, 1))

    def test_contains_end_boundary(self) -> None:
        r = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        assert r.contains(date(2026, 12, 31))

    def test_does_not_contain_before(self) -> None:
        r = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        assert not r.contains(date(2025, 12, 31))

    def test_does_not_contain_after(self) -> None:
        r = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        assert not r.contains(date(2027, 1, 1))


class TestDateRangeOverlaps:
    def test_overlapping_ranges(self) -> None:
        a = DateRange(date(2026, 1, 1), date(2026, 6, 30))
        b = DateRange(date(2026, 5, 1), date(2026, 12, 31))
        assert a.overlaps(b)
        assert b.overlaps(a)

    def test_disjoint_ranges_do_not_overlap(self) -> None:
        a = DateRange(date(2026, 1, 1), date(2026, 3, 31))
        b = DateRange(date(2026, 7, 1), date(2026, 12, 31))
        assert not a.overlaps(b)

    def test_adjacent_ranges_share_boundary_day(self) -> None:
        # Closed-interval semantics: общий день — overlap
        a = DateRange(date(2026, 1, 1), date(2026, 6, 30))
        b = DateRange(date(2026, 6, 30), date(2026, 12, 31))
        assert a.overlaps(b)


class TestDateRangeImmutability:
    def test_start_cannot_be_reassigned(self) -> None:
        r = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        with pytest.raises((AttributeError, TypeError)):
            r.start = date(2025, 1, 1)  # type: ignore[misc]

    def test_two_ranges_equal_when_dates_match(self) -> None:
        a = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        b = DateRange(date(2026, 1, 1), date(2026, 12, 31))
        assert a == b
