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
    # Human-readable заголовок правила из YAML (например «Падение выручки >30% МоМ»).
    # Используется в PDF F-секции вместо rule_id и в observations builder
    # (Phase 10). До Phase 10 поле дропалось registry_factory'ем — теперь
    # пробрасывается синхронно с config/rules/v*.yaml.
    name: str = ""
    # UZ-перевод name (T0.4 / CA-DS29-pdf / ADR-0015). YAML schema требует
    # min_length=1 — fail-fast на load_registry, а не на runtime PDF.
    # Domain dataclass держит soft default="" для test-fixtures, которые
    # конструируют Rule инлайн без UZ-перевода.
    name_uz: str = ""
    # UZ-перевод source (T0.4 follow-up B1). Та же fail-fast стратегия на
    # YAML-уровне + soft default="" для тестовых fixtures.
    source_uz: str = ""


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
            evidence = rule.fn(snapshot)
            if evidence is None:
                continue
            fired.append(
                RedFlag(
                    rule_id=rule.id,
                    rule_version=rule.version,
                    severity=rule.severity,
                    source=rule.source,
                    source_uz=rule.source_uz,
                    message=evidence.message,
                    evidence=evidence.evidence,
                    detected_at=snapshot.as_of,
                ),
            )
        return fired
