# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус проекта и рабочие соглашения.

---

## Current Status

**Phase:** 3 закрыта. Парсер soliq_xltx переведён на best-effort (CA-014 закрыт по контракту). **Готовы стартовать Phase 4 (Bank Mode UI)** или 2.6 (E2E на 5 фирмах папы).

**Активная ветка:** `main` (HEAD `d34572c`). Phase 4 стартует с новой ветки `feat/phase-4-...` от main.

**Verify status:** ruff + mypy --strict + 443 unit + 23 integration (5 PDF-тестов skip на Windows-host) + tsc + eslint + next build — зелёные.

---

## Открытые TODO

- TODO[CA-003]: реальный лукап ГНК для ИНН (сейчас pill «Проверено в ГНК» по 9-значной валидации формата).
- TODO[CA-006]: убрать дублирующий `ix_borrowers_inn` — `UniqueConstraint("inn")` уже создаёт `borrowers_inn_key`. Косметика, миграция перед production.
- TODO[CA-010]: bundle TTF Inter (400/500/600/700) + JetBrains Mono (500/600) в `src/infrastructure/reports/pdf/fonts/` + `@font-face`. Сейчас PDF на DejaVu Sans (читается, но ≠ Inter на экране). Косметика.
- TODO[CA-015]: уточнить парсер `vat_declaration_parser.py` под живые xltx 10006_45/10006_47 — детектор уже опознаёт через widened sentinel + structural fallback (CA-012), но cells F6/G6/F7-F11/G7 могут быть смещены. Ждём реальные файлы.

---

## Активные договорённости

- **VAT-периоды:** `BorrowerSnapshot.vat_periods: list[VatPeriodReport]` (ADR 0006, partial supersede ADR 0004). Декларация даёт `vat_declared` (`vat_charged_total` парсера), ilova — `esf_seller_vat_total` (sum НДС по продажам). Сравнение в рамках одного налогового периода.
- **ИНН заёмщика:** приходит явно от пользователя (UI/API), не угадывается из имени файла.
- **Реальные данные папы:** локально в `~/Downloads` / `tests/fixtures/**/*_full.*`, не в git. В repo — только `*_sample.csv` + synthetic factory-helpers для xltx (`tests/fixtures/soliq_xltx/_factories.py`).
- **xltx форматы (5 типов):** VAT_DECLARATION (8 листов), VAT_REGISTRY_ILOVA (10 листов, Приложение №4), FORM_2_INCOME_STATEMENT (3 листа), FORM_1_BALANCE_SHEET (4 листа), PROFIT_TAX (15 листов). Distinguished по сигнатурным cells list01.
- **Парсер soliq_xltx best-effort:** raises только на формат (UnsupportedFormatError, XltxBorrowerMismatchError); cell-level → warn + None. Каждый DTO имеет `parse_warnings: list[str]`; registry дополнительно `skipped_rows_count`. `to_soliq_chunk` возвращает `tuple[SoliqChunk, list[str]]`.
- **Persistence:** testcontainers + real Postgres для integration-тестов; draft TTL = 30d (`DRAFT_TTL_DAYS`); draft auth по `draft_id` без owner (переделать в Phase 4 Bank Mode).
- **Compose-postgres** на host **5433** (5432 занят локальным нативным Postgres).
- **Windows + asyncpg:** обязателен `WindowsSelectorEventLoopPolicy` (настроено в `migrations/env.py` + `interfaces/api/main.py`).
- **Backend в Docker:** WeasyPrint требует Pango/HarfBuzz/Fontconfig (см. ADR 0008). Compose-сервис `api` на 8000. Любые правки кода → `docker compose up -d --build api`, не `restart` (см. memory `project_docker_crlf_gotcha.md`).

---

## Working Agreements

- Перед каждой задачей: перечитай PROJECT_BRIEF.md Section 4 (Architecture) и Section 11 (Anti-patterns).
- Plan mode обязателен если затрагивается >2 файлов.
- Не начинай кодить без плана — сначала покажи декомпозицию.
- Язык UI: русский. Язык кода: английский.
- Коммиты: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Никаких `TODO` без ID (`# TODO[CA-001]: описание`).

