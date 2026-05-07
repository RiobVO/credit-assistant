"""RuleRegistry: контейнер правил + run_all → list[RedFlag]."""

from datetime import date

import pytest

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.red_flag import RedFlag
from domain.rules.rule import Rule, RuleRegistry, UnknownRuleError
from domain.value_objects.flag_severity import FlagSeverity
from domain.value_objects.inn import INN


def _snapshot() -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=Borrower(
            inn=INN("123456789"),
            name="ООО",
            legal_form=LegalForm.LLC,
            registration_date=date(2020, 1, 1),
            director_name="Иванов",
            director_appointed_at=date(2024, 1, 1),
            okved_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 8),
    )


def _always_fires(snapshot: BorrowerSnapshot) -> RedFlag | None:
    return RedFlag(
        rule_id="ALWAYS_FIRES",
        rule_version="v1",
        severity=FlagSeverity.HIGH,
        source="test",
        message="fired",
        evidence={},
        detected_at=snapshot.as_of,
    )


def _never_fires(snapshot: BorrowerSnapshot) -> RedFlag | None:
    return None


class TestRule:
    def test_rule_holds_metadata_and_fn(self) -> None:
        rule = Rule(
            id="ALWAYS_FIRES",
            version="v1",
            severity=FlagSeverity.HIGH,
            source="test",
            category="financial",
            fn=_always_fires,
        )
        assert rule.id == "ALWAYS_FIRES"


class TestRuleRegistryRunAll:
    def test_returns_only_fired_flags(self) -> None:
        registry = RuleRegistry(
            rules=[
                Rule("FIRES", "v1", FlagSeverity.HIGH, "src", "financial", _always_fires),
                Rule("SILENT", "v1", FlagSeverity.LOW, "src", "financial", _never_fires),
            ],
        )
        flags = registry.run_all(_snapshot())
        assert len(flags) == 1
        assert flags[0].rule_id == "ALWAYS_FIRES"

    def test_empty_registry_returns_empty(self) -> None:
        registry = RuleRegistry(rules=[])
        assert registry.run_all(_snapshot()) == []

    def test_multiple_firing_rules(self) -> None:
        def _fire(rid: str):  # type: ignore[no-untyped-def]
            def _fn(s: BorrowerSnapshot) -> RedFlag | None:
                return RedFlag(
                    rule_id=rid,
                    rule_version="v1",
                    severity=FlagSeverity.MEDIUM,
                    source="test",
                    message="fired",
                    evidence={},
                    detected_at=s.as_of,
                )
            return _fn

        registry = RuleRegistry(
            rules=[
                Rule("A", "v1", FlagSeverity.MEDIUM, "s", "financial", _fire("A")),
                Rule("B", "v1", FlagSeverity.MEDIUM, "s", "financial", _fire("B")),
            ],
        )
        flags = registry.run_all(_snapshot())
        assert {f.rule_id for f in flags} == {"A", "B"}


class TestRuleRegistryLookup:
    def test_by_id_returns_rule(self) -> None:
        target = Rule("X", "v1", FlagSeverity.LOW, "s", "structural", _never_fires)
        registry = RuleRegistry(rules=[target])
        assert registry.by_id("X") is target

    def test_by_id_unknown_raises(self) -> None:
        registry = RuleRegistry(rules=[])
        with pytest.raises(UnknownRuleError):
            registry.by_id("MISSING")

    def test_duplicate_ids_rejected_at_construction(self) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            RuleRegistry(
                rules=[
                    Rule("X", "v1", FlagSeverity.LOW, "s", "financial", _never_fires),
                    Rule("X", "v1", FlagSeverity.LOW, "s", "financial", _never_fires),
                ],
            )
