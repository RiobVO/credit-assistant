"""RuleRegistry: контейнер правил + run_all → list[RedFlag] (упаковано из FiringEvidence)."""

from collections.abc import Callable
from datetime import date

import pytest

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence
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
            oked_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 8),
    )


def _always_fires(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    return FiringEvidence(message="always fires", evidence={"hit": True})


def _never_fires(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
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
    def test_packs_metadata_into_red_flag(self) -> None:
        registry = RuleRegistry(
            rules=[
                Rule(
                    "ALWAYS_FIRES",
                    "v1",
                    FlagSeverity.HIGH,
                    "ЦБ РУз 27-п",
                    "financial",
                    _always_fires,
                ),
            ],
        )
        flags = registry.run_all(_snapshot())
        assert len(flags) == 1
        flag = flags[0]
        assert flag.rule_id == "ALWAYS_FIRES"
        assert flag.severity == FlagSeverity.HIGH
        assert flag.source == "ЦБ РУз 27-п"
        assert flag.message == "always fires"
        assert flag.evidence == {"hit": True}
        assert flag.detected_at == date(2026, 5, 8)

    def test_silent_rule_does_not_emit(self) -> None:
        registry = RuleRegistry(
            rules=[
                Rule("SILENT", "v1", FlagSeverity.LOW, "src", "financial", _never_fires),
            ],
        )
        assert registry.run_all(_snapshot()) == []

    def test_empty_registry_returns_empty(self) -> None:
        registry = RuleRegistry(rules=[])
        assert registry.run_all(_snapshot()) == []

    def test_multiple_firing_rules(self) -> None:
        def _make_fn(
            label: str,
        ) -> Callable[[BorrowerSnapshot], FiringEvidence | None]:
            def _fn(s: BorrowerSnapshot) -> FiringEvidence | None:
                return FiringEvidence(message=label, evidence={})
            return _fn

        registry = RuleRegistry(
            rules=[
                Rule("A", "v1", FlagSeverity.MEDIUM, "s", "financial", _make_fn("a")),
                Rule("B", "v1", FlagSeverity.MEDIUM, "s", "financial", _make_fn("b")),
            ],
        )
        flags = registry.run_all(_snapshot())
        assert {f.rule_id for f in flags} == {"A", "B"}


class TestRuleRegistrySeverityOverride:
    """ADR-0024 Session 3: FiringEvidence.severity override поверх rule.severity."""

    def test_override_none_uses_rule_severity(self) -> None:
        # Evidence без severity — flag берёт severity из YAML (Rule.severity).
        def _fires_default(s: BorrowerSnapshot) -> FiringEvidence | None:
            return FiringEvidence(message="default", evidence={})

        registry = RuleRegistry(
            rules=[
                Rule("R", "v1", FlagSeverity.MEDIUM, "s", "financial", _fires_default),
            ],
        )
        flags = registry.run_all(_snapshot())
        assert flags[0].severity == FlagSeverity.MEDIUM

    def test_override_promotes_severity(self) -> None:
        # Evidence.severity=HIGH перекрывает Rule.severity=MEDIUM.
        def _fires_escalated(s: BorrowerSnapshot) -> FiringEvidence | None:
            return FiringEvidence(
                message="escalated",
                evidence={},
                severity=FlagSeverity.HIGH,
            )

        registry = RuleRegistry(
            rules=[
                Rule("R", "v1", FlagSeverity.MEDIUM, "s", "financial", _fires_escalated),
            ],
        )
        flags = registry.run_all(_snapshot())
        assert flags[0].severity == FlagSeverity.HIGH


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
