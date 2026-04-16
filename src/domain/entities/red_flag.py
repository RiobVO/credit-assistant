"""RedFlag: результат сработавшего правила, прикладывается к досье заёмщика."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from domain.value_objects.flag_severity import FlagSeverity


@dataclass(frozen=True, slots=True)
class RedFlag:
    rule_id: str
    rule_version: str
    severity: FlagSeverity
    source: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    detected_at: date = field(default_factory=date.today)

    def __hash__(self) -> int:
        # evidence — dict, не хешируемый. Хешируем по rule_id + detected_at
        return hash((self.rule_id, self.rule_version, self.detected_at))
