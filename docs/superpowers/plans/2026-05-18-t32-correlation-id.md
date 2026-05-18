# T3.2 — Structured logging + correlation_id (CA-064 sibling)

> Foundation для T3.1 (Sentry tags) / T3.3 (Prometheus labels) / T3.5 (audit-export forensics).
> Без correlation_id любой prod-инцидент дебажится «по timestamp» — для compliance audit недостаточно.

## Decisions (approved 2026-05-18, defaults)

- **Header naming**: `X-Request-ID` (Heroku/AWS convention, короче чем `X-Correlation-ID`).
- **ID format**: `uuid.uuid4().hex` — 32 hex chars, проще grep, без dashes.
- **Echo back**: всегда — analyst видит ID в DevTools → передаёт в support. Info-leak risk нулевой (UUID не PII).
- **`audit_log.request_id` колонка**: включить в T3.2 (+1 atomic commit). Natural fit forensics — без request_id audit-trail неполный.
- **Middleware order**: до `CORSMiddleware`. Request_id bind происходит раньше → last-resort error handlers (если когда-то добавим exception middleware) получают context.

## Out of scope

- Frontend `error.tsx` correlation propagation — отдельный T3.x (вместе с Sentry на T3.1).
- OpenTelemetry / distributed tracing — overkill для single-process API.
- uvicorn access-log enrichment — uvicorn пишет свой формат, оставляем как есть (наш middleware всё равно проинжектит ID в app-level logs, которые покрывают всю бизнес-логику).
- `correlation_id` параметр в Python signatures — bind через `contextvars` транспарентно для всех call-sites.

## Foundation findings (pre-impl grep)

- `src/config/logging.py` — structlog уже включает `merge_contextvars` processor → `bind_contextvars(request_id=...)` автоматически попадает в structlog records без правок call-sites.
- 16 файлов используют stdlib `logging.getLogger(__name__)` (не structlog) — `merge_contextvars` их не видит. Нужен stdlib bridge через `logging.Filter`, читающий `structlog.contextvars.get_contextvars()`.
- `app.add_middleware(CORSMiddleware, ...)` — единственное existing middleware, в `interfaces/api/app.py:153`.
- `AuditLogORM` в `audit_log.py` — есть `payload` JSONB; добавляем nullable VARCHAR(32) колонку + index.

## Atomic split

### T3.2.1 — stdlib bridge + ContextvarsFilter (~3 файла)

**Файлы:**
1. `src/config/logging.py` — добавить `ContextvarsFilter(logging.Filter)`, который перед каждым record вызывает `structlog.contextvars.get_contextvars()` и инжектит каждый ключ в `record.__dict__` (через `setattr` чтобы JSON renderer его подобрал). Wire через `logging.config.dictConfig`: root logger получает stream handler с `structlog.stdlib.ProcessorFormatter`, использующим тот же processor chain (включая `merge_contextvars`).
2. `src/config/logging_test.py` (новый) — unit:
   - `test_stdlib_logger_without_bind_has_no_request_id` — logging.getLogger("test").info("foo") → captured record не содержит `request_id`.
   - `test_stdlib_logger_with_bind_emits_request_id` — `bind_contextvars(request_id="abc")` + `logger.info("foo")` → captured record has `request_id="abc"`.
   - `test_configure_logging_idempotent` — двойной вызов `configure_logging()` не падает (existing invariant).
   - `test_bind_clears_between_tests` — unbind в teardown работает (paranoia против test pollution).
3. `pyproject.toml` — без изменений (structlog уже в deps).

**TDD цикл:**
- Red 1: первый тест без Filter → assertion fails (нет request_id).
- Green 1: добавить ContextvarsFilter, wire через dictConfig.
- Red 2: idempotent test — двойной вызов configure_logging создаёт дублирующиеся handlers.
- Green 2: `dictConfig` с `disable_existing_loggers=False` + idempotent guard через module-level flag или handler.clear().

**Verify:**
```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest src/config/logging_test.py -v"
```

**Commit:** `feat(logging): T3.2.1 stdlib bridge for structlog contextvars`.

---

### T3.2.2 — RequestIDMiddleware (~3 файла)

