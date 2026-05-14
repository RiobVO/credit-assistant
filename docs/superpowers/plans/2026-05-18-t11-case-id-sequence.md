# T1.1 case_id monotonic sequence (compromised B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans для последовательной реализации. Steps размечены чекбоксами `- [ ]`.

**Goal:** Заменить derived `BR-YYYY-XXXX` (от dossier UUID first-4-hex) на банковский monotonic sequence per-year. Сохраняется в `dossiers.case_id` (VARCHAR(20) UNIQUE NOT NULL). Year rollover application-level через `pg_advisory_xact_lock(year)`. Frontend убирает derived helper, рендерит «—» pre-submit. Closes CA-DS18b и CA-DS18c.

**Architecture:**
- Persistence: новая колонка `case_id` + Postgres SEQUENCE `dossier_case_seq` + миграция с backfill `ROW_NUMBER() OVER (PARTITION BY year)` ASC по `created_at`.
- Allocator: `CaseIdAllocator` (application service) — берёт advisory lock по году, проверяет нужен ли reset (year > MAX year в БД), вызывает `nextval`, форматирует `BR-{YYYY}-{NNNN}`. Вызывается use-case'ом перед `dossier_repo.save()`.
- Read-side: `DossierViewRecord` расширяется полем `case_id`; mapper в API и PDF renderer читают его напрямую вместо derived формата.
- Frontend: `formatCaseId` helper + test удаляются, `manual-input-view.tsx` передаёт `null` в `PageHead`, который рендерит «—».

**Tech Stack:** SQLAlchemy 2.0 async, Alembic, FastAPI, pytest+testcontainers, Next.js 15 / vitest.

**Commit policy:** Single atomic commit в конце (после Phase 7 verify). Within phases TDD — но без промежуточных коммитов.

---

## File Structure

**Backend — новые:**
- `src/application/ports/case_id_allocator_port.py` — `CaseIdAllocatorPort` Protocol.
- `src/application/services/case_id_allocator.py` — `SqlAlchemyCaseIdAllocator` имплементация.
- `src/application/services/case_id_allocator_test.py` — unit-тесты (mock session).
- `tests/integration/persistence/case_id_allocator_test.py` — integration (testcontainers): backfill round-trip, year rollover, parallel-safety.
- `src/infrastructure/persistence/migrations/versions/20260518_1500_dossier_case_id_sequence.py` — Alembic.

**Backend — modify:**
- `src/infrastructure/persistence/models/dossier.py` — добавить `case_id: Mapped[str]`.
- `src/application/dto/dossier_view_record.py` — +`case_id: str`.
- `src/infrastructure/persistence/repositories/dossier_repository.py` — `save()` принимает `case_id`, `get_view_by_id` селектит его.
- `src/infrastructure/persistence/mappers/dossier_mapper.py` — без правок (snapshot mapper, case_id передаётся напрямую).
- `src/interfaces/api/shared/dossier_storage.py` — добавить `allocator: CaseIdAllocatorPort` в `DossierStorage`.
- `src/interfaces/api/shared/dossier.py` — `manual_input_dossier` аллоцирует case_id перед save.
- `src/interfaces/api/shared/dossier_mapper.py` — drop `_application_id`, использовать `view.case_id`.
- `src/infrastructure/reports/pdf/pdf_renderer.py` — drop `_format_application_id`, читать `view.case_id`.

**Backend — tests modify:**
- `tests/integration/persistence/snapshot_dossier_repository_test.py`
- `tests/integration/persistence/dossier_view_repository_test.py`
- `tests/integration/persistence/dossier_source_mode_test.py`
- `tests/integration/api/bank_search_test.py`
- `tests/integration/api/bank_stats_test.py`
- `tests/integration/api/dossier_get_test.py`
- `scripts/seed_demo_borrowers.py`

**Frontend — delete:**
- `web/src/features/manual-input/lib/case-id.ts`
- `web/src/features/manual-input/lib/case-id.test.ts`

**Frontend — modify:**
- `web/src/features/manual-input/manual-input-view.tsx` (drop import + useMemo, pass null)

**Docs:**
- `CLAUDE.md` — Active task → next, T1.1 status closed.
- `docs/pre-demo-roadmap.md` — T1.1 → DONE с commit hash.

---

## Task 1: Alembic migration — sequence + column + backfill

**Files:**
- Create: `src/infrastructure/persistence/migrations/versions/20260518_1500_dossier_case_id_sequence.py`

**Why:** Migration атомарно создаёт sequence, добавляет nullable column, backfill'ит existing rows partition-by-year ASC по created_at, ставит NOT NULL+UNIQUE, синхронизирует sequence с MAX seq текущего года.

- [ ] **Step 1.1: Создать миграцию**

