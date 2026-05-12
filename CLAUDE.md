# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус проекта и рабочие соглашения.

---

## Current Status

**Phase:** 4 закрыта (Bank Mode UI). Spec: `docs/superpowers/specs/2026-05-11-phase-4-bank-mode-design.md`, ADR-0009.

**Активная ветка:** `main`. Post-4 серия — 20+ fix-тикетов по UI/PDF/data-integrity, frontend test infra, route extract, domain refactor (BalanceSnapshot), bank-mode UX. Реестр правил 19 (17 продакшн + INSUFFICIENT_DATA + NEGATIVE_EQUITY). Готовы стартовать Phase 5 (E2E на 5 фирмах папы / 2.6, либо переход к pilot-демо).

**Verify status:** ruff + mypy --strict (262 src files) + 745 passed (5 PDF-тестов skip на Windows-host — нужен GTK runtime в Docker) + tsc + eslint + next build (15 routes) + vitest (19 tests) — зелёные. Docker smoke: `APP_MODE=bank` end-to-end на real fixture папы (ИНН 201308534) после CA-047/050/051/052/053/054/055/056/057/058 — EBIT 256,9 млн, ROE 10,7% (amber stripe), Debt/EBIT 2,41× (amber stripe), readiness STANDARD 75%, score 94/100; «Пересобрать с дополнениями» переносит Шаг 1 borrower-карточкой в новый draft. CI зелёный.

---

## Открытые TODO

