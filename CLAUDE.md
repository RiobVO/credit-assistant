# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус проекта и рабочие соглашения.

---

## Current Status

**Phase:** 4 закрыта (Bank Mode UI). Spec: `docs/superpowers/specs/2026-05-11-phase-4-bank-mode-design.md`, ADR-0009. Phase 4 покрыла 4.A (DB фундамент) → 4.B (JWT auth, AuthnPort, CLI seed) → 4.C (search + history endpoints) → 4.D (`APP_MODE` gating + audit-wiring) → 4.E (frontend foundation, BFF httpOnly cookies) → 4.F (`/search` гибрид + `/history` таблица) → 4.G (DossierView extract в features/, shared `/dossier/[id]`) → 4.H (docker smoke + docs).

**Активная ветка:** `main` (после Phase 4 squash).

**Verify status:** ruff + mypy --strict + 459 unit + 68 integration (5 PDF-тестов skip на Windows-host) + tsc + eslint + next build (14 routes) — зелёные. Docker smoke `APP_MODE=bank`: login → /me → search → list → audit-log запись подтверждены.

---

## Открытые TODO

- TODO[CA-003]: реальный лукап ГНК для ИНН (сейчас pill «Проверено в ГНК» по 9-значной валидации формата).
- TODO[CA-006]: убрать дублирующий `ix_borrowers_inn` — `UniqueConstraint("inn")` уже создаёт `borrowers_inn_key`. Косметика, миграция перед production.
- TODO[CA-010]: bundle TTF Inter (400/500/600/700) + JetBrains Mono (500/600) в `src/infrastructure/reports/pdf/fonts/` + `@font-face`. Сейчас PDF на DejaVu Sans (читается, но ≠ Inter на экране). Косметика.
- TODO[CA-015]: уточнить парсер `vat_declaration_parser.py` под живые xltx 10006_45/10006_47 — детектор уже опознаёт через widened sentinel + structural fallback (CA-012), но cells F6/G6/F7-F11/G7 могут быть смещены. Ждём реальные файлы.
- TODO[CA-018]: extract `(accountant)/manual-input` в `features/manual-input` + thin re-export. Сейчас на bank install `/manual-input` (куда search ведёт для upload) рендерится с accountant sidebar. Аналогично 4.G для DossierView, но scope не вошёл в Phase 4.
- TODO[CA-019]: refresh-token rotation + denylist (Redis) — в v1 refresh stateless 7д без инвалидации. ADR-0009 fixes path к v2.
- TODO[CA-020]: LDAP/OAuth AuthnAdapter для production-банка. AuthnPort готов (`application/ports/authn_port.py`), нужен новый adapter в `infrastructure/auth/`.

---

## Активные договорённости

