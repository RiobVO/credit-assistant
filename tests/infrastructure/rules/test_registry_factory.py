"""Loader: YAML → RuleRegistry с проверкой соответствия code↔yaml."""

from pathlib import Path

import pytest

from infrastructure.rules.registry_factory import (
    CODE_RULES,
    RuleConfigError,
    load_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_YAML = REPO_ROOT / "config" / "rules" / "v1_uz_msb.yaml"


@pytest.fixture
def tmp_yaml(tmp_path: Path) -> Path:
    return tmp_path / "rules.yaml"


class TestLoadRegistryHappyPath:
    def test_loads_full_registry_from_default_yaml(self) -> None:
        registry = load_registry(DEFAULT_YAML)
        # 17 продакшн-правил + 1 meta (INSUFFICIENT_DATA, CA-016).
        assert len(registry.rules) == 18
        # Все in-code правила должны быть в registry
        for rule_id in CODE_RULES:
            assert registry.by_id(rule_id).id == rule_id

    def test_version_propagates_to_rules(self) -> None:
        registry = load_registry(DEFAULT_YAML)
        for rule in registry.rules:
            assert rule.version == "v1"


class TestLoadRegistryMismatch:
    def test_yaml_with_unknown_rule_raises(self, tmp_yaml: Path) -> None:
        tmp_yaml.write_text(
            "version: v1\n"
            "rules:\n"
            "  - id: NOT_A_RULE\n"
            "    name: x\n"
            "    category: financial\n"
            "    severity: low\n"
            "    source: nope\n",
            encoding="utf-8",
        )
        with pytest.raises(RuleConfigError, match="not implemented in code"):
            load_registry(tmp_yaml)

    def test_yaml_missing_some_rules_raises(self, tmp_yaml: Path) -> None:
        # Только одно из 17, остальные 16 — code-only
        tmp_yaml.write_text(
            "version: v1\n"
            "rules:\n"
            "  - id: DIRECTOR_CHANGED_6M\n"
            "    name: x\n"
            "    category: structural\n"
            "    severity: medium\n"
            "    source: src\n",
            encoding="utf-8",
        )
        with pytest.raises(RuleConfigError, match="not declared in YAML"):
            load_registry(tmp_yaml)

    def test_invalid_severity_raises_validation_error(self, tmp_yaml: Path) -> None:
        tmp_yaml.write_text(
            "version: v1\n"
            "rules:\n"
            "  - id: DIRECTOR_CHANGED_6M\n"
            "    name: x\n"
            "    category: structural\n"
            "    severity: urgent\n"  # invalid
            "    source: src\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            load_registry(tmp_yaml)
