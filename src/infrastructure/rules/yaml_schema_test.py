"""Unit-тесты RuleSpecYaml schema.

Покрывает required-конvенции для UZ-полей (name_uz, source_uz) — schema
должна падать на boot, а не на runtime PDF.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from infrastructure.rules.yaml_schema import RuleSpecYaml

_VALID_SPEC: dict[str, object] = {
    "id": "REVENUE_DROP_MOM_30",
    "name": "Падение выручки >30% МоМ",
    "name_uz": "Tushumning oydan oyga 30% dan ortiq pasayishi",
    "category": "financial",
    "severity": "high",
    "source": "ЦБ РУз положение №27-п",
    "source_uz": "ЦБ РУз положение №27-п",
}


def test_valid_spec_parses() -> None:
    spec = RuleSpecYaml.model_validate(_VALID_SPEC)
    assert spec.source_uz == "ЦБ РУз положение №27-п"


def test_source_uz_required() -> None:
    """T0.4 follow-up B1: пропуск source_uz должен падать на загрузке."""
    payload = {k: v for k, v in _VALID_SPEC.items() if k != "source_uz"}
    with pytest.raises(ValidationError):
        RuleSpecYaml.model_validate(payload)


def test_source_uz_min_length_one() -> None:
    """Пустая строка тоже отвергается — иначе runtime fallback маскирует bug."""
    payload = dict(_VALID_SPEC)
    payload["source_uz"] = ""
    with pytest.raises(ValidationError):
        RuleSpecYaml.model_validate(payload)
