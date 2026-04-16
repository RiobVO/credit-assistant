"""RedFlag: результат сработавшего правила. Frozen, evidence — типизированный dict."""

from datetime import date

import pytest

from domain.entities.red_flag import RedFlag
from domain.value_objects.flag_severity import FlagSeverity


def _flag(**overrides: object) -> RedFlag:
    base: dict[str, object] = {
        "rule_id": "REVENUE_DROP_MOM_30",
        "rule_version": "v1",
        "severity": FlagSeverity.HIGH,
        "source": "ЦБ РУз положение №27-п, п.4.5",
        "message": "Падение выручки 35% м/м два месяца подряд",
        "evidence": {"mom_pct": -0.35, "consecutive_months": 2},
        "detected_at": date(2026, 5, 8),
    }
    base.update(overrides)
    return RedFlag(**base)  # type: ignore[arg-type]


class TestRedFlagConstruction:
    def test_creates_with_all_fields(self) -> None:
        flag = _flag()
        assert flag.rule_id == "REVENUE_DROP_MOM_30"
        assert flag.severity == FlagSeverity.HIGH
        assert flag.evidence["mom_pct"] == -0.35

    def test_two_flags_with_same_fields_are_equal(self) -> None:
        # Поведение equality нужно для дедупликации в integration-тестах
        assert _flag() == _flag()


class TestRedFlagImmutability:
    def test_severity_cannot_be_reassigned(self) -> None:
        flag = _flag()
        with pytest.raises((AttributeError, TypeError)):
            flag.severity = FlagSeverity.LOW  # type: ignore[misc]
