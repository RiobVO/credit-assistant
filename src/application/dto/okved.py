"""OkvedEntry DTO: запись каталога ОКВЭД (CA-DS17).

Reference catalog МСБ-сегмента УзР: code + локализованные labels (RU/UZ,
short/full). Источник — ``config/okved/uz_msb.json`` (single source для
backend и frontend, см. CA-066 паттерн).

Loader живёт в ``infrastructure.catalog.okved_catalog`` — этот модуль
чистый dataclass без I/O.

Поля локализации:
* ``short_*`` — для compact display (PDF sub-header, frontend chip).
* ``full_*`` — для подробных описаний (PDF detail row, frontend autocomplete).

UZ short может совпадать с UZ full если короткая версия не нужна — это
ок, симметрия структуры важнее экономии 16 строк.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OkvedEntry:
    code: str
    short_ru: str
    full_ru: str
    short_uz: str
    full_uz: str
