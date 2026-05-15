# T1.4 — Multi-tenant runtime isolation (Approach A pure)

> Scope сужен после PROJECT_BRIEF Sec 11 review: «один банк = одна установка».
> Approach A pure — separate compose-project per bank, brand_id присутствует
> только для startup-sanity + audit forensics, не для row-level SQL guard.
>
> Roadmap T1.4 в `docs/pre-demo-roadmap.md` обновляется в финальном коммите.

## Decisions

- **Approach A pure** — изоляция через separate Postgres (отдельный compose project / volume / port set), `brand_id` НЕ добавляется в `borrowers/dossiers/snapshots/drafts/analysts`. PROJECT_BRIEF Sec 11 compliant.
- **`brand_id` в `audit_log` only** — для forensics (если оператор miswired connection string, лог покажет mismatch row).
- **Settings.brand_id** — pydantic-settings env binding, single source of truth. Loader `load_brand` читает settings, не `os.getenv`.
- **Generalize startup-asserts** в helper `_validate_runtime_config(settings)` в `interfaces/api/app.py` — PII_ENC_KEYS + BRAND_ID живут рядом.
- **ADR-0018** «Single-tenant per deployment — defense-in-depth».

## Atomic split

### T1.4.1 — Settings.brand_id + startup assertion + ADR-0018

**Файлы (~7):**
1. `src/config/settings.py` — `brand_id: str = "default"`.
2. `src/infrastructure/brand/brand_config.py` — `load_brand(brand_id)` принимает обязательный аргумент (без env fallback); резолвится из settings там, где зовётся.
3. `src/interfaces/api/app.py` — extract `_validate_runtime_config(settings)` helper, объединить PII_ENC_KEYS + BRAND_ID checks; вызывать в `create_app` перед `FastAPI(...)`.
4. Call-sites `load_brand()` без аргумента — переключить на `load_brand(settings.brand_id)` (grep по `src` после рефакторинга).
5. `src/infrastructure/brand/brand_config_test.py` — обновить тесты под mandatory argument.
6. `src/interfaces/api/app_test.py` (новый или extend) — `create_app` raises на missing brand file + raises на missing PII_ENC_KEYS в prod.
7. `docs/adr/0018-multi-tenant-runtime-isolation.md`.

**TDD цикл:**
- Red: `test_create_app_raises_when_brand_config_missing` (BRAND_ID=ghost, нет `config/brands/ghost.json` → RuntimeError).
- Green: реализация helper'а в `app.py`.
- Red: `test_load_brand_requires_brand_id_argument` (вызов без аргумента → TypeError).
- Green: refactor `load_brand` сигнатуры + call-sites.
- Refactor: extract `_validate_runtime_config`.

**Verify:** `docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest src/infrastructure/brand src/interfaces/api"` → 0 fails.

**Commit:** `feat(infra): T1.4.1 startup brand-config assertion + Settings.brand_id`.

---

### T1.4.2 — audit_log.brand_id для forensics

**Файлы (~8):**
1. Alembic migration `20260518_2200_audit_log_brand_id.py`:
   - `ALTER TABLE audit_log ADD COLUMN brand_id VARCHAR(50) NOT NULL DEFAULT 'default'`.
   - Backfill (`UPDATE audit_log SET brand_id = 'default' WHERE brand_id IS NULL` — defensive).
   - Index `ix_audit_log_brand_id_created_at`.
   - Downgrade: DROP COLUMN + DROP INDEX.
2. `src/infrastructure/persistence/models/audit_log.py` — `brand_id: Mapped[str]` колонка с `server_default="default"`.
3. `src/infrastructure/persistence/repositories/audit_log_repository.py` — `record(*, brand_id, ...)`.
4. Call-sites `record_event(...)` — добавить `brand_id=settings.brand_id`:
   - `src/interfaces/api/bank/admin.py`
   - `src/interfaces/api/bank/mfa.py`
   - `src/interfaces/api/bank/auth.py`
   - `src/interfaces/api/bank/search.py`
   - `src/application/use_cases/authenticate_analyst.py`
5. `src/infrastructure/persistence/repositories/audit_log_repository_test.py` (новый или extend) — round-trip brand_id.
6. Тесты на 3-4 callsite — brand_id попадает в БД.

**TDD цикл:**
- Red: `test_audit_log_records_brand_id` (record(brand_id="uzbekbank") → raw SELECT == "uzbekbank").
- Green: migration + ORM column + repo argument.
- Red: integration на bank/auth — login event пишет `brand_id == settings.brand_id`.
- Green: wire settings.brand_id в call-sites.

**Verify:** полный pytest + ruff + mypy + миграция up/down idempotent.

**Commit:** `feat(audit): T1.4.2 brand_id column в audit_log для forensics`.

---

### T1.4.3 — ops doc + roadmap finalize + ADR-0018 final

**Файлы (~3):**
1. `docs/operations/multi-tenant-deploy.md` — recipe для одной машины с N банков:
   - Compose `--project-name <brand>` + separate volume + offset ports (`8000+N` / `5433+N` / `6379+N`).
   - `.env.<brand>` per inst (BRAND_ID, DATABASE_URL, REDIS_URL, PII_ENC_KEYS — отдельные секреты per bank).
   - Verification script: подключиться к каждому Postgres, убедиться что dossiers разные.
2. `docs/pre-demo-roadmap.md` — T1.4 status → DONE 2026-05-18; scope-clarification block (Approach A pure rationale).
3. `CLAUDE.md` Current Status + Persistence/infra block update.

**Verify:** `docker compose --project-name t14-test-a -p 8010:8000 ...` smoke (или skip, если local Windows compose неудобно — отложить как live-browser smoke с heads-up в commit message).

**Commit:** `docs(internal): T1.4 status sync + multi-tenant deploy playbook`.

---

## Out of scope (явно)
- `brand_id` колонки в `borrowers`/`dossiers`/`snapshots`/`drafts`/`analysts` — Approach A не требует. Если future shared-DB требование появится — добавляется отдельным таском.
- LDAP/OAuth (T1.5).
- Cross-tenant SQL guard middleware — Approach A полагается на DB-level isolation.