**Файлы:**
1. `src/interfaces/api/middleware.py` (новый) — `RequestIDMiddleware(BaseHTTPMiddleware)`:
   - В `dispatch(request, call_next)`: читает `request.headers.get("X-Request-ID")`; если нет — `uuid.uuid4().hex`.
   - `structlog.contextvars.bind_contextvars(request_id=rid)` → `response = await call_next(request)` → `response.headers["X-Request-ID"] = rid`.
   - `try/finally structlog.contextvars.unbind_contextvars("request_id")` — чтобы между запросами context чистый.
2. `src/interfaces/api/middleware_test.py` (новый) — middleware unit:
   - `test_missing_header_generates_hex_uuid` — request без `X-Request-ID` → response[`X-Request-ID`] matches `^[0-9a-f]{32}$`.
   - `test_existing_header_echoed_back` — request с `X-Request-ID: foo123` → response[`X-Request-ID`] == `foo123`.
   - `test_bind_active_during_request` — handler видит `get_contextvars()["request_id"]` совпадающий с response header.
   - `test_unbind_after_response` — после ответа `get_contextvars()` не содержит `request_id`.
3. `src/interfaces/api/app.py` — `app.add_middleware(RequestIDMiddleware)` **перед** CORSMiddleware (помни: FastAPI middleware stack — LIFO, последний `add_middleware` выполняется первым на request). Чтобы RequestID был **outer** — добавить его **после** CORS, либо использовать порядок аккуратно. **Heads-up:** FastAPI добавляет middleware в обратном порядке — последний `add_middleware` обрабатывает request первым. Значит **RequestIDMiddleware = последний add_middleware** = outer = bind ДО CORS.

**TDD цикл:**
- Red 1: `test_missing_header_generates_hex_uuid` — middleware ещё не существует, ImportError.
- Green 1: создать middleware с auto-gen + echo.
- Red 2: `test_bind_active_during_request` — bind ещё не делаем.
- Green 2: добавить bind/unbind с try/finally.

**Verify:**
```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest src/interfaces/api/middleware_test.py -v"
```

**Commit:** `feat(api): T3.2.2 RequestIDMiddleware for X-Request-ID correlation`.

---

### T3.2.3 — Integration: request → log → captured request_id (~2 файла)

**Файлы:**
1. `tests/integration/correlation_id_propagation_test.py` (новый) — integration:
   - `test_request_id_propagates_to_app_logs` — FastAPI TestClient + caplog. GET `/api/system/health` без header → assert last app-log record (внутри health handler есть structlog.get_logger().info, либо instrumental log там же добавляем) has `request_id` matching response header.
   - `test_existing_request_id_propagates` — request с `X-Request-ID: deadbeef` → log has `request_id="deadbeef"`.
   - `test_request_ids_are_isolated_between_requests` — два sequential requests дают разные request_id в логах.
2. `src/interfaces/api/shared/health.py` — добавить `logger.info("health_check_started")` в handler (один log line, безвредный) — чтобы integration test имел что capture'ить. Если уже есть log — пропустить.

**Note:** caplog в pytest требует propagation на root logger. Если `dictConfig` отключил propagation — переопределить через `caplog.set_level(logging.INFO)` + assert через `caplog.records[-1].__dict__.get("request_id")`.

**TDD цикл:**
- Red 1: test fails — нет log line в health handler.
- Green 1: добавить `logger.info(...)` в health.py.
- Red 2: test fails — request_id не в record.
- Green 2: убедиться что middleware wired в `create_app` (если ещё не) — финальный wiring step.

**Verify:**
```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest tests/integration/correlation_id_propagation_test.py -v"
```

**Commit:** `feat(api): T3.2.3 wire RequestIDMiddleware into create_app + integration test`.

---

### T3.2.4 — `audit_log.request_id` колонка (~5 файлов)

**Файлы:**
1. Alembic migration `20260518_<timestamp>_audit_log_request_id.py`:
   - `op.add_column("audit_log", sa.Column("request_id", sa.String(32), nullable=True))`.
   - `op.create_index("ix_audit_log_request_id", "audit_log", ["request_id"])`.
   - Downgrade: drop index + drop column.