- TODO[CA-003]: реальный лукап ГНК для ИНН (сейчас pill «Проверено в ГНК» по 9-значной валидации формата).
- TODO[CA-015]: уточнить `vat_declaration_parser.py` под живые xltx 10006_45/10006_47 — детектор опознаёт через widened sentinel + structural fallback (CA-012), но cells F6/G6/F7-F11/G7 могут быть смещены. Ждём реальные файлы.
- TODO[CA-019]: refresh-token rotation + denylist (Redis) — в v1 refresh stateless 7д без инвалидации. ADR-0009 fixes path к v2.
- TODO[CA-020]: LDAP/OAuth AuthnAdapter для production-банка. AuthnPort готов (`application/ports/authn_port.py`), нужен новый adapter в `infrastructure/auth/`.
- TODO[CA-028]: dynamic unit detection для FORM_2 — сейчас hardcoded ×1000, читать B24 list01 («Единица измерения, …»).
- TODO[CA-029b]: парсер PROFIT_TAX (taxes_paid, 15 листов) — adapter raises UnsupportedFormatError. По образцу FORM_2/FORM_1 + реальные xltx папы.

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
- **JWT (Phase 4.B):** native `bcrypt` (passlib 1.7.x несовместим с bcrypt 5.x), HS256, access 15м + refresh 7д, без ротации в v1 (TODO[CA-019]). `AuthnPort` готов под LDAP/OAuth (TODO[CA-020]). `JWT_SECRET` через env, мин. 32 байта в проде.
- **Frontend BFF cookies:** httpOnly + sameSite=lax + secure-в-проде. Backend возвращает JSON, Next route handlers (`app/api/auth/*`, `app/api/bank/*`, `app/api/dossier/[id]/pdf`) пакуют tokens в `ca_access` (path=`/`) и `ca_refresh` (path=`/api/auth`). Client JS никогда не видит JWT.
- **Seed analyst:** `docker compose exec api bash -c "cd /app/src && uv run --no-sync python -m interfaces.cli.seed_analysts --email ... --password ... --full-name ..."`. Upsert по email.
- **CA-044 data integrity (Money | None):** `FinancialReport.taxes_paid` опциональный сквозь весь стек. `None` = «пользователь не заполнил» (PDF «—», БД null); `Money(0)` = «осознанно ноль уплат». Frontend mapper: `moneyOptional(digits)` → `undefined` при пустой строке, **не** `Money(0)`. Паттерн применять к любому новому опциональному money-полю.
- **CA-043 fmt_pct contract:** `template_filters.fmt_pct` принимает значение **уже в процентах** (consistent с `kpi_calculator: (a-b)/b*100`, frontend `formatYoy`, rule evidence). Не fraction. До CA-043 фильтр умножал на 100 повторно.
- **CA-037 KPI naming (`ebit` / `debt_to_ebit`):** EBIT = `profit_before_tax + interest_expense` — компонент EBITDA без D&A. До подключения D&A (FORM_5 / PROFIT_TAX, TODO[CA-029b]) — это **EBIT, не EBITDA**. UI рендерит «EBIT (прокси EBITDA)» + tooltip. Когда D&A появится — добавляем `ebitda` / `debt_to_ebitda` **рядом** (не переименовываем).
- **CA-037 snapshot JSONB round-trip:** новые nullable поля `FinancialReport` (profit_before_tax/interest_expense + balance_end/balance_start через BalanceSnapshot — CA-047) сериализуются в JSONB через `_financial_report_to_dict`/`_from_dict`. Legacy записи без CA-037 ключей читаются с `.get()` → None. **Если расширяешь FinancialReport новым полем — обязательно добавь в snapshot_mapper и unit-тест round-trip**, иначе данные тихо потеряются.
- **CA-047 BalanceSnapshot:** балансовые поля FORM_1 сгруппированы в `domain/value_objects/balance_snapshot.py` (`assets/liabilities/equity/total_debt`, все nullable). `FinancialReport` имеет `balance_end / balance_start: BalanceSnapshot | None` вместо 8 raw полей. **Wire contracts остались flat** для обратной совместимости: Pydantic `FinancialReportInput` и JSONB-payload в БД по-прежнему 8 ключей; группировка — только domain. 0-migration на legacy dossiers.
- **CA-042 FORM_2 tier priority:** для (field, year): `header.period_year == year` (CURRENT) > `year + 1` (PRIOR). CURRENT silently перезаписывает PRIOR; same-tier → first wins + warning. Реализация в `parse_manual_input_files._set_with_tier_priority` + `_Form2SourceTier(IntEnum)`.
- **CA-035b readiness в готовом досье:** GET `/api/dossier/{id}/readiness` — зеркало POST `/api/manual-input/readiness` на persisted snapshot. **`source_trail` в БД не хранится** (draft-only); `infer_parser_sources_from_snapshot` восстанавливает `set[ParserSource]` heuristic-ом по полям. Когда подключится PROFIT_TAX (CA-029b) — расширить.
- **CA-049 NEGATIVE_EQUITY rule:** critical-severity, на `latest_annual.balance_end.equity ≤ 0`. Дополняет, не дублирует ROE-карточку (ROE = None при equity_avg ≤ 0 — техническая неопределённость; NEGATIVE_EQUITY — явный сигнал в Разделе F). **Если добавляешь новое правило — обновляй YAML+`CODE_RULES` синхронно**: `load_registry()` raises на асимметрии.
- **CA-048 KPI threshold coloring:** пороги ROE (>15 GOOD / 5-15 WARN / <5 BAD) и Debt/EBIT (<2 GOOD / 2-4 WARN / >4 BAD) хранятся в `KpiValue.level_tone: KpiLevelTone | None`, **вычисляются в kpi_calculator.py — single source of truth**. Frontend и PDF только рендерят. Boundary inclusive на верхней границе warn. Особый кейс `debt_to_ebit = 0`: backend GOOD, UI спец-`NoDebtCard`. **Если добавляешь новый KPI с absolute threshold — расширь kpi_calculator, не дублируй пороги на frontend/PDF.**
- **CA-053 strict-mode useEffect:** `cancelled`-guards в `.finally()` опасны для terminal UI-flags (loading/error indicators). React 19 strict-mode run/cleanup/run может пропустить `setState(false)` если в обоих ветках guard блокирует. Для UI-flags `setIsLoading(false)` ставь безусловно — повторный state-update no-op.
- **CA-055 back-target в досье:** «список»-страницы (`/search`, `/history` в bank) при mount пишут `sessionStorage['ca:dossier-back-target']` через `rememberBackTarget`. ActionBar `consumeBackTarget()` + `router.push(target)`, fallback `/history`. **Manual-input не сохраняется как back-target** — даже если пользователь временно ушёл на досье из формы, back с досье уйдёт на `/search` / `/history`, не на форму с потенциально устаревшим draft'ом.
- **CA-058 prefill Шага 1:** при «Пересобрать с дополнениями» borrower-карточка из досье тянется через sessionStorage (`ca:manual-input-prefill-step1`). `rememberStep1Prefill(borrower)` в ActionBar.handleRebuild, `consumeStep1Prefill()` в manual-input-view.useEffect (только если нет draft — draft.payload приоритетнее, удаляется ключ при consume). Финансы (Шаг 2) и кредит (Шаг 3) остаются defaults — для них и пересобирают.

