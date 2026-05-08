"""Dossier mapper: round-trip RedFlag → JSONB → RedFlag."""

from __future__ import annotations

from datetime import date

from domain.entities.red_flag import RedFlag
from domain.value_objects.flag_severity import FlagSeverity
from infrastructure.persistence.mappers.dossier_mapper import (
    red_flags_from_jsonb,
    red_flags_to_jsonb,
)


def test_red_flags_round_trip() -> None:
    flags = (
        RedFlag(
            rule_id="REVENUE_DROP_MOM_30",
            rule_version="v1",
            severity=FlagSeverity.HIGH,
            source="ЦБ РУз положение №27-п, п.4.5",
            message="Падение выручки на 42% в марте 2026",
            evidence={"month": "2026-03", "drop_pct": -0.42, "consecutive": 2},
            detected_at=date(2026, 5, 8),
        ),
        RedFlag(
            rule_id="VAT_ESF_MISMATCH",
            rule_version="v1",
            severity=FlagSeverity.CRITICAL,
            source="НК РУз ст. 256",
            message="Разрыв НДС-декларация vs ЭСФ 80%",
            evidence={},
            detected_at=date(2026, 5, 8),
        ),
    )
    restored = red_flags_from_jsonb(red_flags_to_jsonb(flags))
    assert restored == flags