- **VAT-периоды:** `BorrowerSnapshot.vat_periods: list[VatPeriodReport]` (ADR 0006, partial supersede ADR 0004). Декларация даёт `vat_declared` (`vat_charged_total` парсера), ilova — `esf_seller_vat_total` (sum НДС по продажам). Сравнение в рамках одного налогового периода.
- **ИНН заёмщика:** приходит явно от пользователя (UI/API), не угадывается из имени файла.
- **Реальные данные папы:** локально в `~/Downloads` / `tests/fixtures/**/*_full.*`, не в git. В repo — только `*_sample.csv` + synthetic factory-helpers для xltx (`tests/fixtures/soliq_xltx/_factories.py`).
- **xltx форматы (5 типов):** VAT_DECLARATION (8 листов), VAT_REGISTRY_ILOVA (10 листов, Приложение №4), FORM_2_INCOME_STATEMENT (3 листа), FORM_1_BALANCE_SHEET (4 листа), PROFIT_TAX (15 листов). Distinguished по сигнатурным cells list01.
- **Парсер soliq_xltx best-effort:** raises только на формат (UnsupportedFormatError, XltxBorrowerMismatchError); cell-level → warn + None. Каждый DTO имеет `parse_warnings: list[str]`; registry дополнительно `skipped_rows_count`. `to_soliq_chunk` возвращает `tuple[SoliqChunk, list[str]]`.
- **Persistence:** testcontainers + real Postgres для integration-тестов; draft TTL = 30d (`DRAFT_TTL_DAYS`); draft auth по `draft_id` без owner (валидно для accountant; bank-mode авторизация перешла на JWT в Phase 4).
- **Compose-postgres** на host **5433** (5432 занят локальным нативным Postgres).
- **Windows + asyncpg:** обязателен `WindowsSelectorEventLoopPolicy` (настроено в `migrations/env.py` + `interfaces/api/main.py`).
- **Backend в Docker:** WeasyPrint требует Pango/HarfBuzz/Fontconfig (см. ADR 0008). Compose-сервис `api` на 8000. Любые правки кода → `docker compose up -d --build api`, не `restart` (см. memory `project_docker_crlf_gotcha.md`).
- **Phase 4 — Bank Mode (ADR-0009):** `APP_MODE` env управляет инсталляцией (bank/accountant); один режим на установку. Bank: shared endpoints (`/api/manual-input`, `/api/dossier/*`, `/api/soliq-upload`, drafts) закрыты `Depends(get_current_analyst)` на router-уровне. Audit `login/login_failed/logout/search_borrower/view_dossier/generate_dossier/download_pdf` с masked-ИНН пишется из use cases в `audit_log`. `dossiers.source_mode` (`bank` | `accountant`) + nullable FK `created_by_analyst_id` — bank-history фильтрует по `source_mode='bank'`.
- **JWT (Phase 4.B):** native `bcrypt` (passlib 1.7.x несовместим с bcrypt 5.x), HS256, access 15м + refresh 7д, без ротации в v1 (TODO[CA-019]). `AuthnPort` готов под LDAP/OAuth (TODO[CA-020]). `JWT_SECRET` через env (.env / compose / Vault), мин. 32 байта в проде.
- **Frontend BFF cookies:** httpOnly + sameSite=lax + secure-в-проде. Backend возвращает JSON, Next route handlers (`app/api/auth/*`, `app/api/bank/*`, `app/api/dossier/[id]/pdf`) пакуют tokens в `ca_access` (path=`/`) и `ca_refresh` (path=`/api/auth`). Client JS никогда не видит JWT.
- **Seed analyst:** `docker compose exec api bash -c "cd /app/src && uv run --no-sync python -m interfaces.cli.seed_analysts --email ... --password ... --full-name ..."`. Upsert по email.

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
| 2026-05-11 | 4 | **Bank Mode UI — Phase 4 закрыта.** 4.A DB фундамент (analysts/audit_log/dossier columns) → 4.B JWT auth (bcrypt+jose, AuthnPort, /api/bank/auth/{login,refresh,logout,me}, seed CLI) → 4.C bank endpoints (/borrowers/search, /dossiers с filter mine/all+q+pagination, masked-ИНН audit) → 4.D `APP_MODE`-gating в `create_app` + optional-analyst injection в shared endpoints + 6 mode-gating integration-тестов → 4.E frontend foundation (BFF httpOnly cookies, `(bank)` route group, login screen, mode-aware root redirect, Next 16 `proxy.ts`) → 4.F `/search` гибридный flow + `/history` TanStack-Query table → 4.G extract `DossierView` в `features/dossier/`, `AppShell` mode-aware, `/dossier/[id]` переезд в root + PDF BFF proxy → 4.H docker smoke (APP_MODE=bank end-to-end), ADR-0009. | spec, ADR-0009, PRs squashed в main |

> Подробные транзакционные журналы предыдущих сессий (decompositions, real-data smoke numbers, по-step rationale) удалены при сжатии — см. `git log --oneline` для сырого таймлайна и `docs/adr/` для архитектурных решений.
