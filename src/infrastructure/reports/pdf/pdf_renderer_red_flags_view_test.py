"""Unit-тесты `_build_red_flags_view` (T0.4 follow-up B1+B2).

Проверяем что locale-aware picker подставляет ``source_uz`` + ``message_uz``
для UZ-bundle и RU-варианты для RU-bundle. Pure-Python, без WeasyPrint —
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
        message="Декларация НДС vs ЭСФ расходится на 80%",
        message_uz="QQS deklaratsiyasi va EHF 80% ga farqlanadi",
        evidence={},
        detected_at=date(2026, 5, 8),
    )


def _dossier_with(flag: RedFlag) -> SimpleNamespace:
    return SimpleNamespace(red_flags=(flag,))


def test_red_flags_view_uses_ru_source_and_message_for_ru_locale() -> None:
    view = _build_red_flags_view(_dossier_with(_flag()), {"VAT_ESF_MISMATCH": "X"}, _RU)
    assert view[0]["source"] == "НК РУз ст. 256; Soliq внутренние методики"
    assert view[0]["description"] == "Декларация НДС vs ЭСФ расходится на 80%"


def test_red_flags_view_uses_uz_source_and_message_for_uz_locale() -> None:
    view = _build_red_flags_view(_dossier_with(_flag()), {"VAT_ESF_MISMATCH": "X"}, _UZ)
    assert view[0]["source"] == "НК РУз ст. 256; Soliq ichki uslublari"
    assert view[0]["description"] == "QQS deklaratsiyasi va EHF 80% ga farqlanadi"


def test_red_flags_view_falls_back_to_ru_when_uz_fields_empty() -> None:
    """Backward-compat для test-fixtures и legacy data, где source_uz /
    message_uz == "" — re-render на UZ показывает RU-cite + RU description."""
    flag = RedFlag(
        rule_id="REVENUE_DROP_MOM_30",
        rule_version="v1",
        severity=FlagSeverity.HIGH,
        source="ЦБ РУз положение №27-п",
        source_uz="",
        message="Падение выручки 42%",
        message_uz="",
        evidence={},
        detected_at=date(2026, 5, 8),
    )
    view = _build_red_flags_view(_dossier_with(flag), {"REVENUE_DROP_MOM_30": "X"}, _UZ)
    assert view[0]["source"] == "ЦБ РУз положение №27-п"
    assert view[0]["description"] == "Падение выручки 42%"
