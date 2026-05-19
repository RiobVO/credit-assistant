"""OKED-UZ benchmark catalog loader (ADR-0024 / Commit 3).

Источник — ``config/benchmarks/oked-uz.json``. Mirror паттерна
``okved_catalog.py``: singleton-доступ через ``default_catalog()``,
парсинг через ``load_catalog(path)`` для тестов с custom path.

Catalog позволяет ``observations_builder`` резолвить industry-label для
borrower'а по его ОКЭД. Раньше PDF cover hardcoded строку «бенчмарк опт.
торговли пищ. продуктами ≈ 12%» для ВСЕХ borrowers — это был bug (особенно
очевиден для ОКЭД 43.39 Отделочные работы → секция F Строительство).

Lookup стратегии:
* ``by_oked_code("43.39")`` → возвращает bucket с ``code_prefix="F"``
  (Строительство), потому что ``"43"`` ∈ ``oked_subsections``.
* ``by_section("F")`` → прямой lookup по section-letter.

Если медианы для UZ не известны — bucket существует, но ``median.*`` поля
``None``. Observations builder использует name из bucket, но не пишет
fake число.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from application.dto.oked_benchmark import (
    OkedBenchmarkBucket,
    OkedBenchmarkMedian,
)

_CATALOG_DIR = Path(__file__).resolve().parents[3] / "config" / "benchmarks"
_DEFAULT_FILE = "oked-uz.json"


class OkedBenchmarkCatalogError(ValueError):
    """Catalog файл отсутствует или повреждён."""


class OkedBenchmarkCatalog:
    """In-memory benchmark registry. Создаётся через ``load_catalog``."""

    __slots__ = ("_buckets", "_by_section", "_by_subsection")

    def __init__(self, buckets: tuple[OkedBenchmarkBucket, ...]) -> None:
        self._buckets = buckets
        self._by_section: dict[str, OkedBenchmarkBucket] = {
            b.code_prefix: b for b in buckets
        }
        self._by_subsection: dict[str, OkedBenchmarkBucket] = {}
        for bucket in buckets:
            for prefix in bucket.oked_subsections:
                self._by_subsection[prefix] = bucket

    def by_section(self, section_letter: str) -> OkedBenchmarkBucket | None:
        return self._by_section.get(section_letter)

    def by_oked_code(self, code: str) -> OkedBenchmarkBucket | None:
        """ОКЭД код «43.39» → bucket Строительство (по 2-digit префиксу «43»)."""
        if not code:
            return None
        # Берём 2-digit prefix (до точки или первые 2 символа).
        prefix = code.split(".")[0][:2]
        return self._by_subsection.get(prefix)

    def list(self) -> tuple[OkedBenchmarkBucket, ...]:
        return self._buckets


def load_catalog(path: Path | None = None) -> OkedBenchmarkCatalog:
    """Парсит JSON и возвращает свежий catalog. Без кэширования.

    Raises ``OkedBenchmarkCatalogError`` при отсутствии файла, невалидном
    JSON или отсутствии required-полей.
    """
    target = path or (_CATALOG_DIR / _DEFAULT_FILE)
    if not target.exists():
        raise OkedBenchmarkCatalogError(f"OKED benchmark catalog not found: {target}")
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OkedBenchmarkCatalogError(f"invalid JSON in {target}: {exc}") from exc

    buckets_raw = raw.get("buckets")
    if not isinstance(buckets_raw, list):
        raise OkedBenchmarkCatalogError(f"missing or non-list 'buckets' in {target}")

    buckets: list[OkedBenchmarkBucket] = []
    for idx, item in enumerate(buckets_raw):
        if not isinstance(item, dict):
            raise OkedBenchmarkCatalogError(
                f"bucket #{idx} in {target} is not an object"
            )
        try:
            median_raw = item["median"]
            buckets.append(
                OkedBenchmarkBucket(
                    code_prefix=item["code_prefix"],
                    oked_subsections=tuple(item["oked_subsections"]),
                    name_ru=item["name_ru"],
                    name_uz=item["name_uz"],
                    median=OkedBenchmarkMedian(
                        roe_pct=median_raw.get("roe_pct"),
                        net_margin_pct=median_raw.get("net_margin_pct"),
                        asset_turnover=median_raw.get("asset_turnover"),
                        debt_to_equity=median_raw.get("debt_to_equity"),
                    ),
                    sample_size=item.get("sample_size"),
                    source=item.get("source", ""),
                    notes=item.get("notes", ""),
                )
            )
        except KeyError as exc:
            raise OkedBenchmarkCatalogError(
                f"missing key {exc} in bucket #{idx} of {target}"
            ) from exc

    return OkedBenchmarkCatalog(tuple(buckets))


@lru_cache(maxsize=1)
def default_catalog() -> OkedBenchmarkCatalog:
    """Process-wide singleton. Используется observations_builder и API endpoint."""
    return load_catalog()