```python
"""T1.1 — dossier_case_id sequence (compromised B)

Revision ID: b3e9f1a7d4c5
Revises: a1f3c5e8b9d2
Create Date: 2026-05-18 15:00:00.000000+00:00

Заменяет derived BR-YYYY-XXXX (от UUID first-4-hex) на monotonic sequence
per-year. Backfill: existing dossiers нумеруются ASC по created_at в их
году (ROW_NUMBER() OVER PARTITION BY year). После backfill setval'им
sequence на (max_seq_current_year), чтобы первый allocate после миграции
взял MAX+1.

Format: BR-{YYYY}-{NNNN} (4 цифры zfill). UNIQUE constraint глобальный
(не per-year) — sequence гарантирует отсутствие коллизий, UNIQUE — defence
in depth и FK-target в будущем (Phase 4 applications).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e9f1a7d4c5"
down_revision: str | None = "a1f3c5e8b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS dossier_case_seq START WITH 1")

    op.add_column(
        "dossiers",
        sa.Column("case_id", sa.String(20), nullable=True),
    )

    # Backfill per-year ASC по created_at. ROW_NUMBER даёт monotonic
    # nnnn в пределах года, tiebreaker по id для детерминизма при
    # совпадающем created_at.
    op.execute(
        """
        WITH numbered AS (
            SELECT id,
                   EXTRACT(YEAR FROM created_at)::int AS yr,
                   ROW_NUMBER() OVER (
                       PARTITION BY EXTRACT(YEAR FROM created_at)
                       ORDER BY created_at, id
                   ) AS rn
            FROM dossiers
        )
        UPDATE dossiers d
        SET case_id = 'BR-' || numbered.yr::text || '-'
                      || LPAD(numbered.rn::text, 4, '0')
        FROM numbered
        WHERE d.id = numbered.id
        """
    )

    op.alter_column("dossiers", "case_id", nullable=False)
    op.create_unique_constraint("uq_dossiers_case_id", "dossiers", ["case_id"])
    op.create_index("ix_dossiers_case_id", "dossiers", ["case_id"])

    # Setval sequence на MAX seq текущего года (CURRENT_DATE по UTC через
    # CURRENT_DATE в alembic). is_called=false → next nextval вернёт N.
    # Если current-year rows нет — next nextval = 1.
    op.execute(
        """
        SELECT setval(
            'dossier_case_seq',
            GREATEST(1, COALESCE((
                SELECT MAX(SUBSTRING(case_id FROM 9 FOR 4)::int) + 1
                FROM dossiers
                WHERE SUBSTRING(case_id FROM 4 FOR 4)::int
                      = EXTRACT(YEAR FROM CURRENT_DATE)::int
            ), 1)),
            false
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_dossiers_case_id", table_name="dossiers")
    op.drop_constraint("uq_dossiers_case_id", "dossiers", type_="unique")
    op.drop_column("dossiers", "case_id")
    op.execute("DROP SEQUENCE IF EXISTS dossier_case_seq")
```

- [ ] **Step 1.2: Применить миграцию в Docker**

```bash
docker compose exec -T api bash -c "cd /app/src && uv run --no-sync alembic upgrade head"
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade a1f3c5e8b9d2 -> b3e9f1a7d4c5, T1.1 — dossier_case_id sequence (compromised B)`. Existing 5 dossiers получают `BR-2026-0001..0005`.

- [ ] **Step 1.3: Smoke-проверка существующих case_id**

```bash
docker compose exec -T postgres psql -U postgres -d credit -c "SELECT id, case_id, created_at FROM dossiers ORDER BY created_at;"
```

Expected: 5 строк с `case_id` BR-2026-0001..BR-2026-0005, monotonic ASC по `created_at`.

---

## Task 2: ORM model — case_id column

**Files:**
- Modify: `src/infrastructure/persistence/models/dossier.py`

- [ ] **Step 2.1: Добавить `case_id` mapped_column**

После `rules_evaluated`, перед `source_mode`:

```python
    case_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
```

`__table_args__` — индекс уже создан в migration (`ix_dossiers_case_id`), в ORM дублировать не надо (Alembic source-of-truth).

- [ ] **Step 2.2: ruff + mypy на модель**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check src/infrastructure/persistence/models/dossier.py && uv run python -m mypy --strict src/infrastructure/persistence/models/dossier.py"
```

Expected: 0 errors.

---

## Task 3: CaseIdAllocatorPort (application port)

**Files:**
- Create: `src/application/ports/case_id_allocator_port.py`

- [ ] **Step 3.1: Создать порт**

```python
"""CaseIdAllocatorPort: контракт аллокатора банковского case_id."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class CaseIdAllocatorPort(Protocol):
    """Выдаёт monotonic case_id `BR-{YYYY}-{NNNN}` под текущий год.

    Реализация обязана быть race-safe при параллельных аллокациях в одной
    транзакции через advisory lock — иначе year rollover может выдать
    дубликаты.
    """

    async def allocate(self, now: datetime) -> str:
        """Возвращает следующий case_id для года ``now.year``.

        ``now`` инжектируется (не ``datetime.now()`` внутри), чтобы:
        * тесты задавали детерминированный год без monkeypatch;
        * вызывающий мог использовать ту же временную точку, что и
          ``created_at`` записи (атомарность year-семантики).
        """
        ...
```

- [ ] **Step 3.2: ruff + mypy**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check src/application/ports/case_id_allocator_port.py && uv run python -m mypy --strict src/application/ports/case_id_allocator_port.py"
```

Expected: 0 errors.

---

## Task 4: CaseIdAllocator unit tests (red)

**Files:**
- Create: `src/application/services/case_id_allocator_test.py`

**Why:** Pure-Python unit с mock session проверяет format строки и формулу year-rollover (логика без БД). Integration тест в Task 6 проверяет реальный advisory lock + sequence.

- [ ] **Step 4.1: Написать падающие тесты**

```python
"""Unit-тесты CaseIdAllocator на mock-сессии.

Проверяем формат строки, проброс year, выбор reset vs no-reset. Реальная
advisory-lock семантика проверяется в integration-тесте на testcontainers
(см. tests/integration/persistence/case_id_allocator_test.py).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.services.case_id_allocator import SqlAlchemyCaseIdAllocator


def _make_session(*, max_year: int | None, nextval: int) -> Any:
    """Stub session: 3 execute-вызова (lock, max_year query, nextval/reset).

    Возвращает session, в котором ``execute`` отдаёт mock-result с правильным
    ``.scalar_one_or_none()`` / ``.scalar_one()`` в нужном порядке.
    """
    session = MagicMock()
    results: list[Any] = []

    # SELECT pg_advisory_xact_lock(...) — возвращает void, scalar не читается.
    results.append(MagicMock())
    # SELECT MAX(...) — max_year.
    max_result = MagicMock()
    max_result.scalar_one_or_none.return_value = max_year
    results.append(max_result)
    # Если нужен ALTER SEQUENCE — будет третий execute без scalar.
    # Потом nextval.
    nextval_result = MagicMock()
    nextval_result.scalar_one.return_value = nextval
    # Порядок execute зависит от ветки — заполним обе.
    results.append(MagicMock())  # ALTER SEQUENCE (или nextval если не было reset)
    results.append(nextval_result)

    session.execute = AsyncMock(side_effect=results)
    return session


