"""Unit-тесты `_resolve_okved` (T0.4 follow-up B3 — UZ locale picker).

Pure-функция, безопасно тестируется на любом host'е (без WeasyPrint /
GTK runtime, в отличие от integration-теста `pdf_renderer_test.py`).
Проверяем, что catalog-picker отдаёт UZ-пару для ``messages.locale == "uz"``
и RU-пару для остальных значений, плюс unknown-fallback.
"""

from __future__ import annotations

from infrastructure.i18n.pdf_messages import load_pdf_messages
from infrastructure.reports.pdf.pdf_renderer import _resolve_okved

_RU = load_pdf_messages("ru")
_UZ = load_pdf_messages("uz")


def test_resolve_okved_returns_ru_pair_for_ru_messages() -> None:
    short, full = _resolve_okved("47.11", _RU)
    assert short == "Розн. торговля прод. товарами"
    assert full == (
        "Розничная торговля преимущественно пищевыми продуктами"
        " в неспециализированных магазинах"
    )


def test_resolve_okved_returns_uz_pair_for_uz_messages() -> None:
    short, full = _resolve_okved("47.11", _UZ)
    assert short == "Oziq-ovqat chakana savdosi"
    assert full == "Asosan oziq-ovqat mahsulotlari bilan chakana savdo"


def test_resolve_okved_unknown_code_returns_dash_full_label() -> None:
    short, full = _resolve_okved("99.99", _RU)
    assert short == "99.99"
    assert full == "—"