---

## Working Agreements

- Перед каждой задачей: перечитай PROJECT_BRIEF.md Section 4 (Architecture) и Section 11 (Anti-patterns).
- Plan mode обязателен если затрагивается >2 файлов.
- Не начинай кодить без плана — сначала покажи декомпозицию.
- Язык UI: русский. Язык кода: английский.
- Коммиты: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Никаких `TODO` без ID (`# TODO[CA-001]: описание`).
- После `git mv` + правок (sed/Edit) обязателен `git add -u` или явный re-add — иначе modify не попадает в коммит (rename стейджится с исходным content). См. memory `feedback_git_mv_sed_gotcha.md`.

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
| 2026-05-08 | 2 | Phase 2 — domain под реальный CSV (ADR 0004 → 0006), DataSourcePort + use case, EsfCsvAdapter (CSV папы 25k invoices), ManualInput API + UI 3 шага, persistence (Alembic + 4 ORM/repos/mappers + drafts), SoliqXltxAdapter (5 xltx-форм). | PR #1, PR #2, ADR 0004/0005/0006 |
| 2026-05-09 | 3.A | Result Screen UI — `/(accountant)/dossier/[id]` banking dashboard на Recharts + shadcn/ui. Mock data (заменён в 3.B). | PR #3 |
| 2026-05-10 | 3.B | GET /api/dossier/{id} — read-модель `DossierViewRecord`, KPI calculator (revenue_ltm + monthly_revenue_24m), Pydantic-схемы (Decimal как str), frontend useQuery + skeleton + error UI. | PR #4, ADR 0007 |
| 2026-05-10 | 3.C | PDF endpoint — `GET /api/dossier/{id}/pdf` (WeasyPrint + Jinja2 + matplotlib). Backend в Docker (python:3.12-slim + Pango). 4 страницы A–G. | PR #5, ADR 0008 |
| 2026-05-10 | post-3 | Parser hardening (CA-011..014 v1) — squash в main: ₽→сум на досье, widened детект 10006_*, динамические 15 лет селектор, tolerant ilova. Docker CRLF fix через `.gitattributes`. Best-effort refactor: парсер не raises на данных, только на формате; все DTO имеют `parse_warnings`. | `75ab42b`, `319f0fd`, `64444d0` |
| 2026-05-11 | 4 | **Bank Mode UI — Phase 4 закрыта.** 4.A DB фундамент → 4.B JWT auth (bcrypt+jose, AuthnPort) → 4.C bank endpoints (/borrowers/search, /dossiers) → 4.D `APP_MODE`-gating + audit-wiring → 4.E frontend foundation (BFF httpOnly cookies, login screen) → 4.F /search hybrid + /history TanStack-Query table → 4.G extract DossierView в `features/dossier/` + AppShell mode-aware → 4.H docker smoke. | spec, ADR-0009 |
| 2026-05-11 | post-4 | **Real-data E2E smoke fixes (CA-021..025)** — round red-flag evidence до 2 знаков, clamp YoY% ±999, clamp DSCR (>999×/<0,01×), accountant back через router.back fallback, PDF score-gauge arc geometry. | `8b0dc4e`, `12b601f`, `2b97b77`, `7f81f3d`, `b800709` |
| 2026-05-11 | post-4 | **FORM_2 parser (CA-026)** — `parse_form2(wb)` извлекает 16 финансовых полей × current+prior из 3-листовой xltx. ×1000, signed-pairs, best-effort. +11 тестов. | `dac388f` |
| 2026-05-11 | post-4 | **Multi-file autofill (CA-027)** — `POST /api/manual-input/parse-files` принимает N xltx + merged autofill payload. Frontend dropzone Шаг 2 batch-upload. | `5a5f395`, `659440d` |
| 2026-05-11 | post-4 | **FORM_1 parser (CA-029a)** — `parse_form1(wb)` извлекает 12 балансовых × period_end/start. ×1000, balance-equation sanity → warning. Real-fixture Q4 2025, ИНН 201308534. +17 тестов. PROFIT_TAX → TODO[CA-029b]. | `2bf833b` |
| 2026-05-11 | post-4 | **Pre-score gauge null state (CA-033)** — `_lib/finance.ts` хелперы → null-семантика; classifyDscrRisk(null) → neutral. Разделение «нет данных» vs «явный 0». | `96e53e4` |
| 2026-05-12 | post-4 | **Data Readiness Assessment (CA-035, ADR-0010)** — 4-уровневая шкала (INSUFFICIENT/MINIMAL/STANDARD/COMPREHENSIVE) + missing_capabilities + confidence_score. POST `/api/manual-input/readiness`, frontend `Checklist` debounce 500ms. | `a070f3f`, `2a97a90`, `ff8f585`, `642fa60`, `ef12e15`, `7e7826a` |
| 2026-05-12 | post-4 | **FORM_1 wiring + applyToForm (CA-041)** — FORM_1 latest-period priority в `parse_manual_input_files`, разворачивает в assets_total/liabilities_total + period_start снимки. Frontend `applyToForm` маппит на form. | `c32e60c` |
| 2026-05-12 | post-4 | **PDF/UI consistency batch (CA-036/043/044/045/046)** — серия после PDF-smoke досье папы. CA-044: `taxes_paid: Money\|None` сквозь стек. CA-043: убрал `*100` в fmt_pct (был double-scale «−1442,9%»). CA-036/046: empty-state Revenue24mChart двухтекстовый UI+PDF. | `7edf363` |
| 2026-05-12 | post-4 | **CAGR/Margin null-state + Итого fix (CA-034)** — хелперы → number\|null; общий `RatioPill`+`RatioTotalCell`; margin coeff из col6 в col1. | `56bc757` |
| 2026-05-12 | post-4 | **EBIT/ROE/Debt-to-EBIT KPI (CA-037)** — 3 пустые KPI заполнены сквозь parser→entity→snapshot→KPI→PDF/UI. `FinancialReport` +8 nullable полей (→ BalanceSnapshot позже, CA-047). API rename `ebitda→ebit`. Critical gap: snapshot_mapper JSONB не сериализовал поля → KPI null; smoke real fixture папы EBIT 256,9 млн, ROE 10,7%, Debt/EBIT 2,41×. Породил CA-047/048/049. | `174ab27`, `6132097` |
| 2026-05-12 | post-4 | **KPI threshold left stripe (CA-048)** — `level_tone: GOOD/WARN/BAD` в `KpiValue`, single source of truth в kpi_calculator.py (boundary inclusive on warn top). UI 4px border-l, PDF 3pt border-left. +27 boundary тестов. | `13cfda6` |
| 2026-05-12 | post-4 | **FORM_2 tier priority (CA-042)** — для (field, year): CURRENT > PRIOR через `_set_with_tier_priority` + `_Form2SourceTier` enum. CURRENT перетирает PRIOR silently. +5 тестов. | `29f5407` |
| 2026-05-12 | post-4 | **NEGATIVE_EQUITY rule (CA-049)** — реестр 18→19, critical-severity на `latest.equity ≤ 0` (boundary inclusive). +7 тестов; YAML+CODE_RULES sync. Источник: Базель III IRB. | `912453f` |
| 2026-05-12 | post-4 | **Readiness в готовом досье (CA-035b)** — GET `/api/dossier/{id}/readiness` зеркало для draft endpoint. `infer_parser_sources_from_snapshot` heuristic. Frontend `ReadinessBadge` non-blocking. | `8bb07c1` |
| 2026-05-12 | post-4 | **Frontend test infra (CA-040)** — `web/` получил vitest + RTL + jsdom. `globals: false` + explicit cleanup в afterEach. 19 smoke-тестов. CI шаг `Tests (vitest)`. | `d1882c5` |
| 2026-05-12 | post-4 | **Extract manual-input в features/ (CA-018)** — `(accountant)/manual-input/_*` → `features/manual-input/{components,hooks,lib}/`. Новый shared route `app/manual-input/{page,layout}.tsx` с AppShell mode-aware. Удалён dead code. Fix-коммит `5a1ff84` для забытых sed-правок после `git mv`. | `b3a5940` + `5a1ff84` |
| 2026-05-12 | post-4 | **BalanceSnapshot sub-entity (CA-047)** — 8 flat balance-полей FinancialReport сгруппированы в `BalanceSnapshot { assets, liabilities, equity, total_debt }` (`balance_end` + `balance_start`). Wire contracts остались flat — 0-migration на legacy dossiers. | `fedaa4e` |
| 2026-05-12 | post-4 | **Risk-signals accordion + counter (CA-050)** — ChevronRight был decoration → теперь `<button>` + useState per row → expandable panel с rule_id/severity/message/evidence. Счётчик 17→`data.rules_evaluated` (19). | `78fb6f7` |
| 2026-05-12 | post-4 | **Bank sidebar «+ Новая заявка» CTA (CA-051)** — primary blue CTA между header и nav в bank Sidebar. | `051b576` |
| 2026-05-12 | post-4 | **History-aware back (CA-052)** — unified `router.back()` в обоих режимах с mode-fallback. Заменило hardcoded `<Link href="/history">`. | `6f71f51` |
| 2026-05-12 | post-4 | **useFormDraft loader hang (CA-053)** — strict-mode useEffect run/cleanup/run: cancelled-guard в `.finally()` пропускал `setIsLoading(false)` → loader зависал. Fix: убрал guard на UI-flag. **Урок**: cancelled-guards опасны для terminal UI-flags. | `27fa34a` |
| 2026-05-12 | post-4 | **submit replace вместо push (CA-054)** — `submitMutation.onSuccess` → `router.replace`, `/manual-input?draft=X` не остаётся в history (draft удалён после submit). | `446da13` |
| 2026-05-12 | post-4 | **Smart back через sessionStorage (CA-055)** — `/search`/`/history` пишут `ca:dossier-back-target`; ActionBar читает + fallback `/history`. Manual-input не сохраняется как back-target. Per-tab. | `eab91bc` |
| 2026-05-12 | post-4 | **«Пересобрать с дополнениями» + ?inn= (CA-056)** — третья кнопка в ActionBar → `/manual-input?inn=<INN>`. Pre-fill ИНН в Шаге 1. | `8d10c71` |
| 2026-05-12 | post-4 | **Убрана dead «Сохранить как черновик» (CA-057)** — `onSaveDraft` никогда не передавался → клик был no-op. Auto-save в `goNext` уже работает. | `4be0b53` |
| 2026-05-12 | post-4 | **Pre-fill Шага 1 при «Пересобрать» (CA-058)** — borrower-карточка из досье тянется через sessionStorage (per-tab). `form.reset` Шага 1 при mount если нет draft. Финансы и кредит остаются пустыми. | `3fd0a34` |
| 2026-05-12 | post-4 | **Округление MARGIN evidence до 4 знаков (CA-021b)** — `low_margin_high_turnover` делил Decimal'ы с хвостом 20+ знаков (0.02160653715822424767 в PDF). `margin.quantize(Decimal("0.0001"))` перед сериализацией в evidence. +1 тест. | `20699d0` |
| 2026-05-12 | post-4 | **Валидация юр.адреса ≥15 симв + цифра (CA-038)** — Шаг 1 zod `registeredAddress`: `min(3)` → `min(15)` + refine на наличие цифры (номер дома). «Ташкент» больше не проходит. +4 теста (новый `schema.test.ts`). | `66cd56c` |
| 2026-05-12 | post-4 | **Inline warning «директор <90 дней» (CA-039)** — Шаг 1 под полем даты назначения amber-плашка `Назначение <90 дней — будет учтено как сигнал риска`. Pure-helper `isRecentDirectorAppointment(value, threshold=90, now)` с inject `now` для детерминированных границ. Порог exclusive (`diff<90`). +7 unit-тестов. | `5909082` |
| 2026-05-12 | post-4 | **Убран hardcoded documentsCount в SubHeader (CA-059)** — `documentsCount={5}` в callsite было vранье. `ApplicationOutput` +nullable `documents_count`, backend mapper не выставляет → None, фронт скрывает кнопку «Документы» при null/0. Status badge читал из `data.application.status` — там backend возвращает const `in_review` до approve/reject workflow, валидно. | `bf64ec3` |

> Сжатая история. Полные decomposition / smoke numbers / per-step rationale — в commit messages (`git log --oneline`) и `docs/adr/`.
