"""DateRange: closed interval [start, end] для финансовых периодов."""

from dataclasses import dataclass
from datetime import date


class InvalidDateRangeError(ValueError):
    """Нарушен инвариант start <= end."""


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise InvalidDateRangeError(
                f"start ({self.start}) must be <= end ({self.end})",
            )

    @property
    def length_days(self) -> int:
        # Closed interval: единственный день = длина 1
        return (self.end - self.start).days + 1

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def overlaps(self, other: "DateRange") -> bool:
        return self.start <= other.end and other.start <= self.end
