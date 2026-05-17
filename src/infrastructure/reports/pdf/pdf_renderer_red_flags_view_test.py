"""Unit-тесты `_build_red_flags_view` (T0.4 follow-up B1).

Проверяем что locale-aware source picker подставляет ``source_uz`` для
UZ-bundle и RU ``source`` для RU-bundle. Pure-Python, без WeasyPrint —
безопасно запускается на Windows.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from domain.entities.red_flag import RedFlag
from domain.value_objects.flag_severity import FlagSeverity
from infrastructure.i18n.pdf_messages import load_pdf_messages
from infrastructure.reports.pdf.pdf_renderer import _build_red_flags_view

_RU = load_pdf_messages("ru")
_UZ = load_pdf_messages("uz")


def _flag() -> RedFlag:
    return RedFlag(
        rule_id="VAT_ESF_MISMATCH",
        rule_version="v1",
        severity=FlagSeverity.CRITICAL,
        source="НК РУз ст. 256; Soliq внутренние методики",
        source_uz="НК РУз ст. 256; Soliq ichki uslublari",
        message="QQS deklaratsiyasi va EHF oʻrtasidagi farq 80%",
        evidence={},
        detected_at=date(2026, 5, 8),
    )


def _dossier_with(flag: RedFlag) -> SimpleNamespace:
    return SimpleNamespace(red_flags=(flag,))


def test_red_flags_view_uses_ru_source_for_ru_messages() -> None:
    view = _build_red_flags_view(_dossier_with(_flag()), {"VAT_ESF_MISMATCH": "X"}, _RU)
    assert view[0]["source"] == "НК РУз ст. 256; Soliq внутренние методики"


def test_red_flags_view_uses_uz_source_for_uz_messages() -> None:
    view = _build_red_flags_view(_dossier_with(_flag()), {"VAT_ESF_MISMATCH": "X"}, _UZ)
    assert view[0]["source"] == "НК РУз ст. 256; Soliq ichki uslublari"


def test_red_flags_view_falls_back_to_ru_when_source_uz_empty() -> None:
    """Backward-compat для test-fixtures и legacy data, где source_uz == ""."""
    flag = RedFlag(
        rule_id="REVENUE_DROP_MOM_30",
        rule_version="v1",
        severity=FlagSeverity.HIGH,
        source="ЦБ РУз положение №27-п",
        source_uz="",  # пустой — например, после старого snapshot или test-mock
        message="Падение выручки 42%",
        evidence={},
        detected_at=date(2026, 5, 8),
    )
    view = _build_red_flags_view(_dossier_with(flag), {"REVENUE_DROP_MOM_30": "X"}, _UZ)
    assert view[0]["source"] == "ЦБ РУз положение №27-п"
