# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус проекта и рабочие соглашения.

---

## Current Status

**Phase:** 4 закрыта (Bank Mode UI). Spec: `docs/superpowers/specs/2026-05-11-phase-4-bank-mode-design.md`, ADR-0009. Phase 4 покрыла 4.A (DB фундамент) → 4.B (JWT auth, AuthnPort, CLI seed) → 4.C (search + history endpoints) → 4.D (`APP_MODE` gating + audit-wiring) → 4.E (frontend foundation, BFF httpOnly cookies) → 4.F (`/search` гибрид + `/history` таблица) → 4.G (DossierView extract в features/, shared `/dossier/[id]`) → 4.H (docker smoke + docs).

**Активная ветка:** `main` (HEAD `156fa5d`). Phase 4 шла линейно прямо в main: 4.A `74a650f` → 4.B `f760b41` → 4.C `487c29b` → 4.D `86b9703` → 4.E `f582edd` → 4.F `64008b1` → 4.G `bc854e9` → 4.H `84c0db6` + 2 fix(ci). Готовы стартовать Phase 5 (E2E на 5 фирмах папы / 2.6, либо переход к pilot-демо).

**Verify status:** ruff + mypy --strict (src+tests) + 459 unit + 68 integration (5 PDF-тестов skip на Windows-host) + tsc + eslint + next build (14 routes) — зелёные. Docker smoke `APP_MODE=bank`: login → /me → search → list → audit-log запись подтверждены. CI зелёный после `156fa5d`.

## Smoke-инструкция Phase 4 (Bank Mode end-to-end)

См. ниже шаги в README/чеклисте sessions; полный flow воспроизводится на host'е за ~3 минуты.

---

## Открытые TODO