@pytest.mark.asyncio
async def test_allocate_first_ever_dossier_resets_to_1() -> None:
    """Нет dossiers — max_year=None → reset, seq=1, BR-{year}-0001."""
    session = _make_session(max_year=None, nextval=1)
    allocator = SqlAlchemyCaseIdAllocator(session)
    case_id = await allocator.allocate(datetime(2026, 5, 18, 12, 0, 0))
    assert case_id == "BR-2026-0001"


@pytest.mark.asyncio
async def test_allocate_same_year_no_reset() -> None:
    """max_year=2026, now.year=2026 → no reset, seq=42, BR-2026-0042."""
    session = MagicMock()
    lock_result = MagicMock()
    max_result = MagicMock()
    max_result.scalar_one_or_none.return_value = 2026
    nextval_result = MagicMock()
    nextval_result.scalar_one.return_value = 42
    session.execute = AsyncMock(side_effect=[lock_result, max_result, nextval_result])

    allocator = SqlAlchemyCaseIdAllocator(session)
    case_id = await allocator.allocate(datetime(2026, 5, 18, 12, 0, 0))
    assert case_id == "BR-2026-0042"
    # 3 execute (lock, max query, nextval) — БЕЗ ALTER SEQUENCE.
    assert session.execute.await_count == 3


@pytest.mark.asyncio
async def test_allocate_new_year_resets_sequence() -> None:
    """max_year=2026, now.year=2027 → reset → seq=1, BR-2027-0001."""
    session = MagicMock()
    lock_result = MagicMock()
    max_result = MagicMock()
    max_result.scalar_one_or_none.return_value = 2026
    alter_result = MagicMock()
    nextval_result = MagicMock()
    nextval_result.scalar_one.return_value = 1
    session.execute = AsyncMock(
        side_effect=[lock_result, max_result, alter_result, nextval_result]
    )

    allocator = SqlAlchemyCaseIdAllocator(session)
    case_id = await allocator.allocate(datetime(2027, 1, 1, 0, 0, 0))
    assert case_id == "BR-2027-0001"
    # 4 execute: lock, max query, ALTER SEQUENCE, nextval.
    assert session.execute.await_count == 4


@pytest.mark.asyncio
async def test_allocate_zfill_to_4_digits() -> None:
    """seq=7 → '0007', seq=9999 → '9999'."""
    for seq, expected_suffix in [(7, "0007"), (123, "0123"), (9999, "9999")]:
        session = MagicMock()
        lock_result = MagicMock()
        max_result = MagicMock()
        max_result.scalar_one_or_none.return_value = 2026
        nextval_result = MagicMock()
        nextval_result.scalar_one.return_value = seq
        session.execute = AsyncMock(
            side_effect=[lock_result, max_result, nextval_result]
        )

        allocator = SqlAlchemyCaseIdAllocator(session)
        case_id = await allocator.allocate(datetime(2026, 5, 18))
        assert case_id == f"BR-2026-{expected_suffix}"
```

- [ ] **Step 4.2: Запустить — ожидаем fail (модуль не существует)**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest src/application/services/case_id_allocator_test.py -v"
```

Expected: `ModuleNotFoundError: No module named 'application.services.case_id_allocator'`.

---

## Task 5: CaseIdAllocator implementation (green)

**Files:**
- Create: `src/application/services/case_id_allocator.py`

- [ ] **Step 5.1: Реализация**

```python
"""SqlAlchemyCaseIdAllocator: monotonic case_id с year-rollover.

Алгоритм (внутри текущей транзакции):
1. ``pg_advisory_xact_lock(year)`` — serializes конкурентные аллокации
   для одного года (lock освобождается на commit/rollback).
2. Читает ``MAX(year)`` из всех существующих case_id. Если ``now.year``
   больше — делает ``ALTER SEQUENCE ... RESTART WITH 1`` (year boundary).
3. ``SELECT nextval('dossier_case_seq')`` — atomic.
4. Форматирует ``BR-{year}-{seq:04d}``.

Trade-off: lock per-year means same-year writes сериализуются. Для bank-
internal tool с <10 досье/час это незаметно. Альтернатива (counter table +
UPSERT RETURNING) проще, но roadmap T1.1 зафиксировал sequence-подход.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyCaseIdAllocator:
    """Реализация ``CaseIdAllocatorPort`` поверх Postgres SEQUENCE + advisory lock."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def allocate(self, now: datetime) -> str:
        year = now.year

        # Advisory transactional lock: один год — один поток. Освобождается
        # на commit/rollback, ничего вручную чистить не нужно.
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:k)"), {"k": year}
        )

        # MAX year среди уже выданных case_id. NULL — таблица пуста.
        max_year_row = await self._session.execute(
            text(
                "SELECT MAX(SUBSTRING(case_id FROM 4 FOR 4)::int) FROM dossiers"
            )
        )
        max_year: int | None = max_year_row.scalar_one_or_none()

        if max_year is None or year > max_year:
            # Year rollover (или первая аллокация в БД) — sequence
            # начинается с 1. RESTART синхронизирует с любым внешним
            # bump (setval из миграции тоже идемпотентно).
            await self._session.execute(
                text("ALTER SEQUENCE dossier_case_seq RESTART WITH 1")
            )

        seq_row = await self._session.execute(
            text("SELECT nextval('dossier_case_seq')")
        )
        seq: int = seq_row.scalar_one()
        return f"BR-{year}-{seq:04d}"
```

