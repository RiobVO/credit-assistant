# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус проекта и рабочие соглашения.

---

## Current Status

**Phase:** 2 — Data Adapters (in progress)
**Last completed task:** 2.4.2 ManualInput UI — три шага в `web/src/app/(accountant)/manual-input/`. Шаг 1: 8 полей борровера (ИНН с GNK-pill, наименование, ОПФ, дата регистрации, ОКВЭД, директор + дата назначения, юр. адрес — добавлен сверх дизайна, обязателен на API). Шаг 2: две таблицы 3×4 квартала (выручка / чистая прибыль) + 4 годовых поля (НДС/налоги/активы/обязательства) + computed D/A и собственный капитал. Шаг 3: сумма / срок / ставка / цель + категории-pills + DSCR-pre-score panel (gauge + monthly payment + secondary metrics + checklist). Submit к `/api/manual-input` через TanStack Query mutation, результат рендерится в `DossierResult` (score, recommendation, severity breakdown, список red flags). Дизайн-токены (navy/primary/success palette) добавлены в `globals.css` рядом с shadcn neutral; шрифты переключены на Inter + JetBrains Mono. shadcn-примитивы: `input`, `label`, `select`, `textarea` (form-helper не используем — рh-form FormProvider напрямую). Зависимости: `react-hook-form`, `zod`, `@hookform/resolvers`, `date-fns`. tsc + lint + `next build` зелёные; smoke-test: dev server отдаёт `/manual-input` с маркерами CreditScope / Шаг 1 / Сведения о заёмщике, end-to-end POST к работающему backend возвращает корректный `DossierResponse`.
**Next task:** 2.5 persistence (Alembic + Postgres + repos) — миграции, Borrower/Snapshot/Dossier репозитории, persistance чернового сохранения формы.

**Phase 2 декомпозиция (согласована):** 2.0 ✓ → 2.1 ✓ → 2.2 ✓ → 2.4.1 ✓ (API) → 2.4.2 ✓ (UI) → **2.5 persistence** ← здесь → 2.3 SoliqExcelAdapter (после первой реальной выгрузки) → 2.6 E2E на 5 фирмах. VAT-адаптер для активации `VAT_ESF_MISMATCH` появится в 2.x после получения сводной справки НДС.

**Открытые TODO из 2.4.2:**
- TODO[CA-003]: реальный лукап ГНК для ИНН (сейчас pill «Проверено в ГНК» по 9-значной валидации формата)
- TODO[CA-004]: per-year taxes UI на Шаге 2 (сейчас taxes_paid="0" для 2023/2024 — degraded)
- TODO[CA-005]: расширить `ManualInputRequest` схему backend полями `loan_term_months`, `loan_rate_pct`, `loan_purpose`, `loan_category` (сейчас собираются на UI, но в payload не идут)

**Активная ветка:** `feat/phase-2-data-adapters` (HEAD `0e62486`, запушена в origin). Не смержена в main. После Phase 2 — PR на main.

**Договорённости по Phase 2 (зафиксированы):**
- VAT хранится отдельно от ЭСФ — агрегат на `BorrowerSnapshot.esf_seller_vat_total` (ADR 0004).
- ИНН заёмщика приходит явно от пользователя (через UI/API), не угадывается из имени файла.
- Реальные данные папы (полный CSV 25k строк) — локально, не в git. В repo только `*_sample.csv`-фикстуры (см. `.gitignore`).

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
| 2026-05-08 | 2 | **Session close** (2.0 → 2.4.1) | За одну сессию закрыто 4 атомарных шага Phase 2 на ветке `feat/phase-2-data-adapters` (`b4c0d3f` → `0ee4cf3` → `4127a3d` → `7408aae`). End-to-end pipeline работает: payload → snapshot → 17 правил → score → JSON. Реальный CSV папы (25 292 invoices, 2020–2026, 111 контрагентов) парсится без ошибок. Открытое: 2.4.2 UI — следующая сессия. |
| 2026-05-08 | 2 | 2.4.2 ManualInput UI (3 шага) | По дизайну Claude Design (`Credit Assessment - Step 1/2/3.html`): дарк-сайдбар CreditScope, topbar с крошками, page-head + дело-чип, 3-шаговый stepper, info-banner per step, форма с rh-form + zod. Step 1 — 8 полей борровера; Step 2 — 2 квартальные таблицы 3×4 + 4 годовых поля + computed D/A & equity; Step 3 — loan amount/term/rate/purpose + DSCR pre-score panel + checklist. Submit через TanStack Query → `DossierResult` (score, recommendation, severity breakdown, red flags). Дизайн-токены в globals.css, шрифты Inter + JetBrains Mono. tsc + lint + `next build` + smoke (curl /manual-input + curl /api/manual-input) зелёные. Открытые TODO[CA-003..005]. |
| 2026-05-08 | 2 | **Session close** (2.4.2) | Frontend-сессия. 24 новых файла + 5 модифицированных, коммит `0e62486` запушен в origin. End-to-end проверен: dev server отдаёт `/manual-input`, реальный POST к `/api/manual-input` возвращает корректный `DossierResponse` с red_flags. Открытое: 2.5 persistence — следующая сессия. |
