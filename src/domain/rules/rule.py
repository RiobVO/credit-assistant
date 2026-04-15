"""Rule + RuleRegistry: контейнер правила и движок прогона по снапшоту."""

from dataclasses import dataclass

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.red_flag import RedFlag
from domain.rules.protocol import RuleFn
from domain.value_objects.flag_severity import FlagSeverity


class UnknownRuleError(KeyError):
    """Запрос правила, которого нет в registry."""


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    version: str
    severity: FlagSeverity
    source: str
    category: str
    fn: RuleFn


class RuleRegistry:
    def __init__(self, rules: list[Rule]) -> None:
        seen: set[str] = set()
        for rule in rules:
            if rule.id in seen:
                raise ValueError(f"duplicate rule id: {rule.id}")
            seen.add(rule.id)
        self._rules: list[Rule] = list(rules)
        self._by_id: dict[str, Rule] = {r.id: r for r in rules}

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    def by_id(self, rule_id: str) -> Rule:
        try:
            return self._by_id[rule_id]
        except KeyError as exc:
            raise UnknownRuleError(rule_id) from exc

    def run_all(self, snapshot: BorrowerSnapshot) -> list[RedFlag]:
        fired: list[RedFlag] = []
        for rule in self._rules:
            result = rule.fn(snapshot)
            if result is not None:
                fired.append(result)
        return fired