2. `src/infrastructure/persistence/models/audit_log.py` — `request_id: Mapped[str | None] = mapped_column(String(32), nullable=True)` + index в `__table_args__`.
3. `src/infrastructure/persistence/repositories/audit_log_repository.py` — `record()` дополнительно читает `structlog.contextvars.get_contextvars().get("request_id")` (best-effort, None для CLI/jobs/background tasks без middleware) и пишет в `orm.request_id`.
4. `tests/integration/persistence/audit_log_repository_test.py` (extend, либо новый если нет) — 2 теста:
   - `test_record_writes_request_id_from_contextvars` — `bind_contextvars(request_id="abc")` + repo.record(...) → row.request_id == "abc".
   - `test_record_without_request_id_keeps_null` — pristine context → row.request_id is None.
5. `tests/integration/test_audit_log_request_id_e2e.py` (новый, опционально — если выше юнит покрывает) — full E2E: TestClient request → audit-log row создаётся с request_id matching response header.

**TDD цикл:**
- Red: `test_record_writes_request_id_from_contextvars` — нет колонки → schema error либо attribute error на ORM model.
- Green: миграция + ORM колонка + repo update.

**Verify:**
```bash
docker compose exec -T api bash -c "cd /app/src && uv run --no-sync alembic upgrade head"
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m pytest tests/integration/persistence/audit_log_repository_test.py -v"
```

**Heads-up:** в Alembic downgrade проверить, что drop index идёт **до** drop column (PG требует именно такой порядок).

**Commit:** `feat(audit): T3.2.4 audit_log.request_id column from contextvars`.

---

### T3.2.5 — Docs sync (~3 файла)

**Файлы:**
1. `CLAUDE.md`:
   - Current Status: добавить bullet `**T3.2 (structured logging + correlation_id) complete 2026-05-18** (commits ...)` с deets (header X-Request-ID, hex32, audit_log.request_id, middleware order).
   - Tier 3 active list — `T3.2` → strikethrough, остальные 5 остаются.
2. `docs/pre-demo-roadmap.md` — Tier 3 section: `~~T3.2~~ → DONE 2026-05-18` с короткой ссылкой на commits + decisions snapshot.
3. (опционально) `docs/adr/` — **не нужен ADR**. Это standard pattern (X-Request-ID + contextvars), не architectural choice достойный записи. Если решим extend на frontend / Sentry tags — там ADR-0021 observability stack охватит.

**Commit:** `docs(internal): T3.2 status sync + correlation_id conventions`.

---

## Verify (full Pre-push checklist)

После каждого atomic commit:
```bash
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest"
```

И перед push на main: `gh run list --branch main -L 3` подтверждает зелёный baseline.

## Estimate

- T3.2.1 stdlib bridge — 1.5h
- T3.2.2 middleware — 1.5h
- T3.2.3 integration — 1h
- T3.2.4 audit_log column — 1.5h
- T3.2.5 docs — 0.5h

**Total: ~6h.**

## Risks / open subtleties

- **dictConfig idempotency**: `configure_logging` сейчас вызывается из `create_app`, который тесты могут дёргать многократно. Без guard на handler-cleanup можем накопить дубли handlers → каждый log line печатается N раз. Решение: явный `logging.getLogger().handlers.clear()` перед добавлением, либо module-level flag.
- **caplog vs propagation**: если переопределим root logger через dictConfig, caplog может не видеть records. Решение: либо оставить root propagation включённой, либо в тестах использовать `structlog.testing.capture_logs()` (предпочтительнее — structlog-native).
- **contextvars в async/await**: `contextvars.copy_context()` копируется на каждый `asyncio.create_task` — означает background-tasks (`uptime_collector_loop`) **не унаследуют** request_id если их запускают вне request-цикла. Это expected behavior (uptime_collector живёт в lifespan, не в request) — но docстрингом упомянуть.
- **Middleware order**: FastAPI LIFO — последний `add_middleware` обрабатывается первым. Хотим RequestID **outer** → добавлять его **после** CORSMiddleware. Cross-check: integration test покажет правильный порядок (если CORS дропает X-Request-ID header — увидим красное).
- **Test pollution через contextvars**: между тестами state может протечь. Решение: `autouse fixture clear_contextvars` в conftest.py для test-suite (либо inline в каждом тесте).
