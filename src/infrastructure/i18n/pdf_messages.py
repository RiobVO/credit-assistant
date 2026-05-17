"""PdfMessages loader (T0.4 / ADR-0015): JSON → PdfMessages DTO.

Источник — ``config/pdf-i18n/<locale>.json``. Loader парсит плоский JSON,
группирует dotted-keys (``severity.critical``, …) в ``Mapping[str, str]``
поля DTO и валидирует обязательные scalar/group/sequence ключи.

Singleton-доступ через ``default_pdf_messages(locale)`` — JSON парсится один
раз per-locale и кэшируется (``lru_cache(maxsize=2)``: ru + uz). Тесты
передают свой path в ``load_pdf_messages`` для изоляции и используют
``default_pdf_messages.cache_clear()`` для перезаливки между прогонами.

Format-placeholder валидация (``{pct}``, ``{rules_count}``) намеренно не
делается — она зависит от call-site'а (observations_builder + methodology).
Опечатка в JSON ловится unit-тестами обоих локалей при импорте.
"""

from __future__ import annotations

import json
from dataclasses import fields
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from application.dto.pdf_messages import PdfMessages

Locale = Literal["ru", "uz"]
_SUPPORTED_LOCALES: tuple[Locale, ...] = ("ru", "uz")

# config/pdf-i18n лежит в корне репо. src/infrastructure/i18n/ → ../../../config/pdf-i18n
_I18N_DIR = Path(__file__).resolve().parents[3] / "config" / "pdf-i18n"

_MONTHS_COUNT = 12

# С ``from __future__ import annotations`` field.type приходит как ``str``.
# Эти три литерала покрывают всю schema PdfMessages — расширяешь DTO новым
# shape, добавь литерал и ветку в ``_resolve_field``.
_SCALAR_TYPE = "str"
_MAPPING_TYPE = "Mapping[str, str]"
_MONTH_TUPLE_TYPE = "tuple[str, ...]"


class UnknownLocaleError(ValueError):
    """Запрошена локаль, которой нет в реестре."""


class IncompletePdfMessagesError(ValueError):
    """Отсутствует обязательный ключ / subkey / месяц в JSON."""


def load_pdf_messages(locale: Locale, path: Path | None = None) -> PdfMessages:
    """Загружает PdfMessages из JSON. ``path`` override для тестов.

    Падает на:
    * unknown locale → ``UnknownLocaleError``.
    * file missing / invalid JSON → ``OSError`` / ``json.JSONDecodeError``.
    * missing required scalar / Mapping subkey / month слот → ``IncompletePdfMessagesError``.
    """
    if locale not in _SUPPORTED_LOCALES:
        raise UnknownLocaleError(
            f"locale {locale!r} not supported; expected one of {_SUPPORTED_LOCALES}"
        )

    json_path = path or (_I18N_DIR / f"{locale}.json")
    raw_text = json_path.read_text(encoding="utf-8")
    raw: dict[str, Any] = json.loads(raw_text)
    # Comment-key начинается с подчёркивания — игнорим, JSON без spec-comments.
    raw_filtered = {k: v for k, v in raw.items() if not k.startswith("_")}

    return _build_messages(locale, raw_filtered)


@lru_cache(maxsize=len(_SUPPORTED_LOCALES))
def default_pdf_messages(locale: Locale) -> PdfMessages:
    """Singleton accessor. JSON парсится один раз per-locale.

    Использует module-level ``_I18N_DIR``. Тесты, которые хотят override path,
    зовут ``load_pdf_messages`` напрямую (uncached).
    """
    return load_pdf_messages(locale)


def _build_messages(locale: str, raw: dict[str, Any]) -> PdfMessages:
    """Маппит плоский JSON → ``PdfMessages``. Валидирует наличие всех полей."""
    kwargs: dict[str, Any] = {"locale": locale}

    for field in fields(PdfMessages):
        if field.name == "locale":
            continue
        # ``from __future__ import annotations`` гарантирует field.type — str.
        type_str = field.type if isinstance(field.type, str) else str(field.type)
        kwargs[field.name] = _resolve_field(field.name, type_str, raw)

    return PdfMessages(**kwargs)


def _resolve_field(name: str, type_str: str, raw: dict[str, Any]) -> Any:
    """Одно поле DTO → значение из плоского JSON по форме типа."""
    if type_str == _SCALAR_TYPE:
        if name not in raw:
            raise IncompletePdfMessagesError(f"missing required key {name!r} in pdf-i18n JSON")
        value = raw[name]
        if not isinstance(value, str):
            raise IncompletePdfMessagesError(
                f"key {name!r} expected str, got {type(value).__name__}"
            )
        return value

    if type_str == _MAPPING_TYPE:
        prefix = f"{name}."
        group: dict[str, str] = {}
        for k, v in raw.items():
            if not k.startswith(prefix):
                continue
            if not isinstance(v, str):
                raise IncompletePdfMessagesError(
                    f"key {k!r} expected str, got {type(v).__name__}"
                )
            group[k.removeprefix(prefix)] = v
        if not group:
            raise IncompletePdfMessagesError(
                f"group {name!r} empty: expected dotted keys with prefix {prefix!r}"
            )
        return group

    if type_str == _MONTH_TUPLE_TYPE:
        if name not in raw:
            raise IncompletePdfMessagesError(f"missing required array {name!r} in pdf-i18n JSON")
        seq = raw[name]
        if not isinstance(seq, list) or len(seq) != _MONTHS_COUNT:
            raise IncompletePdfMessagesError(
                f"array {name!r} expected list of {_MONTHS_COUNT} strings"
            )
        for idx, item in enumerate(seq):
            if not isinstance(item, str):
                raise IncompletePdfMessagesError(
                    f"array {name!r}[{idx}] expected str, got {type(item).__name__}"
                )
        return tuple(seq)

    raise AssertionError(f"unhandled PdfMessages field type: {type_str!r} on {name!r}")


__all__ = (
    "IncompletePdfMessagesError",
    "Locale",
    "UnknownLocaleError",
    "default_pdf_messages",
    "load_pdf_messages",
)