---

## Architecture Reminders

- `domain/` не знает про `infrastructure/` — никогда.
- Все бизнес-правила — только в `domain/rules/`, ссылка на источник обязательна.
- Новый банк = новый adapter, не правки в ядре.
- Two modes (Bank / Accountant) — два UI поверх одного бизнес-ядра.

---

## Security Hard Rules

- Данные заёмщиков не логируются.
- Никаких внешних API в production (только on-premise).
- Soliq данные — только через официальный экспорт/API, не scraping.
- `.env` не в git, secrets через Vault в production.

---

## Start of Session Command

```
Прочитай @PROJECT_BRIEF.md целиком, потом @CLAUDE.md.
Скажи на каком phase мы сейчас и какая следующая atomic задача.
Не начинай кодить — сначала покажи план.
```

---

## Session Log (краткая история)

| Date | Phase | Summary | Refs |
|---|---|---|---|
| 2026-05-08 | 0 | Foundation — Python 3.12 + uv + FastAPI 0.136 + Next 16.2 + shadcn/ui + Postgres 16 + Redis 7 + GH Actions CI. | `ba401fb`, ADR 0002 |
| 2026-05-08 | 1 | Domain Core — 4 VO + 8 entities + 17 правил pure fn + ScoringService + YAML rules + 5 синтетических borrowers + 217 тестов. | ADR 0003 |
| 2026-05-08 | 2 | Phase 2 — domain под реальный CSV (ADR 0004 → 0006), DataSourcePort + use case, EsfCsvAdapter (CSV папы 25k invoices), ManualInput API + UI 3 шага, persistence (Alembic + 4 ORM/repos/mappers + drafts), SoliqXltxAdapter (5 xltx-форм через format_detector + VAT_DECLARATION + VAT_REGISTRY_ILOVA + endpoint upload + UI). 2.6 E2E на 5 фирмах ⏸ pending. | PR #1, PR #2, ADR 0004/0005/0006 |
| 2026-05-09 | 3.A | Result Screen UI — `/(accountant)/dossier/[id]` banking dashboard на Recharts + shadcn/ui (gauge, KPI, 24m chart, risk signals). Mock data (заменён в 3.B). CA-004 закрыт. | PR #3 |
| 2026-05-10 | 3.B | GET /api/dossier/{id} — read-модель `DossierViewRecord` (single SELECT + 2 JOIN), KPI calculator (revenue_ltm + monthly_revenue_24m), Pydantic-схемы (Decimal как str, display_score = 100−score), frontend useQuery + skeleton + error UI. | PR #4, ADR 0007 |
| 2026-05-10 | 3.C | PDF endpoint — `GET /api/dossier/{id}/pdf` (WeasyPrint + Jinja2 + matplotlib). Backend в Docker (compose `api`, python:3.12-slim + libpango/harfbuzz/fontconfig). 4 страницы A–G. Frontend «Скачать PDF» enabled. | PR #5, ADR 0008 |
| 2026-05-10 | post-3 | Parser hardening (CA-011..014 v1) — squash в main: ₽→сум на досье, widened детект 10006_*, динамические 15 лет селектор, tolerant ilova `_read_rows`. | `75ab42b` |
| 2026-05-10 | post-3 | Docker CRLF fix — `.gitattributes` для `*.sh` / Dockerfile / `docker/**` после bash`\r` сбоя при rebuild на Windows. См. memory `project_docker_crlf_gotcha.md`. | `319f0fd` |
| 2026-05-10 | post-3 | **Parser best-effort refactor (CA-014 closed)** — soliq_xltx перешёл на «парсер не raises на данных, только на формате». Все 3 DTO имеют `parse_warnings`; `to_soliq_chunk → tuple[SoliqChunk, list[str]]`; endpoint всегда 200 + warnings; UI collapsable жёлтый блок «Предупреждения парсера (N)». 14 файлов / +612/−279, +15 unit-тестов. | `64444d0` |

> Подробные транзакционные журналы предыдущих сессий (decompositions, real-data smoke numbers, по-step rationale) удалены при сжатии — см. `git log --oneline` для сырого таймлайна и `docs/adr/` для архитектурных решений.
