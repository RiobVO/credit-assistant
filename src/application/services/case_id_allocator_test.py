"""Unit-тесты CaseIdAllocator на stub-сессии.

Проверяем формат строки, year-rollover ветку и пропуск reset'а при same-year.
Реальная advisory-lock семантика и race-safety проверяются в integration-
тесте на testcontainers (см. ``tests/integration/persistence/
case_id_allocator_test.py``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from application.services.case_id_allocator import SqlAlchemyCaseIdAllocator


class _StubSession:
    """Минимальный async-stub session. Возвращает mock-results по
    содержимому SQL-строки. Записывает executed SQL для assertions.
    """

    def __init__(self, *, max_year: int | None, nextval: int) -> None:
        self._max_year = max_year
        self._nextval = nextval
        self.executed: list[str] = []

    async def execute(self, stmt: Any, params: Any = None) -> Any:
        sql = str(stmt)
        self.executed.append(sql)
        result = MagicMock()
        if "MAX(SUBSTRING" in sql:
            result.scalar_one_or_none.return_value = self._max_year
        elif "nextval" in sql:
            result.scalar_one.return_value = self._nextval
        return result


@pytest.mark.asyncio
async def test_allocate_first_ever_uses_sequence_as_is() -> None:
    """Пустая таблица — max_year=None → no reset (миграция уже sync'ed
    sequence). nextval=1 → BR-{year}-0001.
    """
    session = _StubSession(max_year=None, nextval=1)
    allocator = SqlAlchemyCaseIdAllocator(session)  # type: ignore[arg-type]

    case_id = await allocator.allocate(datetime(2026, 5, 18, 12, 0, 0))

    assert case_id == "BR-2026-0001"
    # 3 execute: advisory lock + MAX query + nextval — БЕЗ ALTER SEQUENCE.
    assert len(session.executed) == 3
    assert "pg_advisory_xact_lock" in session.executed[0]
    assert "MAX(SUBSTRING" in session.executed[1]
    assert "nextval" in session.executed[2]
    assert not any("ALTER SEQUENCE" in s for s in session.executed)


@pytest.mark.asyncio
async def test_allocate_same_year_skips_reset() -> None:
    """max_year=2026, now.year=2026 → no reset, seq=42 → BR-2026-0042."""
    session = _StubSession(max_year=2026, nextval=42)
    allocator = SqlAlchemyCaseIdAllocator(session)  # type: ignore[arg-type]

    case_id = await allocator.allocate(datetime(2026, 5, 18, 12, 0, 0))

    assert case_id == "BR-2026-0042"
    # 3 execute: lock, MAX, nextval — БЕЗ ALTER SEQUENCE.
    assert len(session.executed) == 3
    assert not any("ALTER SEQUENCE" in s for s in session.executed)


@pytest.mark.asyncio
async def test_allocate_new_year_resets_sequence() -> None:
    """max_year=2026, now.year=2027 → reset, seq=1 → BR-2027-0001."""
    session = _StubSession(max_year=2026, nextval=1)
    allocator = SqlAlchemyCaseIdAllocator(session)  # type: ignore[arg-type]

    case_id = await allocator.allocate(datetime(2027, 1, 1, 0, 0, 0))

    assert case_id == "BR-2027-0001"
    assert len(session.executed) == 4
    assert "ALTER SEQUENCE" in session.executed[2]


@pytest.mark.parametrize(
    ("seq", "expected"),
    [(1, "BR-2026-0001"), (7, "BR-2026-0007"), (123, "BR-2026-0123"), (9999, "BR-2026-9999")],
)
@pytest.mark.asyncio
async def test_allocate_zfill_to_4_digits(seq: int, expected: str) -> None:
    """nextval форматируется в 4-значное zfill."""
    session = _StubSession(max_year=2026, nextval=seq)
    allocator = SqlAlchemyCaseIdAllocator(session)  # type: ignore[arg-type]

    case_id = await allocator.allocate(datetime(2026, 6, 1))

    assert case_id == expected