- [ ] **Step 5.2: Запустить unit-тесты — green**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest src/application/services/case_id_allocator_test.py -v"
```

Expected: 5 passed (3 + zfill параметризованных).

---

## Task 6: CaseIdAllocator integration tests (testcontainers)

**Files:**
- Create: `tests/integration/persistence/case_id_allocator_test.py`

**Why:** Unit-тест не проверяет реальный advisory lock + sequence. Integration на testcontainers Postgres ловит:
- Backfill round-trip (миграция сама поднимается testcontainers'ом).
- Same-year аллокация monotonic.
- Year rollover reset.
- Параллельные транзакции на year boundary не выдают дубль.

- [ ] **Step 6.1: Найти существующий testcontainers conftest**

```bash
grep -r "pg_session" tests/integration/persistence/ -l
```

Expected: список тестов с фикстурой `pg_session` (например `snapshot_dossier_repository_test.py`).

- [ ] **Step 6.2: Написать integration-тесты**

```python
"""Integration: CaseIdAllocator на реальном Postgres через testcontainers.

Покрывает то, что unit на mock-session дать не может:
* Backfill из миграции выдаёт ASC по created_at.
* nextval после backfill стартует с MAX+1.
* Year rollover внутри новой транзакции делает RESTART корректно.
* Параллельные аллокации в одной транзакции (последовательный вызов
  внутри одной session) дают monotonic без collision'ов.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.case_id_allocator import SqlAlchemyCaseIdAllocator
from domain.entities.red_flag import FlagCategory, FlagSeverity, FiringEvidence, RedFlag
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.dossier import DossierORM


def _new_dossier_row(
    *,
    case_id: str,
    snapshot_id,
    created_at: datetime,
) -> DossierORM:
    return DossierORM(
        id=uuid4(),
        snapshot_id=snapshot_id,
        score=0,
        recommendation="approve",
        severity_breakdown={},
        red_flags=[],
        rules_version="v1",
        rules_evaluated=0,
        source_mode="accountant",
        created_by_analyst_id=None,
        case_id=case_id,
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_allocate_first_ever_returns_0001(
    pg_session: AsyncSession,
) -> None:
    """Чистая БД (testcontainer fresh): первый allocate → BR-{now.year}-0001."""
    allocator = SqlAlchemyCaseIdAllocator(pg_session)
    case_id = await allocator.allocate(datetime(2026, 5, 18, tzinfo=UTC))
    assert case_id == "BR-2026-0001"


@pytest.mark.asyncio
async def test_allocate_monotonic_same_year(
    pg_session: AsyncSession,
) -> None:
    """Три allocate подряд same-year → 0001, 0002, 0003."""
    allocator = SqlAlchemyCaseIdAllocator(pg_session)
    ids = [
        await allocator.allocate(datetime(2026, 5, 18, tzinfo=UTC))
        for _ in range(3)
    ]
    assert ids == ["BR-2026-0001", "BR-2026-0002", "BR-2026-0003"]


@pytest.mark.asyncio
async def test_allocate_year_rollover_resets(
    pg_session: AsyncSession,
    seeded_borrower_and_snapshot: tuple,
) -> None:
    """После BR-2026-0042 в БД, allocate с now.year=2027 → BR-2027-0001."""
    _, snapshot_id = seeded_borrower_and_snapshot
    pg_session.add(
        _new_dossier_row(
            case_id="BR-2026-0042",
            snapshot_id=snapshot_id,
            created_at=datetime(2026, 12, 31, 23, 0, tzinfo=UTC),
        )
    )
    await pg_session.flush()
    # Sequence из миграции стоит на 1 (фреш контейнер), для теста явно
    # подталкиваем до 42, имитируя «42 досье аллоцировано в 2026».
    await pg_session.execute(text("SELECT setval('dossier_case_seq', 42, true)"))

    allocator = SqlAlchemyCaseIdAllocator(pg_session)
    case_id = await allocator.allocate(datetime(2027, 1, 1, tzinfo=UTC))
    assert case_id == "BR-2027-0001"


@pytest.mark.asyncio
async def test_allocate_continues_after_rollover(
    pg_session: AsyncSession,
    seeded_borrower_and_snapshot: tuple,
) -> None:
    """После BR-2027-0001 второй allocate same-year → BR-2027-0002 (без повторного reset)."""
    _, snapshot_id = seeded_borrower_and_snapshot
    pg_session.add(
        _new_dossier_row(
            case_id="BR-2027-0001",
            snapshot_id=snapshot_id,
            created_at=datetime(2027, 1, 1, tzinfo=UTC),
        )
    )
    await pg_session.flush()
    await pg_session.execute(text("SELECT setval('dossier_case_seq', 1, true)"))

    allocator = SqlAlchemyCaseIdAllocator(pg_session)
    case_id = await allocator.allocate(datetime(2027, 1, 2, tzinfo=UTC))
    assert case_id == "BR-2027-0002"
```

**Note по фикстуре `seeded_borrower_and_snapshot`:** если её ещё нет — взять паттерн из `tests/integration/persistence/snapshot_dossier_repository_test.py` (там создаётся borrower + snapshot inline). Сделать helper-функцию в этом же файле, либо положить в conftest.py если нет. Не вытаскивать в новый conftest без нужды.

- [ ] **Step 6.3: Запустить integration**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest tests/integration/persistence/case_id_allocator_test.py -v"
```

Expected: 4 passed.

---

## Task 7: DossierViewRecord — case_id field

**Files:**
- Modify: `src/application/dto/dossier_view_record.py`

- [ ] **Step 7.1: Добавить поле**

После `created_at`:

```python
@dataclass(frozen=True, slots=True)
class DossierViewRecord:
    dossier_id: UUID
    dossier: DossierRecord
    snapshot: BorrowerSnapshot
    created_at: datetime
    case_id: str
```

Docstring файла: добавить в abstract block упоминание `case_id` — банковский id `BR-YYYY-NNNN`, аллоцированный allocator'ом при сохранении.

- [ ] **Step 7.2: mypy**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m mypy --strict src/application/dto/dossier_view_record.py"
```

Expected: 0 errors (file-level). Cross-file ошибки в репо/маппере поедут на следующих шагах.

---

## Task 8: SqlAlchemyDossierRepository — save принимает case_id, get_view_by_id селектит

**Files:**
- Modify: `src/infrastructure/persistence/repositories/dossier_repository.py`
- Modify: `src/application/ports/dossier_repository_port.py`

- [ ] **Step 8.1: Расширить порт `save()` обязательным `case_id`**

```python
    async def save(
        self,
        record: DossierRecord,
        snapshot_id: UUID,
        case_id: str,
        *,
        source_mode: str = "accountant",
        created_by_analyst_id: UUID | None = None,
    ) -> UUID:
```

Docstring обновить: `case_id` — банковский id `BR-YYYY-NNNN`, выдан `CaseIdAllocator`'ом вызывающим use-case'ом. Не дефолтится, чтобы forget'нуть allocator стало compile-time ошибкой.

- [ ] **Step 8.2: Реализация `save()` в `SqlAlchemyDossierRepository`**

```python
    async def save(
        self,
        record: DossierRecord,
        snapshot_id: UUID,
        case_id: str,
        *,
        source_mode: str = "accountant",
        created_by_analyst_id: UUID | None = None,
    ) -> UUID:
        new_id = uuid4()
        orm = DossierORM(
            id=new_id,
            snapshot_id=snapshot_id,
            score=record.score,
            recommendation=record.recommendation,
            severity_breakdown=dict(record.severity_breakdown),
            red_flags=red_flags_to_jsonb(record.red_flags),
            rules_version=record.rules_version,
            rules_evaluated=record.rules_evaluated,
            source_mode=source_mode,
            created_by_analyst_id=created_by_analyst_id,
            case_id=case_id,
        )
        self._session.add(orm)
        await self._session.flush()
        return new_id
```

- [ ] **Step 8.3: `get_view_by_id` пробрасывает `case_id`**

В функции `get_view_by_id` после `dossier_record = ...`:

```python
        return DossierViewRecord(
            dossier_id=dossier_orm.id,
            dossier=dossier_record,
            snapshot=snapshot,
            created_at=dossier_orm.created_at,
            case_id=dossier_orm.case_id,
        )
```

- [ ] **Step 8.4: mypy на репо + порт**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m mypy --strict src/application/ports/dossier_repository_port.py src/infrastructure/persistence/repositories/dossier_repository.py"
```

Expected: 0 errors.

---

## Task 9: Wire allocator в `manual_input_dossier` endpoint

**Files:**
- Modify: `src/interfaces/api/shared/dossier_storage.py`
- Modify: `src/interfaces/api/shared/dossier.py`

- [ ] **Step 9.1: Расширить `DossierStorage`**

В `dossier_storage.py` добавить allocator в dataclass + конструктор:

```python
from application.ports.case_id_allocator_port import CaseIdAllocatorPort
from application.services.case_id_allocator import SqlAlchemyCaseIdAllocator

# ...

@dataclass(frozen=True, slots=True)
class DossierStorage:
    borrower: BorrowerRepositoryPort
    snapshot: BorrowerSnapshotRepositoryPort
    dossier: DossierRepositoryPort
    draft: DraftRepositoryPort
    case_id_allocator: CaseIdAllocatorPort


async def get_dossier_storage(session: SessionDep) -> DossierStorage:
    return DossierStorage(
        borrower=SqlAlchemyBorrowerRepository(session),
        snapshot=SqlAlchemyBorrowerSnapshotRepository(session),
        dossier=SqlAlchemyDossierRepository(session),
        draft=SqlAlchemyDraftRepository(session),
        case_id_allocator=SqlAlchemyCaseIdAllocator(session),
    )
```

- [ ] **Step 9.2: Аллоцировать case_id в `dossier.py`**

В `manual_input_dossier()` после snapshot save и перед dossier save:

```python
    from datetime import UTC, datetime
    now = datetime.now(UTC)
    case_id = await storage.case_id_allocator.allocate(now)

    source_mode = "bank" if analyst is not None else "accountant"
    dossier_id = await storage.dossier.save(
        record,
        snapshot_id,
        case_id,
        source_mode=source_mode,
        created_by_analyst_id=analyst.id if analyst is not None else None,
    )
```

`datetime.now(UTC)` импортируется в top-level (не функцию) для чистоты imports.

- [ ] **Step 9.3: mypy на оба файла**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m mypy --strict src/interfaces/api/shared/dossier_storage.py src/interfaces/api/shared/dossier.py"
```

Expected: 0 errors.

---

## Task 10: dossier_mapper — drop derived, читать `view.case_id`

**Files:**
- Modify: `src/interfaces/api/shared/dossier_mapper.py`

- [ ] **Step 10.1: Удалить функцию `_application_id` (lines 288-299)**

Целиком убрать helper. И импорт `datetime` пересмотреть — он может быть нужен ещё где-то, оставить если да.

- [ ] **Step 10.2: Заменить call site (line 367-368)**

В `build_dossier_view_response`:

```python
        application=ApplicationOutput(
            id=view.case_id,
            status="in_review",
        ),
```

- [ ] **Step 10.3: mypy**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m mypy --strict src/interfaces/api/shared/dossier_mapper.py"
```

Expected: 0 errors.

---

## Task 11: PDF renderer — drop `_format_application_id`, читать из view.case_id

**Files:**
- Modify: `src/infrastructure/reports/pdf/pdf_renderer.py`

- [ ] **Step 11.1: Заменить call в `_build_context` (line ~120)**

```python
        application_id = view.case_id
```

- [ ] **Step 11.2: Удалить функцию `_format_application_id` (lines 199-202)**

Целиком убрать helper.

- [ ] **Step 11.3: mypy**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m mypy --strict src/infrastructure/reports/pdf/pdf_renderer.py"
```

Expected: 0 errors.

---

## Task 12: Обновить integration-тесты на новую сигнатуру save()

**Files:**
- Modify: `tests/integration/persistence/snapshot_dossier_repository_test.py`
- Modify: `tests/integration/persistence/dossier_view_repository_test.py`
- Modify: `tests/integration/persistence/dossier_source_mode_test.py`
- Modify: `tests/integration/api/bank_search_test.py`
- Modify: `tests/integration/api/bank_stats_test.py`
- Modify: `tests/integration/api/dossier_get_test.py`
- Modify: `scripts/seed_demo_borrowers.py`

**Pattern:** каждый `dossier_repo.save(record, snapshot_id, ...)` получает 3-й позиционный `case_id`. В тестах генерируем уникальные через counter или random:

```python
import secrets
case_id = f"BR-2026-{secrets.token_hex(2).upper()}"
```

Либо ввести test-helper `_test_case_id(year=2026, n=...)`. Использую `secrets.token_hex(2)` подход — не вводим shared helper ради одной строки в файле, копируем.

- [ ] **Step 12.1: `snapshot_dossier_repository_test.py:102`**

```python
    dossier_id = await dossier_repo.save(record, snapshot_id, "BR-2026-A001")
```

- [ ] **Step 12.2: `dossier_view_repository_test.py:65`**

```python
    dossier_id = await dossier_repo.save(record, snapshot_id, "BR-2026-A002")
```

Также в этом файле проверка `view.case_id`: добавить ассерт после `assert view is not None`:

```python
    assert view.case_id == "BR-2026-A002"
```

- [ ] **Step 12.3: `dossier_source_mode_test.py:48, 69, 91-93`**

```python
    # line 48
    dossier_id = await dossier_repo.save(_record(), snapshot_id, "BR-2026-B001")
    # line 69
    dossier_id = await dossier_repo.save(
        _record(),
        snapshot_id,
        "BR-2026-B002",
        source_mode="bank",
        created_by_analyst_id=analyst_id,
    )
    # lines 91-93
    await dossier_repo.save(_record(), snapshot_id, "BR-2026-B003", source_mode="accountant")
    await dossier_repo.save(_record(), snapshot_id, "BR-2026-B004", source_mode="bank")
    await dossier_repo.save(_record(), snapshot_id, "BR-2026-B005", source_mode="bank")
```

- [ ] **Step 12.4: `bank_search_test.py:148, 150-155, 157-162`**

Уникальные case_id per save:

```python
    await dossier_repo.save(_record(score=10), snapshot_id, "BR-2026-C001", source_mode="accountant")
    await dossier_repo.save(
        _record(score=20),
        snapshot_id,
        "BR-2026-C002",
        source_mode="bank",
        created_by_analyst_id=analyst.id,
    )
    latest_id = await dossier_repo.save(
        _record(score=30),
        snapshot_id,
        "BR-2026-C003",
        source_mode="bank",
        created_by_analyst_id=analyst.id,
    )
```

- [ ] **Step 12.5: `bank_stats_test.py:124-126, 149-150, 168`**

```python
    # 124-126
    await repo.save(_record("approve"), snapshot_id, "BR-2026-D001", source_mode="bank", created_by_analyst_id=aid)
    await repo.save(_record("approve"), snapshot_id, "BR-2026-D002", source_mode="bank", created_by_analyst_id=aid)
    await repo.save(_record("review"), snapshot_id, "BR-2026-D003", source_mode="bank", created_by_analyst_id=aid)
    # 149-150
    await repo.save(_record("approve"), snapshot_id, "BR-2026-D004", source_mode="accountant")
    await repo.save(_record("approve"), snapshot_id, "BR-2026-D005", source_mode="accountant")
    # 168
    await repo.save(_record("approve"), snapshot_id, "BR-2026-D006", source_mode="bank")
```

- [ ] **Step 12.6: `dossier_get_test.py` — assertion на `BR-` остаётся, но теперь это allocator's output**

Файл вызывает POST /api/manual-input — case_id выдаст allocator. Assertion `app["id"].startswith("BR-")` уже корректен. Дополнительно проверить format strict:

```python
    import re
    assert re.fullmatch(r"BR-\d{4}-\d{4}", app["id"]), f"unexpected case_id format: {app['id']}"
    assert app["status"] == "in_review"
```

Заменить line 114-115:

```python
    # Application: id вида BR-YYYY-NNNN, status пока всегда in_review.
    app = body["application"]
    import re
    assert re.fullmatch(r"BR-\d{4}-\d{4}", app["id"]), f"unexpected case_id format: {app['id']}"
    assert app["status"] == "in_review"
```

(Импорт `re` лучше вынести в top-level файла, если в нём ещё не было.)

- [ ] **Step 12.7: `scripts/seed_demo_borrowers.py:274-279`**

Seed-скрипт идёт по списку демо-borrowers; добавить allocator + per-call case_id:

```python
            from application.services.case_id_allocator import SqlAlchemyCaseIdAllocator
            allocator = SqlAlchemyCaseIdAllocator(session)
            from datetime import UTC, datetime
            case_id = await allocator.allocate(datetime.now(UTC))
            dossier_id = await dossier_repo.save(
                record,
                snapshot_id,
                case_id,
                source_mode="bank",
                created_by_analyst_id=None,
            )
```

Imports вынести в head файла.

- [ ] **Step 12.8: Запустить полный backend test-сьют**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest -x"
```

Expected: 0 failures. Если что-то падает — фиксим pre-commit (никаких `-k skip`).

---

## Task 13: Frontend — drop derived helper

**Files:**
- Delete: `web/src/features/manual-input/lib/case-id.ts`
- Delete: `web/src/features/manual-input/lib/case-id.test.ts`
- Modify: `web/src/features/manual-input/manual-input-view.tsx`

- [ ] **Step 13.1: Удалить helper + тест**

```bash
rm web/src/features/manual-input/lib/case-id.ts
rm web/src/features/manual-input/lib/case-id.test.ts
```

- [ ] **Step 13.2: Очистить `manual-input-view.tsx`**

В шапке файла удалить:

```tsx
import { formatCaseId } from "./lib/case-id";
```

В теле компонента удалить useMemo (lines 99-106 диапазон, целиком блок с комментом CA-DS18):

```tsx
  const caseId = useMemo(() => formatCaseId(draft.draftId), [draft.draftId]);
```

И комменты выше (`// CA-DS18 Level 1: caseId ...` до строки про hydration-safe). Заменить на однострочный коммент:

```tsx
  // T1.1: case_id выдаёт backend allocator на successful dossier create.
  // Pre-submit pill показывает «—» — placeholder до allocation.
```

Заменить `<PageHead caseId={caseId} step={step} />` → `<PageHead caseId={null} step={step} />`.

Проверить — если `useMemo` больше нигде не используется в файле, убрать его из импорта `react`.

- [ ] **Step 13.3: Запустить vitest + tsc**

```bash
cd web && npm run test -- --run && npx tsc --noEmit
```

Expected: 0 failed tests, 0 tsc errors. Counter тестов уменьшится на 8 (бывшие тесты case-id).

---

## Task 14: Full verify (backend + frontend + e2e smoke)

- [ ] **Step 14.1: Backend full pipeline**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest"
```

Expected: ruff clean, mypy clean, pytest all green.

- [ ] **Step 14.2: Frontend full pipeline**

```bash
cd web && npm run lint && npx tsc --noEmit && npm run test -- --run && npm run build
```

Expected: 0 errors, build success.

- [ ] **Step 14.3: Live-smoke в браузере (manual)**

Запустить dev-сервер фронта если не поднят:

```bash
cd web && npm run dev
```

Открыть `http://localhost:3000/manual-input`:
- Pill в page-head показывает «—» (был динамический `BR-2026-XXXX`).
- Дойти до Step 3, нажать «Собрать досье».
- На экране досье pill в sub-header показывает `BR-2026-NNNN` (allocator-выданный).
- Скачать PDF, открыть — footer / cover / page-footer показывают тот же case_id.

Если в проде уже 5 dossiers со старым derived форматом — после миграции у них теперь backfilled BR-2026-0001..0005. Открыть `/history`, проверить consistency.

- [ ] **Step 14.4: Записать команду-верификатор (project rule)**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -c \"
import asyncio
from datetime import UTC, datetime
from infrastructure.persistence.database import async_session_factory
from application.services.case_id_allocator import SqlAlchemyCaseIdAllocator

async def main():
    async with async_session_factory() as s:
        a = SqlAlchemyCaseIdAllocator(s)
        ids = [await a.allocate(datetime.now(UTC)) for _ in range(3)]
        await s.rollback()  # не сохраняем — это smoke
        print('[OK] allocated:', ids)

asyncio.run(main())
\""
```

Expected: `[OK] allocated: ['BR-2026-NNNN', 'BR-2026-NNNN+1', 'BR-2026-NNNN+2']` где NNNN — следующий после backfill'нутого MAX (для 5 existing dossiers — будет 0006, 0007, 0008). После rollback ничего в БД не сохранено, но advisory lock + sequence работают.

---

## Task 15: Docs sync + atomic commit

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/pre-demo-roadmap.md`

- [ ] **Step 15.1: Обновить `docs/pre-demo-roadmap.md`**

Перенести T1.1 из «active» в «closed» (выше T0):

```markdown
### T1.1 — case_id monotonic sequence (CA-DS18b/c) ✅ DONE 2026-05-18 (commit <HASH>)

Compromised B: sequence на `dossiers` table. Постдемо миграция case_id на applications через FK без потерь.

- ✅ Alembic migration `b3e9f1a7d4c5`: CREATE SEQUENCE + ADD COLUMN case_id VARCHAR(20) UNIQUE NOT NULL + backfill ROW_NUMBER per-year по created_at ASC + setval current year MAX+1.
- ✅ `CaseIdAllocator` (port + Sqlalchemy implementation) — advisory_xact_lock per-year, ALTER SEQUENCE RESTART на year boundary, nextval.
- ✅ DossierViewRecord +case_id; `dossier_repo.save(record, snapshot_id, case_id, ...)` обязательный позиционный.
- ✅ `dossier_mapper._application_id` и `pdf_renderer._format_application_id` удалены — оба читают `view.case_id` напрямую.
- ✅ Frontend `formatCaseId` helper + test удалены; `manual-input-view` рендерит «—» pre-submit.
- ✅ Closes CA-DS18b (banking sequence) + CA-DS18c (year edge).
```

Обновить header status: «**Tier 1 / T1.1 ✅ closed 2026-05-18**. Next active — T1.2 refresh-token rotation + Redis.»

- [ ] **Step 15.2: Обновить `CLAUDE.md` Current Status block**

Заменить «Active — T1.1 case_id monotonic sequence» на:

```markdown
**T1.1 (case_id monotonic sequence) complete 2026-05-18 (commit <HASH>).** Banking-grade sequence на `dossiers` table (compromised B без Phase 4 application entity). Existing 5 dossiers backfilled: BR-2026-0001..0005 по created_at ASC. Allocator через `pg_advisory_xact_lock(year)` + `ALTER SEQUENCE RESTART` на year boundary. Closes CA-DS18b/c.

**Active — T1.2 refresh-token rotation + Redis denylist (CA-019).** См. roadmap.
```

Smoke-target в Existing block обновить: `**BR-2026-0081**` → новый backfilled id (нужно проверить какой получит «кадр дон нон» после backfill — это самый ранний по created_at среди 5 dossiers, значит BR-2026-0001).

- [ ] **Step 15.3: Финальный verify перед коммитом**

```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest" && cd web && npm run lint && npx tsc --noEmit && npm run test -- --run
```

Expected: all green.

- [ ] **Step 15.4: Atomic commit**

```bash
git add src/infrastructure/persistence/migrations/versions/20260518_1500_dossier_case_id_sequence.py \
        src/infrastructure/persistence/models/dossier.py \
        src/application/ports/case_id_allocator_port.py \
        src/application/services/case_id_allocator.py \
        src/application/services/case_id_allocator_test.py \
        src/application/dto/dossier_view_record.py \
        src/application/ports/dossier_repository_port.py \
        src/infrastructure/persistence/repositories/dossier_repository.py \
        src/interfaces/api/shared/dossier_storage.py \
        src/interfaces/api/shared/dossier.py \
        src/interfaces/api/shared/dossier_mapper.py \
        src/infrastructure/reports/pdf/pdf_renderer.py \
        tests/integration/persistence/case_id_allocator_test.py \
        tests/integration/persistence/snapshot_dossier_repository_test.py \
        tests/integration/persistence/dossier_view_repository_test.py \
        tests/integration/persistence/dossier_source_mode_test.py \
        tests/integration/api/bank_search_test.py \
        tests/integration/api/bank_stats_test.py \
        tests/integration/api/dossier_get_test.py \
        scripts/seed_demo_borrowers.py \
        CLAUDE.md \
        docs/pre-demo-roadmap.md \
        docs/superpowers/plans/2026-05-18-t11-case-id-sequence.md

git rm web/src/features/manual-input/lib/case-id.ts \
       web/src/features/manual-input/lib/case-id.test.ts

git add web/src/features/manual-input/manual-input-view.tsx

git commit -m "$(cat <<'EOF'
feat(dossier): T1.1 case_id monotonic sequence (compromised B)

Заменён derived BR-YYYY-XXXX (первые 4 hex от dossier UUID) на банковский
monotonic sequence per-year. Sequence на dossiers table, не на Phase 4
application entity (compromised B per roadmap).

* Alembic migration b3e9f1a7d4c5: CREATE SEQUENCE dossier_case_seq,
  ADD COLUMN case_id VARCHAR(20) UNIQUE NOT NULL, backfill existing
  rows через ROW_NUMBER() OVER PARTITION BY year ORDER BY created_at,
  setval на MAX+1 для current year.
* CaseIdAllocator (port + sqlalchemy impl): advisory_xact_lock(year),
  read MAX year, ALTER SEQUENCE RESTART на year boundary, nextval.
* DossierViewRecord +case_id; repo.save принимает case_id обязательным
  позиционным аргументом.
* Удалены derived-helpers _application_id (dossier_mapper.py) и
  _format_application_id (pdf_renderer.py) — оба читают view.case_id.
* Frontend: удалены formatCaseId helper + test; manual-input-view
  рендерит '—' в case-pill до dossier create.

Acceptance:
* Existing 5 dossiers backfilled BR-2026-0001..0005 по created_at ASC.
* Новый dossier на 2026 → BR-2026-NNNN с monotonic NNNN.
* Создание dossier на 2027 reset'ит sequence на 1.
* Race-safety на year boundary через pg_advisory_xact_lock(year).

Closes CA-DS18b (banking sequence), CA-DS18c (year edge).
EOF
)"
```

- [ ] **Step 15.5: Push в origin/main**

```bash
git push origin main
```

CI должна стать зелёной. Если упадёт — диагностируем, не пуляем new commit поверх.

- [ ] **Step 15.6: ※ heads-up юзеру**

Коммит тронул migration + persistence model + repo signature + API mapper + PDF renderer + frontend. Smoke-target BR-2026-0081 больше не существует — после backfill это BR-2026-0001 (если «кадр дон нон» самое старое досье). Live-browser walkthrough в проде обязателен перед демо.

---

## Self-Review

**1. Spec coverage:**
- Scope items: migration ✅ (Task 1) · ORM ✅ (Task 2) · allocator ✅ (Tasks 3-6) · DTO ✅ (Task 7) · repo ✅ (Task 8) · use-case wiring ✅ (Task 9) · dossier_mapper ✅ (Task 10) · PDF renderer ✅ (Task 11) · tests update ✅ (Task 12) · frontend ✅ (Task 13) · verify ✅ (Task 14) · docs+commit ✅ (Task 15).
- Resolved decisions: (c) wizard placeholder pre-submit «—» ✅ (Task 13), advisory lock на year boundary ✅ (Task 5), drop formatCaseId+test ✅ (Task 13).

**2. Placeholder scan:** Нет TBD / TODO без ID / "implement later" / "add validation" / "similar to Task N" без кода.

**3. Type consistency:**
- `CaseIdAllocatorPort.allocate(now: datetime) -> str` — used identically в Tasks 3, 4, 5, 6, 9.
- `DossierRepositoryPort.save(record, snapshot_id, case_id, *, source_mode, created_by_analyst_id) -> UUID` — used identically в Tasks 8, 12, 9.
- `DossierViewRecord.case_id: str` — used в Task 7 definition + Task 10 + Task 11 + Task 8 read.

Plan is internally consistent. Approve to execute.
