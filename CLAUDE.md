# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус проекта и рабочие соглашения.

---

## Current Status

**Phase:** 2 — Data Adapters (in progress)
**Last completed task:** 2.4.1 ManualInput API — `interfaces/api/shared/dossier_{schema,mapper,dependencies}.py` + endpoint `POST /api/manual-input`. Pydantic v2 схема со `extra="forbid"` валидирует ИНН (9/14 цифр), Decimal-суммы, поля Borrower + опциональные financial reports / monthly turnover / quarterly reports / counterparties / invoices / tax events / shares. Mapper Pydantic ↔ domain. RuleRegistry грузится из YAML через `lru_cache`. Endpoint: payload → Borrower + ManualChunk → use case → 17 правил → ScoringService → JSON. Integration tests на TestClient покрывают 4 правила (LOAN_TO_REVENUE, DIRECTOR_CHANGED, OKVED_CHANGED, NEGATIVE_PROFIT_3Q) + invalid INN/extra field/missing borrower → 422. 264 теста passed (+10), ruff + mypy --strict зелёные.
**Next task:** 2.4.2 ManualInput UI — `web/app/(accountant)/manual-input/page.tsx` через react-hook-form + zod, multi-step (basic info → financials → loan request). Подключить TanStack Query мутацию к `/api/manual-input`, рендерить `DossierResponse`.

**Phase 2 декомпозиция (согласована):** 2.0 ✓ → 2.1 ✓ → 2.2 EsfCsvAdapter (cp1251, реальный файл папы) → 2.4 ManualInputAdapter (API+UI) → 2.5 persistence (Alembic+Postgres+repos) → 2.3 SoliqExcelAdapter (после первой реальной выгрузки) → 2.6 E2E на 5 фирмах. VAT-адаптер для активации `VAT_ESF_MISMATCH` появится в 2.x после получения сводной справки НДС.

---

## Working Agreements

- Перед каждой задачей: перечитай PROJECT_BRIEF.md Section 4 (Architecture) и Section 11 (Anti-patterns)
- Plan mode обязателен если затрагивается >2 файлов
- Не начинай кодить без плана — сначала покажи декомпозицию
- Язык UI: русский. Язык кода: английский
- Коммиты: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)
- Никаких `TODO` без ID (`# TODO[CA-001]: описание`)

---

## Architecture Reminders

- `domain/` не знает про `infrastructure/` — никогда
- Все бизнес-правила — только в `domain/rules/`, ссылка на источник обязательна
- Новый банк = новый adapter, не правки в ядре
- Two modes (Bank / Accountant) — два UI поверх одного бизнес-ядра

---

## Security Hard Rules

- Данные заёмщиков не логируются
- Никаких внешних API в production (только on-premise)
- Soliq данные — только через официальный экспорт/API, не scraping
- `.env` не в git, secrets через Vault в production

---

## Start of Session Command

```
Прочитай @PROJECT_BRIEF.md целиком, потом @CLAUDE.md.
Скажи на каком phase мы сейчас и какая следующая atomic задача.
Не начинай кодить — сначала покажи план.
```

---

## Session Log

| Session | Phase | Completed | Notes |
|---------|-------|-----------|-------|
| 2026-05-08 | 0 | Foundation 0.1–0.9 | Stack: Python 3.12 + uv, FastAPI 0.136, Next 16.2 (вместо 15 — см. ADR 0002), shadcn/ui, TanStack Query, Postgres 16 + Redis 7 в compose, CI с ruff/mypy/pytest и eslint/tsc/build. |
| 2026-05-08 | 0 | Phase 0 follow-up | Compose поднят и здоров (`credit-postgres` + `credit-redis` healthy, `pg_isready` accepting, redis `PONG`). GitHub remote `origin` → `github.com/RiobVO/credit-assistant`, main pushed (HEAD `ba401fb`). uv добавлен в User PATH через installer — в новых сессиях работает без хака. |
| 2026-05-08 | 1 | Domain Core 1.0–1.9 | Branch `feat/phase-1-domain`. 4 value objects (INN/Money/DateRange/FlagSeverity), 8 entities, 17 правил pure fn, ScoringService (LOW=1/MED=3/HIGH=7/CRIT=15; <15 APPROVE, 15-29 REVIEW, ≥30 REJECT), YAML+loader, 5 синтетических borrowers, 217 тестов, coverage `src/domain/rules` ≈99%, ADR 0003. TODO: CA-001 (INN checksum ГНК), CA-002 (full graph CIRCULAR_INVOICING). |
| 2026-05-08 | 2 | 2.0 Domain под реальный CSV | Убран `Invoice.vat_amount`; добавлен `BorrowerSnapshot.esf_seller_vat_total: Money \| None`; `VAT_ESF_MISMATCH` переписан под агрегат, degraded mode без VAT-адаптера. ADR 0004. 218 тестов passed, ruff + mypy --strict зелёные. Изменения: `src/domain/entities/{invoice,borrower_snapshot}.py`, `src/domain/rules/financial/vat_esf_mismatch.py`, тесты + `tests/fixtures/synthetic_borrowers.py`. |
| 2026-05-08 | 2 | 2.1 Port + use case | `application/dto/parsed_data_chunk.py` (3 chunk-DTO + union), `application/ports/data_source_port.py` (`DataSourcePort` Protocol), `application/use_cases/build_borrower_snapshot.py` (+ `ChunkBorrowerMismatchError`). 13 use case-тестов; всего 231 passed; ruff + mypy --strict зелёные. |
| 2026-05-08 | 2 | 2.2 EsfCsvAdapter | `infrastructure/adapters/esf_csv/{parser,errors}.py` для e-factura.uz CSV (cp1251, `;`). Регекс на дату устойчив к 3 форматам номера; десятичные суммы с запятой; ПИНФЛ-покупатели; пустой ИНН → skip. Sample-фикстура (40 строк) в repo, полный 25k файл в `.gitignore`. Sanity check: парсер усваивает 25 292 invoices папы за 2020-01–2026-05. 22 теста; всего 254 passed; ruff + mypy --strict зелёные. Удалён placeholder `esf_json/`. |
| 2026-05-08 | 2 | 2.4.1 ManualInput API | `interfaces/api/shared/dossier_{schema,mapper,dependencies}.py` + endpoint `POST /api/manual-input` (Pydantic v2, FastAPI Annotated Depends, RuleRegistry через `lru_cache`). End-to-end: payload → Borrower+ManualChunk → use case → 17 правил → ScoringService → JSON. 10 integration-тестов покрывают 4 правила + 422-валидацию. 264 passed; ruff + mypy --strict зелёные. |
