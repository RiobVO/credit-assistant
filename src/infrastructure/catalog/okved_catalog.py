"""OKVED catalog loader (CA-DS17): mirror frontend OkvedAutocomplete.

Источник — ``config/okved/uz_msb.json``. JSON-формат:

```
{
  "version": 1,
  "items": [
    {
      "code": "47.11",
      "short_ru": "...",
      "full_ru": "...",
      "short_uz": "...",
      "full_uz": "..."
    },
    ...
  ]
}
```

Singleton-доступ через ``default_catalog()`` — JSON парсится один раз и
кэшируется в module-scope. Тесты передают свой path в ``load_catalog`` для
изоляции.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from application.dto.okved import OkvedEntry

# config/okved лежит в корне репо (рядом с config/brands, config/rules).
# src/infrastructure/catalog/ → ../../../config/okved
_CATALOG_DIR = Path(__file__).resolve().parents[3] / "config" / "okved"
_DEFAULT_FILE = "uz_msb.json"


class OkvedCatalogError(ValueError):
    """OKVED catalog файл отсутствует или повреждён."""


class OkvedCatalog:
    """In-memory OKVED registry. Создаётся через ``load_catalog``."""

    __slots__ = ("_by_code", "_entries")

    def __init__(self, entries: tuple[OkvedEntry, ...]) -> None:
        self._entries = entries
        self._by_code: dict[str, OkvedEntry] = {e.code: e for e in entries}

    def get(self, code: str) -> OkvedEntry | None:
        return self._by_code.get(code)

    def list(self) -> tuple[OkvedEntry, ...]:
        return self._entries


def load_catalog(path: Path | None = None) -> OkvedCatalog:
    """Парсит JSON и возвращает свежий catalog. Без кэширования.

    Raises ``OkvedCatalogError`` при отсутствии файла, невалидном JSON или
    отсутствии required-полей.
    """
    target = path or (_CATALOG_DIR / _DEFAULT_FILE)
    if not target.exists():
        raise OkvedCatalogError(f"OKVED catalog not found: {target}")
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OkvedCatalogError(f"invalid JSON in {target}: {exc}") from exc

    items = raw.get("items")
    if not isinstance(items, list):
        raise OkvedCatalogError(f"missing or non-list 'items' in {target}")

    entries: list[OkvedEntry] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise OkvedCatalogError(f"item #{idx} in {target} is not an object")
        try:
            entries.append(
                OkvedEntry(
                    code=item["code"],
                    short_ru=item["short_ru"],
                    full_ru=item["full_ru"],
                    short_uz=item["short_uz"],
                    full_uz=item["full_uz"],
                )
            )
        except KeyError as exc:
            raise OkvedCatalogError(
                f"missing key {exc} in item #{idx} of {target}"
            ) from exc

    return OkvedCatalog(tuple(entries))


@lru_cache(maxsize=1)
def default_catalog() -> OkvedCatalog:
    """Process-wide singleton. Используется PDF renderer и API endpoint."""
    return load_catalog()
