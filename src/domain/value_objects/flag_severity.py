"""FlagSeverity: 4 уровня. Weights калибруем после прогона на реальных кейсах."""

from enum import StrEnum


class FlagSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def weight(self) -> int:
        return _SEVERITY_WEIGHTS[self]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, FlagSeverity):
            return NotImplemented
        return self.weight < other.weight

    def __le__(self, other: object) -> bool:
        if not isinstance(other, FlagSeverity):
            return NotImplemented
        return self.weight <= other.weight

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, FlagSeverity):
            return NotImplemented
        return self.weight > other.weight

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, FlagSeverity):
            return NotImplemented
        return self.weight >= other.weight


_SEVERITY_WEIGHTS: dict["FlagSeverity", int] = {
    FlagSeverity.LOW: 1,
    FlagSeverity.MEDIUM: 3,
    FlagSeverity.HIGH: 7,
    FlagSeverity.CRITICAL: 15,
}
