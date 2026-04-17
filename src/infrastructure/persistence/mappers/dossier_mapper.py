"""DossierRecord ↔ DossierORM. RedFlag сериализуется в JSONB-совместимый dict."""

from __future__ import annotations

from datetime import date
from typing import Any

from application.dto.dossier_record import DossierRecord
from domain.entities.red_flag import RedFlag
from domain.value_objects.flag_severity import FlagSeverity


def _red_flag_to_dict(rf: RedFlag) -> dict[str, Any]:
    return {
        "rule_id": rf.rule_id,
        "rule_version": rf.rule_version,
        "severity": rf.severity.value,
        "source": rf.source,
        "message": rf.message,
        "evidence": dict(rf.evidence),
        "detected_at": rf.detected_at.isoformat(),
    }


def _red_flag_from_dict(d: dict[str, Any]) -> RedFlag:
    return RedFlag(
        rule_id=d["rule_id"],
        rule_version=d["rule_version"],
        severity=FlagSeverity(d["severity"]),
        source=d["source"],
        message=d["message"],
        evidence=dict(d.get("evidence") or {}),
        detected_at=date.fromisoformat(d["detected_at"]),
    )


def red_flags_to_jsonb(red_flags: tuple[RedFlag, ...]) -> list[dict[str, Any]]:
    return [_red_flag_to_dict(rf) for rf in red_flags]


def red_flags_from_jsonb(data: list[dict[str, Any]]) -> tuple[RedFlag, ...]:
    return tuple(_red_flag_from_dict(item) for item in data)


def dossier_record_from_orm_columns(
    score: int,
    recommendation: str,
    severity_breakdown: dict[str, int],
    red_flags: list[dict[str, Any]],
    rules_version: str,
    rules_evaluated: int,
) -> DossierRecord:
    """Собирает DossierRecord из колонок ORM. Принимает раздельные значения,
    чтобы не тянуть SQLAlchemy типы в этот модуль."""
    return DossierRecord(
        score=score,
        recommendation=recommendation,
        severity_breakdown=dict(severity_breakdown),
        red_flags=red_flags_from_jsonb(red_flags),
        rules_version=rules_version,
        rules_evaluated=rules_evaluated,
    )
