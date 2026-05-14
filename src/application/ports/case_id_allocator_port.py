"""CaseIdAllocatorPort: контракт аллокатора банковского case_id."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class CaseIdAllocatorPort(Protocol):
    """Выдаёт monotonic case_id ``BR-{YYYY}-{NNNN}`` под текущий год.

    Реализация обязана быть race-safe при параллельных аллокациях через
    advisory lock — иначе year rollover может выдать дубликаты.
    """

    async def allocate(self, now: datetime) -> str:
        """Возвращает следующий case_id для года ``now.year``.

        ``now`` инжектируется (не ``datetime.now()`` внутри), чтобы:
        * тесты задавали детерминированный год без monkeypatch;
        * вызывающий мог использовать ту же временную точку, что и
          ``created_at`` записи (атомарность year-семантики).
        """
        ...
