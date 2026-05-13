"""T0.4 / ADR-0015 loader unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infrastructure.i18n.pdf_messages import (
    IncompletePdfMessagesError,
    UnknownLocaleError,
    default_pdf_messages,
    load_pdf_messages,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _reset_default_cache() -> None:
    # Singleton кэш ru+uz переживает между тестами иначе.
    default_pdf_messages.cache_clear()


class TestLoadPdfMessagesHappyPath:
    def test_ru_loads_from_default_path(self) -> None:
        msg = load_pdf_messages("ru")
        assert msg.locale == "ru"
        assert msg.section_a_title == "Идентификация заёмщика"
        assert msg.severity["critical"] == "Критический"
        assert msg.recommendation["approve"] == "Одобрить"
        assert msg.month_full[0] == "января"
        assert msg.month_short[11] == "дек"

    def test_uz_loads_from_default_path(self) -> None:
        msg = load_pdf_messages("uz")
        assert msg.locale == "uz"
        assert msg.section_a_title == "Qarz oluvchining identifikatsiyasi"
        assert msg.severity["critical"] == "Kritik"
        assert msg.recommendation["approve"] == "Maʼqullash"
        assert msg.month_full[0] == "yanvar"
        assert msg.month_short[11] == "dek"

    def test_all_groups_populated_in_both_locales(self) -> None:
        # Subkey-completeness: каждый Mapping-group в обоих локалях имеет
        # одинаковые ключи. Если в commit 7 (templates wiring) выяснится, что
        # какое-то subkey забыто, тест ловит асимметрию ru↔uz.
        ru = load_pdf_messages("ru")
        uz = load_pdf_messages("uz")
        for name in (
            "recommendation", "severity", "signal_breakdown", "kpi_label",
            "legal_form_full", "legal_form_short", "evidence_label",
            "gnk_status", "gnk_source", "tax_episode", "business_age_year",
            "page_footer",
        ):
            ru_keys = set(getattr(ru, name).keys())
            uz_keys = set(getattr(uz, name).keys())
            assert ru_keys == uz_keys, f"group {name!r} keys differ ru={ru_keys} uz={uz_keys}"

    def test_observations_templates_carry_format_placeholders(self) -> None:
        """Format-placeholders сохраняются — иначе .format() в observations
        упадёт с KeyError на runtime."""
        for locale in ("ru", "uz"):
            msg = load_pdf_messages(locale)
            assert "{pct}" in msg.obs_revenue_growth_head
            assert "{ratio}" in msg.obs_debt_ratio_head
            assert "{rules_count}" in msg.methodology_body
            assert "{rules_version}" in msg.disclaimer_body


class TestLoadPdfMessagesFailure:
    def test_unknown_locale_raises(self) -> None:
        with pytest.raises(UnknownLocaleError, match="not supported"):
            load_pdf_messages("kg")  # type: ignore[arg-type]

    def test_missing_scalar_key_raises(self, tmp_path: Path) -> None:
        minimal = _ru_minimal()
        del minimal["section_a_title"]
        json_path = tmp_path / "broken.json"
        json_path.write_text(json.dumps(minimal), encoding="utf-8")
        with pytest.raises(IncompletePdfMessagesError, match="section_a_title"):
            load_pdf_messages("ru", path=json_path)

    def test_missing_group_raises(self, tmp_path: Path) -> None:
        minimal = _ru_minimal()
        for k in list(minimal):
            if k.startswith("severity."):
                del minimal[k]
        json_path = tmp_path / "broken.json"
        json_path.write_text(json.dumps(minimal), encoding="utf-8")
        with pytest.raises(IncompletePdfMessagesError, match="severity"):
            load_pdf_messages("ru", path=json_path)

    def test_wrong_month_array_length_raises(self, tmp_path: Path) -> None:
        minimal = _ru_minimal()
        minimal["month_full"] = ["jan", "feb"]  # 2 instead of 12
        json_path = tmp_path / "broken.json"
        json_path.write_text(json.dumps(minimal), encoding="utf-8")
        with pytest.raises(IncompletePdfMessagesError, match="month_full"):
            load_pdf_messages("ru", path=json_path)

    def test_non_string_in_group_raises(self, tmp_path: Path) -> None:
        minimal = _ru_minimal()
        minimal["severity.critical"] = 42  # int, not str
        json_path = tmp_path / "broken.json"
        json_path.write_text(json.dumps(minimal), encoding="utf-8")
        with pytest.raises(IncompletePdfMessagesError, match="critical"):
            load_pdf_messages("ru", path=json_path)


class TestDefaultPdfMessagesCache:
    def test_singleton_returns_same_instance(self) -> None:
        first = default_pdf_messages("ru")
        second = default_pdf_messages("ru")
        assert first is second

    def test_cache_clear_yields_new_instance(self) -> None:
        first = default_pdf_messages("ru")
        default_pdf_messages.cache_clear()
        second = default_pdf_messages("ru")
        assert first is not second
        # Content must remain identical.
        assert first.section_a_title == second.section_a_title

    def test_different_locales_cached_independently(self) -> None:
        ru = default_pdf_messages("ru")
        uz = default_pdf_messages("uz")
        assert ru.locale == "ru"
        assert uz.locale == "uz"
        assert ru is not uz


def _ru_minimal() -> dict[str, object]:
    """Полная копия ru.json для последующего намеренного «ломания» в тестах."""
    src = REPO_ROOT / "config" / "pdf-i18n" / "ru.json"
    return dict(json.loads(src.read_text(encoding="utf-8")))
