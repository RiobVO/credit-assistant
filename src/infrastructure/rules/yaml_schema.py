"""Pydantic-схема YAML-конфигурации правил.

Файл config/rules/v*.yaml читается, валидируется этой схемой, и собирается
в RuleRegistry через registry_factory.load_registry().
"""

from pydantic import BaseModel, ConfigDict, Field

from domain.value_objects.flag_severity import FlagSeverity


class RuleSpecYaml(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: FlagSeverity
    source: str = Field(min_length=1)
    formula: str = Field(default="", description="Documentation only")
    rationale: str = Field(default="", description="Documentation only")


class RulesConfigYaml(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(min_length=1)
    rules: list[RuleSpecYaml]
