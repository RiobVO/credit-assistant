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
    # T0.4 / ADR-0015: UZ-перевод name. Required (min_length=1) — banking-grade
    # продукт не должен иметь fallback-to-empty semantics; новое правило без
    # UZ-имени падает на load_registry, не на runtime в PDF.
    name_uz: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: FlagSeverity
    source: str = Field(min_length=1)
    # T0.4 follow-up B1: UZ-перевод source. Required (min_length=1) — fail-fast
    # на load_registry. Compliance-конвенция: regulatory doc names (ЦБ РУз,
    # Базель III, НК РУз, Group-IB report titles) остаются identical, только
    # descriptive RU-phrases переводятся на latin-узб.
    source_uz: str = Field(min_length=1)
    formula: str = Field(default="", description="Documentation only")
    rationale: str = Field(default="", description="Documentation only")


class RulesConfigYaml(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(min_length=1)
    rules: list[RuleSpecYaml]