- TODO[CA-003]: реальный лукап ГНК для ИНН (сейчас pill «Проверено в ГНК» по 9-значной валидации формата).
- TODO[CA-006]: убрать дублирующий `ix_borrowers_inn` — `UniqueConstraint("inn")` уже создаёт `borrowers_inn_key`. Косметика, миграция перед production.
- TODO[CA-010]: bundle TTF Inter (400/500/600/700) + JetBrains Mono (500/600) в `src/infrastructure/reports/pdf/fonts/` + `@font-face`. Сейчас PDF на DejaVu Sans (читается, но ≠ Inter на экране). Косметика.
- TODO[CA-015]: уточнить парсер `vat_declaration_parser.py` под живые xltx 10006_45/10006_47 — детектор уже опознаёт через widened sentinel + structural fallback (CA-012), но cells F6/G6/F7-F11/G7 могут быть смещены. Ждём реальные файлы.
- TODO[CA-018]: extract `(accountant)/manual-input` в `features/manual-input` + thin re-export. Сейчас на bank install `/manual-input` (куда search ведёт для upload) рендерится с accountant sidebar. Аналогично 4.G для DossierView, но scope не вошёл в Phase 4.
- TODO[CA-019]: refresh-token rotation + denylist (Redis) — в v1 refresh stateless 7д без инвалидации. ADR-0009 fixes path к v2.
- TODO[CA-020]: LDAP/OAuth AuthnAdapter для production-банка. AuthnPort готов (`application/ports/authn_port.py`), нужен новый adapter в `infrastructure/auth/`.
- TODO[CA-028]: dynamic unit detection для FORM_2 — сейчас hardcoded ×1000 («тыс. сум»), читать B24 list01 («Единица измерения, …»). Если Soliq поменяет ЕИ — суммы поедут в 1000×. Косметика, до production.
- TODO[CA-029b]: парсер PROFIT_TAX (taxes_paid, 15 листов) — adapter всё ещё raises UnsupportedFormatError. По образцу FORM_2/FORM_1 + реальные xltx папы. FORM_1 закрыт в CA-029a.
- TODO[CA-040] (P2): Frontend unit-test infra (vitest + @testing-library) для `web/`. Сейчас `web/package.json` без test-инфры, ни одного `.test.tsx`. Под этот тикет — тесты CA-033 (pre-score 3 ветки), CA-035 (FORM_1 checklist + autofill counter), и любые будущие frontend unit-тесты. Реализация: добавить `vitest`, `@vitest/ui`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom` в devDependencies, `vitest.config.ts`, `npm run test` script.
- TODO[CA-034] (P2): CAGR 2023→2025 = 0.0% когда 2023 пустой → должно быть N/A; в колонке «Итого за год» сумма (2024+2025) подтягивается без 2023 — если базовый год пустой, не показывать сумму под «Итого».
- TODO[CA-035b] (P2): GET `/api/dossier/{id}/readiness` — domain readiness готов (CA-035 ADR 0010), нужен application use case (load dossier → snapshot → assess) + interfaces wiring + frontend consumer в досье/PDF (показать «доверие к данным» + missing_capabilities). По образцу POST `/api/manual-input/readiness`.
- TODO[CA-042] (P2): latest-period priority для FORM_2 multi-file dispatch. Сейчас first wins per year (`_set_once` в `parse_manual_input_files.py`). Если в одном дропе FORM_2 Q4 2024 + Q4 2025 — конфликт на `revenue_2024` (Q4 2025 prior column vs Q4 2024 current column): первая выигрывает по порядку, не по authoritativeness. Q4 2024 current authoritative для 2024 года. CA-041 применил эту семантику только для FORM_1, FORM_2 оставлен под отдельный обдуманный фикс.
- TODO[CA-037] (P3): 3 из 4 KPI карточек в досье пустые (EBITDA, ROE, Долг/EBITDA). Решение зависит от CA-029 (FORM_1 даст assets + liabilities → ROE/D-EBITDA).
- TODO[CA-038] (P3): валидация юр.адреса — минимум 15 символов + наличие цифры. Сейчас «Ташкент» проходит.
- TODO[CA-039] (P3): Шаг 1 — если дата назначения директора < 90 дней назад, показать inline warning «Будет учтено как сигнал риска».

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
| 2026-05-11 | post-4 | **Real-data E2E smoke fixes (CA-021..024)** — round red-flag evidence до 2 знаков (хвост из 18+ цифр из Decimal-string), clamp YoY% на ±999, clamp DSCR/ratio (>999× / <0,01×) под живые цифры (152152× в DSCR-gauge), accountant `/dossier/[id]` back button через router.back() с fallback `/manual-input`. Визуальный smoke у пользователя пройден. | `8b0dc4e`, `12b601f`, `2b97b77`, `7f81f3d` |
| 2026-05-11 | post-4 | **PDF gauge geometry (CA-025)** — arc-секторы score-gauge в `dossier.html` имели endpoints на радиусе 80–83 при заявленном r=90 → WeasyPrint рисовал кривые мимо. Пересчитал на корректную окружность r=90 вокруг (100,110), синхронизировал orange/yellow с frontend. Визуальный smoke у пользователя ⏸ pending. | `b800709` |
| 2026-05-11 | post-4 | **FORM_2 parser (CA-026)** — `parse_form2(wb)` извлекает 16 финансовых полей (revenue/cost/gross/operating/interest/PBT/tax/net × current+prior) из 3-листовой xltx «Отчёт о финансовых результатах». ×1000 (тыс. сум → UZS), signed-pairs (income−expense), best-effort cell-skipping. Подключён в `SoliqXltxAdapter._dispatch`, real-fixture smoke зелёный (Q4 2025, AZ RUHDIL SAVDO). +11 unit-тестов. FORM_1/PROFIT_TAX → TODO[CA-029]. | `dac388f` |
| 2026-05-11 | post-4 | **Multi-file autofill (CA-027)** — `POST /api/manual-input/parse-files` принимает N xltx + auto-detects formats + возвращает merged autofill payload (revenue 2024/2025 из FORM_2, vat_period из declaration+ilova). Frontend dropzone на Шаге 2 умеет batch-upload. Smoke у пользователя зелёный: FORM_2 заполняет revenue+net_profit, расхождение НДС/ЭСФ + 3 risk signals + скоринг 79/100. | `5a5f395`, `659440d` |
| 2026-05-11 | post-4 | **FORM_1 parser (CA-029a)** — `parse_form1(wb)` извлекает 12 балансовых показателей × 2 column (period_end / period_start) из list02 Формы №1: fixed_assets, non_current_assets, inventory, receivables, cash, current_assets, total_assets, equity, LT/ST liabilities, total_liabilities + derived `total_debt` (570+580+730+740+750, правило «хотя бы одна не-None»). ×1000 (тыс. сум → UZS), best-effort cell-skipping, balance-equation sanity (A ≈ E+L с допуском 0.5%) → warning не raise. Подключён в `SoliqXltxAdapter._dispatch`, real-fixture smoke зелёный (Q4 2025, QADR DON NON SAVDO ИНН 201308534: total_assets 2 533 084 тыс. сум, total_debt 618 267 тыс. сум). +17 unit-тестов. PROFIT_TAX → TODO[CA-029b]. | `2bf833b` |
| 2026-05-11 | post-4 | **Pre-score gauge null state (CA-033)** — `_lib/finance.ts` 3 helper'а переведены на null-семантику: `computeDscr`/`computeDebtToRevenuePct` возвращают `number \| null`, `classifyDscrRisk(null)` даёт четвёртую neutral-ветку «Недостаточно данных». Различие null (нет данных) vs 0/negative (явный red flag) сохранено: убыток → DSCR красный, не серый. Callsite `step-3-loan.tsx` отличает «не введено» от «введён 0» через новый `hasAnyQuarterValue`. `DscrGauge` рисует серую окружность при null. `RiskChip` получил neutral palette. Текст подписи при null → «Загрузите Форму №2 для расчёта DSCR». Три зоны риска (low/medium/high) сохранены. Unit-тесты под CA-040 (vitest infra). Verify: tsc + eslint зелёные. | `96e53e4` |
| 2026-05-12 | post-4 | **FORM_1 wiring в parse-files + applyToForm (CA-041)** — `Form1BalanceSheetData` подключён в `parse_manual_input_files` use case: `_consider_form1` копит кандидатов с **latest-period priority** (свежий снимок вытесняет старый тихо; равный (year, quarter) → first wins + дубликат-warning; старее → пропуск + warning). `_apply_form1` разворачивает победителя snapshot-целиком в 4 поля: `assets_total` / `liabilities_total` (column E, period_end) + `assets_total_period_start` / `liabilities_total_period_start` (column D, period_start — зарезервировано под CA-037 ROE = net_profit / avg_equity). `source_trail` обогащается `form1.*` префиксом (согласовано с CA-035 mapper). `ParsedFinancialsResponse` расширен 2 nullable полями. Frontend: `ParsedFinancialsDto` + `applyToForm` маппит `data.assets_total` → `step2.totalAssets`, `data.liabilities_total` → `step2.totalLiabilities` (period_start TS-optional, в UI не используется). FORM_2 latest-period priority — отдельный TODO[CA-042]. +4 unit-теста + 2 integration-теста (662 passed). Verify: ruff + mypy --strict + pytest + tsc + eslint зелёные. Smoke у пользователя пройден на живом FORM_1 xltx папы: readiness STANDARD 65%, `balance_ratios` capability исчезла из missing после автозаполнения totalAssets/totalLiabilities. | `c32e60c` |
| 2026-05-12 | post-4 | **PDF/UI consistency batch: CA-036/043/044/045/046** — серия фиксов после визуального PDF-smoke на живом досье папы. CA-044 (data integrity, critical): `FinancialReport.taxes_paid: Money \| None` сквозь стек (entity → Pydantic `MoneyInput \| None = None` → mapper `_to_money_optional` → persistence-mapper round-trip). Frontend `moneyOptional()` хелпер: пустое поле формы → `undefined` в payload → `null` в БД, не фабрикуем `Money(0)` в банковский документ. Quarterly_reports очищены от dummy `Money(0)`. KPI calculator + domain/rules grep подтвердили: `taxes_paid` нигде в scoring не читается, **CA-045 контрактно закрыт автоматически** (различимость None vs 0 теперь гарантирована типами). CA-043 (PDF arithmetic, critical): убрал `* 100` в `template_filters.fmt_pct` — контракт всего стека уже percent (kpi_calculator: `(a-b)/b*100`, frontend `formatYoy`, rule evidence). Прежний double-scale показывал `−1442,9%` вместо `−14,4%`. Добавлен regression-guard тест. CA-036 (UI consistency): `Revenue24mChart` empty state двухветочный через `hasAnnualRevenue` prop. CA-046 (PDF consistency): `render_revenue_24m(has_annual_revenue=…)` — синхронизация копирайта с CA-036 в PNG-placeholder через matplotlib. 16 файлов (10 backend + 4 frontend + 2 mixed test). +3 integration/unit-теста (round-trip None, endpoint без taxes_paid, regression-guard fmt_pct, two-text empty state). Verify: 666 passed, 5 skipped (PDF Windows-host), mypy --strict + tsc + eslint зелёные. Smoke: docker rebuild api → POST `/api/manual-input` без taxes_paid[2024] → HTTP 200; визуальный PDF-smoke у пользователя — все 3 фикса видны. | `<pending>` |
| 2026-05-12 | post-4 | **CAGR/Margin null-state + ratio-row "Итого" fix (CA-034)** — `computeCagrPct`/`computeMarginPct` переведены на `number \| null` (null когда `start_value <= 0`/`revenue <= 0` — деление на ноль/Infinity ≠ «0% роста»). Footer financial-table унифицирован: общий `RatioPill` (3 tone success/danger/neutral, «N/A» серым при null), общий `RatioTotalCell` («—» в колонке «Итого за год» для CAGR+маржи — коэффициент ≠ годовая сумма). Margin coefficient переехала из col6 («Итого») в col1 рядом с label (как CAGR DeltaPill). Verify: tsc + eslint зелёные. Unit-тесты — TODO[CA-040]. | `56bc757` |
| 2026-05-12 | post-4 | **Data Readiness Assessment service (CA-035, ADR-0010)** — 4-уровневая шкала готовности данных (INSUFFICIENT/MINIMAL/STANDARD/COMPREHENSIVE) + independent `missing_capabilities` (yoy_trend/cagr/balance_ratios/tax_burden) + `confidence_score`. 5 слоёв: (1) `domain/services/data_readiness.py` pure assess_readiness + 51 unit-тест, (2) `application/use_cases/assess_draft_readiness.py` stateless оркестратор + source_trail→ParserSource mapper + 17 unit-тестов, (3) `interfaces/api/shared/data_readiness.py` POST `/api/manual-input/readiness` + 7 integration-тестов, (4) frontend — React Context `SourceTrailProvider` для UI-only source_trail из CA-027 dropzone + новый `Checklist` компонент с debounce 500ms POST на изменения form, (5) ADR 0010. Smoke пройден на 3 сценариях (INSUFFICIENT 0% → MINIMAL 25% → STANDARD 50% с корректным исчезновением yoy_trend); fix `7e7826a` после smoke: `buildRequest` в checklist.tsx использует `yearTotal` proxy (один Q4 cell с annual revenue → annual_report_year, не partial) — согласовано с CA-027 yearTotal-семантикой. CA-035b (GET /dossier/.../readiness) и CA-041 (FORM_1 wiring в parse-files) — отдельными тикетами. Frontend unit-тесты — TODO[CA-040]. | `a070f3f` (domain) · `177bfa7` (form1 warning hotfix) · `2a97a90` (application) · `ff8f585` (interfaces) · `642fa60` (frontend) · `ef12e15` (docs/ADR-0010) · `7e7826a` (smoke fix) |

> Подробные транзакционные журналы предыдущих сессий (decompositions, real-data smoke numbers, по-step rationale) удалены при сжатии — см. `git log --oneline` для сырого таймлайна и `docs/adr/` для архитектурных решений.
