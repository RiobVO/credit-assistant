"""Unit-тесты `_resolve_lang` fallback chain (T0.4 / ADR-0015).

Endpoint integration-тесты с реальным WeasyPrint лежат в
``tests/integration/api/dossier_pdf_test.py`` (skipped on Windows). Этот файл
прогоняет чистую логику fallback chain — query > brand.default_lang > "ru" —
без сети и БД.
"""

from __future__ import annotations

from interfaces.api.shared.dossier_pdf import _resolve_lang


class TestResolveLang:
    def test_query_wins(self) -> None:
        assert _resolve_lang("uz", "ru") == "uz"
        assert _resolve_lang("ru", "uz") == "ru"

    def test_brand_default_when_query_none(self) -> None:
        assert _resolve_lang(None, "uz") == "uz"
        assert _resolve_lang(None, "ru") == "ru"

    def test_ru_fallback_when_brand_none(self) -> None:
        assert _resolve_lang(None, None) == "ru"

    def test_invalid_brand_default_falls_back_to_ru(self) -> None:
        # Guard от ручного редактирования brand.json с мусором в defaultLang —
        # на load_brand уровне он валидируется, но pessimistic: endpoint
        # не должен крашиться, если что-то протекло.
        assert _resolve_lang(None, "en") == "ru"
        assert _resolve_lang(None, "") == "ru"
