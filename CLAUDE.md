# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус, открытые задачи и рабочие соглашения.
> Историческая глубина: `docs/session-log.md` (полная история), `docs/design-sweep-archive.md` (per-phase narrative), `docs/operations/` (smoke-guides).

---

## Current Status

**Phase 10 (PDF document) закрыта 2026-05-15** (`a8f2b66`, CI `25934169074`). Финальная фаза Design Sweep — credit memorandum aesthetic: hero decision-block, observations pros/cons split, Section A identity hero с avatar + 3 stat tiles, brand-tenant через `BRAND_ID` env → `config/brands/<id>.json`, F-секция рендерит `rule.name` из YAML.

**Direction B (Design Sweep tail) — 8 batch'ей закрыто 2026-05-16:**
- **Batch 1A** (`680005e`) CA-DS17 + CA-DS24 — config-driven OKVED catalog + USD/UZS rate. Pattern `infrastructure/catalog/` зеркалит `infrastructure/brand/`. PDF/frontend single source через `GET /api/system/{okved,usd-rate}`, i18n keys `okved_XX_YY` удалены.
- **Batch 1B** (`9b38422`) CA-DS18 Level 1 — deterministic case_id `BR-YYYY-XXXX` из `draft.id` (4 hex). Hydration-safe, без `Math.random`. Banking-grade sequence → CA-DS18b после Phase 4 application entity.
- **Batch 2** (`d243c0f`) CA-DS20 + CA-DS23 — RTL backfill 32 теста на `InnInput`/`OkvedAutocomplete`/`SourceHint`/`UzsInputShell`. 3 named export'а для testability, семантика не тронута.
- **Batch 3** (`27e8365`) CA-DS22 + CA-DS19 — full keyboard nav в `CustomDropdown` (ARIA 1.2 combobox, Home/End/PgUp clamp, initial highlight = selected) + pulse cleanup на `/search` (live-strip + result-card). 11 RTL тестов.
- **Batch 4** (`c40e636`) CA-DS21 — `auto-edited` 3-state в source-trail. `SourceTrailContext` расширен parallel `parsedValues: Record<formPath, normalizedDigits>` map. `useFieldSourceState` сравнивает current с parsedValues — совпадает → `auto`, отличается (включая clear-to-empty) → `auto-edited` (info-tone borderbar, нейтральный suffix). `ParsedFilesDropzone.applyToForm` параллельно с `setValue` зовёт `mergeParsedValues`. +13 RTL тестов (SourceHint info-tone, borderbar, integration через HookProbe + parsedValues seeding + form.setValue transition).
- **Batch 5** (`2a99f24`) Hygiene — `default_usd_uzs_rate()` singleton (`@lru_cache(maxsize=1)`) mirror OKVED. Endpoint `/api/system/usd-rate` через singleton, `load_usd_uzs_rate(path)` остался uncached для path-override unit-тестов. Integration-test получил autouse `cache_clear` fixture. +2 pytest (singleton identity + env-cache lifecycle).
- **Batch 6** (`2c249f4`) CA-DS6/7/8 — `support` + `businessHours` секции в `config/brands/<id>.json`. Backend `SupportConfig`/`BusinessHours` nested dataclasses (default=None). Frontend `brandSchema` zod расширен, `BrandClient` пробрасывает оба поля; `useBrand().support` единственный источник для `help-view.tsx`. `business-hours.ts` принимает schedule param (fallback default). Persona block («Мадина А., available» mock) удалён — `feedback_mock_ui_on_decision_screens` паттерн. Compliance phone (CA-DS8) добавлен как отдельная строка в `HotlinePrimaryCard`. +5 pytest (brand_config support/businessHours parsing + invalid sections) +5 vitest (brand schema + custom schedule).
- **Batch 7** (`675e3f9`) CA-DS29 (UI part) — runtime locale switcher через cookie. `ca_locale` cookie (path=/, sameSite=lax, maxAge=1y, secure-в-проде, не httpOnly). `LocaleSwitcher` в `GlobalTopbar` (CustomDropdown RU/UZ) → server action `setLocaleAction` → `revalidatePath('/', 'layout')`. Server reads через `next/headers cookies()` в `layout.tsx` и `i18n/request.ts`. Fallback chain: cookie → `NEXT_PUBLIC_LOCALE` env → `DEFAULT_LOCALE`. Trade-off: cookies() делает все routes dynamic (ƒ вместо ○ в build output) — acceptable для bank-internal tool. PDF `?lang=` отложен в **CA-DS29-pdf** (pre-condition — UZ-translation PDF templates). +13 vitest (cookie parser + switcher RTL).
- **Batch 8** (`6680405`) CA-DS14/15/16 — 2FA tail cleanup. **CA-DS14**: новая phone_change FAQ в `/help` про MS Authenticator iCloud-cache scenario (self-recovery vs compliance escalation). **CA-DS15**: ADR-0012 `WebAuthn/Passkeys как alternative 2FA factor` с defer-decision (TOTP остаётся primary до post-pilot Phase 5+ когда CB РУз методики поддержат), implementation sketch + security checklist. **CA-DS16**: drop legacy stored bool `analysts.mfa_enabled` (миграция `c4f8a1d3e0b2`, upgrade drop + downgrade backfill из `mfa_enrolled_at IS NOT NULL`); cleanup в `analyst_repository.add`, `seed_analysts` (`--mfa-enabled` flag удалён), `bank/mfa.py` + `bank/admin.py`. API DTO `mfa_enabled` остаётся (computed), frontend contract не тронут. **Heads-up CA-DS16**: при applying новой миграции на existing prod-БД stored bool sync с `enrolled_at` уже идентичен (mapper computed-only), data-loss нулевой.

Закрыто 15 из 15 Design Sweep tail items 🎉. Frontend stack: 21 test files, 184 vitest tests. Backend: 839 pytest, 5 skipped (WeasyPrint GTK runtime). Открытые TODO с pre-conditions: **CA-003** (real ГНК lookup ждёт CA-DS28 legal review), **CA-024b** (CBU API ждёт legal review), **CA-DS18b** (Postgres sequence case_id ждёт Phase 4 application entity), **CA-DS18c** (formatCaseId year edge ждёт `draft.created_at` через useFormDraft), **CA-DS25** (KPI sparkline ждёт CA-029b cashflow parser), **CA-DS28** (ГНК ждёт legal review), **CA-DS29-pdf** (PDF `?lang=` ждёт UZ-перевод templates).

**Hotfixes 2026-05-16 после live-browser walkthrough:**
- **PDF polish** для реального BR-2026-0081 — 7 дефектов закрыты разом: id-details переверстаны с CSS Grid на `display: table` (WeasyPrint 68 grid vertical-align glitch); sev-pill padding/font подкручены (tight `1pt` снэпил background в ноль); flag.evidence border 0.5pt → 1pt; region-tile `.long` класс для длинных regional имён + `_parse_region` обрабатывает адреса без запятых; `_format_evidence_value` whitelist primary-keys с типизированным форматтером (закрывает Python repr leak `['2026-03-01', '2026-03-31']` → `23%`); chart fallback PNG с background-rect + `tight=False` (вместо обрезанного 200×80 лоскута).
- **Help nested-anchor** hydration error (`<a>` inside `<a>` в `HotlinePrimaryCard`, родилось в `2c249f4` CA-DS8 — никогда не работало, RTL stale). Outer обёртка → `<div>`, два независимых anchors (main hotline + compliance phone). Lesson `feedback_nested_anchor_rtl_blind`: RTL/jsdom не ловят HTML-validity, live-browser обязательно перед мержем.

**Dark theme + 3-theme switcher (CA-DS5) — 8 фаз закрыто 2026-05-16:**
- **Phase 1** — `[data-theme="dark"]` блок в `globals.css` (~50 семантик-токенов: surfaces, ink, border, sidebar/nav, state, brand, chart, shadcn defaults). `@media (prefers-color-scheme: dark) [data-theme="system"]` обёртка обслуживает первый paint когда LS == `system`. `ds-grid-pattern` инвертирована через новый `--grid-line-color`. Brand-primary остаётся константой в обеих темах — tenant identity; soft/ring/ink/hover production-варианты для dark surface.
- **Phase 2** — SSR no-FOUC: blocking inline `<script>` в `<head>` (минифицирован, try/catch) проставляет `data-theme`/`-density`/`-font-scale`/`-reduced-motion` до hydration. Reload без white→dark flash.
- **Phase 3** — `useAppearance` разблокирован: dark/system swatches active, `useEffect` с `matchMedia('(prefers-color-scheme: dark)').addEventListener('change')` для live system-mode sync. `disabled`/`wipLabel` props + i18n key `ap_theme_wip_sub` удалены (мёртвый код).
- **Phase 4** — audit ~30 файлов: `bg-white` → `bg-[var(--surface)]`, `bg-white/N` → `bg-[var(--surface)]/N` или `bg-[var(--surface-2)]`, `placeholder:text-[#9BA3B3]` → `var(--ink-4)`. QR-canvas / Theme-swatch preview / showcase-bar / accountant-sidebar tenant-identity оставлены литералами (semantic constraint или fixed-dark wrap). ESLint `no-restricted-syntax` guard расширен на `src/app/**` с явным `ignores` списком для legit-литералов.
- **Phase 5** — charts (revenue-24m + sparkline + score-gauge) уже использовали `var(--chart-*)` / `var(--ink-*)`, theme-aware без правок. PDF chart_renderer не тронут (light forever per ADR-0013).
- **Phase 6** — +18 vitest (`use-appearance.test.ts` × 11: LS persist, applyToDocument, matchMedia subscribe/unsubscribe, default fallback; `appearance-section.test.tsx` × 7: 3 swatches enabled, aria-pressed, click меняет data-theme).
- **Phase 7** — **ADR-0013** `Three themes (light/dark/system) — PDF light forever`. Context (glare fatigue + compliance evening use-case + WCAG headroom + OS preference respect), Decision (3 темы web + PDF locked), Rationale (PDF = audit print artifact, аудиторы привыкли к white-paper, ~12-16ч инженерного re-skin'а не оправдан), trade-offs (Segmented hierarchy inversion в dark, uzbekbank dark = generic slate без cream-sidebar identity).
- **Phase 8** — verify: ruff ✓, tsc ✓, ESLint ✓ (0 errors), vitest 202/202 ✓ (было 184), next build ✓ (24 routes). Backend mypy/pytest падает на pre-existing condition (`tests/` не смонтирован в docker, in-src `*_test.py` не находят `tests.fixtures.*`) — не моя регрессия, фронтенд-only change.

Heads-up: **live-browser smoke** через `/`, `/search`, `/history`, `/dossier/{id}`, `/help`, `/settings` × 3 темы — НЕ выполнен в этой сессии (требует ручного браузерного walkthrough). Lesson `feedback_nested_anchor_rtl_blind` ещё актуален: RTL/jsdom не ловят visual regressions. Перед мержем в продовой ветке пройти smoke. Открытые subtle-риски: (1) Segmented control в dark mode инвертирует визуальную иерархию (active-pill darker than track) — задокументировано в ADR; (2) `uzbekbank` brand-tenant в dark теряет cream-sidebar identity — приемлемый trade-off.

**Активная ветка:** `main`.

---

## Pre-Demo Roadmap

> **Полный документ:** `docs/pre-demo-roadmap.md` (Tier-декомпозиция, acceptance, заблокированные, backlog).
> **Critical rule:** работаю ТОЛЬКО над активным Tier. Всё что не в Tier 0–4 — Frozen.

### Active Tier 0 — Deal-breakers
- **T0.1** Real soliq fixtures via personal ETSP (3–4 фирмы × 5 типов = 15–20 xltx, gitignore + анонимизированные в git).
- **T0.2** CBU API real integration (CA-024b) — live USD/UZS rate + caching + legal review параллельно.
- **T0.3** ГНК Phase A: manual upload справок (CA-003 Phase A). Public lookup отложен до legal-clearance.
- **T0.4** UZ-локализация PDF (CA-DS29-pdf) — templates + `Rule.name_uz` + YAML migration + endpoint `?lang=`.

### Tier 1–4 (после T0)
- **T1** Prod-killers: case_id sequence (CA-DS18b/c), refresh-token rotation + Redis (CA-019), PII encryption at rest (column-level через app-layer, **не наивный pgcrypto на JSONB** — см. ADR-0014 to write), multi-tenant runtime isolation (BRAND_ID env + startup assertion), LDAP/OAuth (CA-020).
- **T2** Data quality: dynamic units FORM_2 (CA-028), VAT real formats (CA-015), PROFIT_TAX (CA-029b → закрывает CA-DS25), faktura.uz (CA-DS11).
- **T3** Operational readiness: observability (CA-064), structured logging + correlation_id, Prometheus/Grafana, pg_dump backup, audit-log export, Ansible/systemd deploy.
- **T4** Compliance pack (параллельно с T1–T3): pentest от лицензированной узб-лаборатории, аттестат УзСтандарта на ПДн, резидентство в IT-юрисдикции РУз, Admin Guide + Security Architecture + DRP/BCP (RU + UZ).

### Frozen scope (не трогать до post-demo)
- UI polish: новые цвета, шрифты, тени, анимации.
- Расширения dark theme, 4-я тема, accent variants.
- Новые design tokens, brand-tenant новые секции.
- CA-DS25 (KPI sparkline) до T2.3, новые OKVED-каталог расширения сверх baseline.
- i18n keys refactor, новые ADR по визуальному дизайну.
- Coverage сверх baseline ради числа — кроме тестов на новый Pre-Demo код.
- Refactor без бизнес-причины из roadmap.

---

## Активные договорённости (compact)

### Domain / data contracts
- **VAT-периоды** (ADR 0006): `BorrowerSnapshot.vat_periods: list[VatPeriodReport]`. Декларация → `vat_declared`, ilova → `esf_seller_vat_total`. Сравнение в рамках одного налогового периода.
- **ИНН заёмщика**: приходит явно от пользователя, не угадывается из имени файла.
- **xltx форматы (5 типов)**: VAT_DECLARATION (8 листов), VAT_REGISTRY_ILOVA (10, Приложение №4), FORM_2_INCOME_STATEMENT (3), FORM_1_BALANCE_SHEET (4), PROFIT_TAX (15). Distinguished по сигнатурным cells list01.
- **Парсер soliq_xltx best-effort**: raises только на формат (UnsupportedFormatError, XltxBorrowerMismatchError); cell-level → warn + None. Каждый DTO имеет `parse_warnings: list[str]`.
- **Реальные данные папы**: локально в `~/Downloads` / `tests/fixtures/**/*_full.*`, не в git. В repo — `*_sample.csv` + synthetic factory-helpers.

### Persistence / infra
- **Persistence**: testcontainers + real Postgres для integration-тестов; draft TTL = 30d.
- **Compose-postgres** на host **5433** (5432 занят native PG).
- **Windows + asyncpg**: обязателен `WindowsSelectorEventLoopPolicy` (настроено в `migrations/env.py` + `main.py`).
- **Backend в Docker** (ADR 0008): WeasyPrint требует Pango/HarfBuzz/Fontconfig. Compose `api` на 8000. Правки кода → `docker compose up -d --build api`, не `restart` (см. memory `project_docker_crlf_gotcha.md`).
- **Phase 4 — Bank Mode** (ADR-0009): `APP_MODE` env управляет инсталляцией. Bank: shared endpoints закрыты `Depends(get_current_analyst)`. Audit `login/login_failed/logout/search_borrower/view_dossier/generate_dossier/download_pdf` пишется в `audit_log`. `dossiers.source_mode` + nullable FK `created_by_analyst_id`.
- **JWT** (Phase 4.B): native `bcrypt`, HS256, access 15м + refresh 7д без ротации в v1. `JWT_SECRET` через env, мин. 32 байта в проде.
- **Frontend BFF cookies**: httpOnly + sameSite=lax + secure-в-проде. Tokens в `ca_access` (path=`/`) и `ca_refresh` (path=`/api/auth`). Client JS никогда не видит JWT.
- **Seed analyst**: `docker compose exec api bash -c "cd /app/src && uv run --no-sync python -m interfaces.cli.seed_analysts --email ... --password ... --full-name ..."`.

### Rules / KPI conventions (изменяешь — обновляй sync)
- **CA-044** Money | None: `FinancialReport.taxes_paid` опциональный сквозь стек. `None` = «не заполнил», `Money(0)` = «осознанно ноль». Frontend mapper `moneyOptional(digits)` → `undefined` при пустой строке.
- **CA-043** `fmt_pct` контракт: принимает значение **уже в процентах** (consistent с kpi_calculator: `(a-b)/b*100`). Не fraction.
- **CA-037** KPI naming: EBIT = `profit_before_tax + interest_expense` (компонент EBITDA без D&A). UI рендерит «EBIT (прокси EBITDA)» + tooltip. Когда D&A появится — добавляем `ebitda` / `debt_to_ebitda` **рядом**, не переименовываем.
- **CA-037** Snapshot JSONB round-trip: новые nullable поля `FinancialReport` сериализуются в JSONB через `_financial_report_to_dict`/`_from_dict`. **Расширяешь FinancialReport новым полем — обязательно добавь в snapshot_mapper и unit-тест round-trip**.
- **CA-047** BalanceSnapshot: 8 балансовых полей сгруппированы в `domain/value_objects/balance_snapshot.py`. Wire contracts остались flat для обратной совместимости.
- **CA-042** FORM_2 tier priority: `header.period_year == year` (CURRENT) > `year + 1` (PRIOR). CURRENT silently перезаписывает PRIOR.
- **CA-049** NEGATIVE_EQUITY rule: critical-severity, на `latest_annual.balance_end.equity ≤ 0`. **Новое правило — обновляй YAML+CODE_RULES синхронно**: `load_registry()` raises на асимметрии.
- **CA-048** KPI threshold coloring: пороги ROE (>15 GOOD / 5-15 WARN / <5 BAD) и Debt/EBIT (<2 / 2-4 / >4) — single source of truth в `kpi_calculator.py`, не дублировать на frontend/PDF.
- **CA-035b** Readiness в готовом досье: GET `/api/dossier/{id}/readiness`. `source_trail` в БД не хранится; `infer_parser_sources_from_snapshot` heuristic.

### Frontend conventions
- **CA-053** strict-mode useEffect: `cancelled`-guards в `.finally()` опасны для terminal UI-flags (loading/error). Для UI-flags `setIsLoading(false)` ставь безусловно.
- **CA-058** prefill Шага 1: при «Пересобрать с дополнениями» — borrower-карточка через sessionStorage (`ca:manual-input-prefill-step1`). Финансы и кредит остаются defaults.
- **CA-060** Design tokens (ADR-0011): один design system, brand-tenant через `config/brands/<id>.json`. Semantic слой в `globals.css`: `--surface/-2/-3`, `--ink-1..4`, `--state-{ok,warn,bad,info,neutral}-{fg,bg,border}`, `--brand-primary/-hover/-soft/-ink/-ring`. Chart-палитра 9 токенов. **CA-DS5 / ADR-0013**: `[data-theme="dark"]` блок переопределяет все семантик-токены под slate/anthracite. `[data-theme="system"]` живёт под `@media (prefers-color-scheme: dark)` + live matchMedia listener в `useAppearance`. SSR no-FOUC inline script в `<head>`. PDF досье locked light forever — `dossier_pdf.py` игнорит current theme.
- **CA-061** mode-conditional (ADR-0011): `if (mode === "bank")` запрещён глубже top-level shells. Хук `useAppMode()` (`web/src/lib/use-app-mode.ts`) — единственная точка для client-shells.
- **CA-062** ESLint hex guard: `no-restricted-syntax` для `src/features/**` + `src/components/**`. **Не ловит** Tailwind utility `bg-[#XXXXXX]` — ручная гигиена.
- **CA-063 / CA-DS29** i18n infra: `next-intl` 4.4.1, runtime locale switcher через `ca_locale` cookie (CA-DS29) с fallback на `NEXT_PUBLIC_LOCALE` env → `DEFAULT_LOCALE`. Keys в `web/src/i18n/{ru,uz}.json` (keyspace `shared/bank/accountant/dossier`). RTL-тесты обёртывать в `<NextIntlClientProvider locale="ru" messages={ru}>`. **Server reads cookie через `next/headers cookies()`** — layout.tsx и i18n/request.ts: единый source of truth. Smena локали → server action `setLocaleAction` → `revalidatePath('/', 'layout')`, без page reload. **Trade-off**: `cookies()` в layout делает все routes dynamic — не страшно для bank-internal tool. **Brand-strings (имена, теглайны) не локализуются** — это tenant-config. **PDF endpoint игнорит current locale** — рендер всегда на server brand-default, переключение `?lang=` ждёт CA-DS29-pdf (templates пока RU-hardcoded).
- **CA-066** brand-context client-side: server `resolveBrand()` + `<html data-brand>` + `BrandProvider` + `useBrand()` (`web/src/lib/brand-context.tsx`). Tagline в brand-config — **полная** строка. **CA-DS6/7/8** добавили optional `support` (phone/email/slack/docs/compliancePhone) + `businessHours` (timezone + weekdays.start/end) — `useBrand().support` / `.businessHours` рендерятся в `/help`. Backend `SupportConfig`/`BusinessHours` живут только в brand-config, **PDF их не использует** — это frontend-only расширение.
- **CA-066** `t.rich` gotcha: для ReactNode-обёртки message **обязан** иметь tag-плейсхолдер `<x></x>`, не value `{x}`. Иначе «Functions are not valid as a React child».
- **Phase 8 SectionCard / CounterChip / StaticPill** (`web/src/components/section-card.tsx`): shared shell — wizard передаёт `icon`, dossier нет (header grid схлопывается). Visual-only, без i18n bindings. **Не дублировать pattern локально** — 10+ consumer'ов через shared.
- **Phase 7 source-trail UI** (Step 2, расширено CA-DS21): 3-state — `auto` (зелёный borderbar + suffix), `auto-edited` (info-синий borderbar, нейтральный suffix — parser-cap снят правкой), `manual` (серый), плюс спец `manual-required` (amber для taxesPaid). Borderbar реализован как `absolute span` (не CSS-border — мешает UZS-suffix). `useFieldSourceState` читает `parsedValues[fieldName]` из `SourceTrailContext` и сравнивает с current digits; fallback на legacy `sourceTrail[mapping.key]` для не-CA-DS21 источников.
- **Phase 10 PDF brand-tenant**: `BRAND_ID` env → `config/brands/<id>.json` через `infrastructure/brand/`. `BrandConfig` dataclass в `application/dto/` (clean architecture — pure), loader в `infrastructure/`. Backend mirror фронтового `resolveBrand()`, single source of truth — JSON в `config/brands/`. Шрифты PDF строго bundled 400/500/600/700 (no 800 — fallback в WeasyPrint).
- **Phase 10 Observations builder** (`application/services/observations_builder.py`): cover bottom half. Strengths derived from positive KPI: revenue growth · ROE≥GOOD · positive net profit · low debt (cap 3). Risks = top-3 red flags by severity (critical → high → medium → low). Rule name lookup через `RuleRegistry.by_id(rule_id).name` из YAML.
- **Phase 10 Rule.name field**: добавлено в `domain/rules/rule.py`, пробрасывается через `registry_factory` синхронно с `config/rules/v*.yaml`. PDF F-секция рендерит human-readable name; rule_id остаётся в `.src` строке как technical reference для аудитора.
- **Batch 1A catalog pattern (CA-DS17/CA-DS24)**: reference-данные (OKVED, USD rate) — JSON в `config/<topic>/`, DTO в `application/dto/<topic>.py` (pure dataclass), loader в `infrastructure/catalog/<topic>.py`. Backend (PDF, services) читает через singleton catalog (`@lru_cache(maxsize=1)`), frontend через React Query на public endpoint `GET /api/system/<topic>` (catch-all BFF проксирует). **Не плодить hardcode**: новый reference-каталог → JSON + DTO + loader, не словарь в feature-модуле. **i18n keys для catalog labels** запрещены — labels внутри JSON `name_ru`/`name_uz`, frontend выбирает через `useLocale()`. Brand-tenant strings (имена банков) живут в `config/brands/`, не локализуются.

---

## Design Sweep status

| # | Phase | Status | Commit |
|---|---|---|---|
| 1 | Login | DONE | `0a1c86c`..`34d97f6` |
| 2 | Search | DONE | `c9afbce` → `022dfcf` |
| 3 | History | DONE | `8bbc154` |
| 4 | Help | DONE | `cb8b046`..`91c4090` |
| 5 | Settings | DONE | `06f0ae4` + Phase 5.B + functional holes |
| 6 | Manual-input Step 1 (Borrower) | DONE | `d2fb869` + `c116908` |
| 7 | Manual-input Step 2 (Financial) | DONE | `40c770d` |
| 8 | Manual-input Step 3 (Loan) | DONE | `94229e8` |
| 9 | Dossier view | DONE | `bcde558` |
| 10 | PDF document | DONE | `a8f2b66` |

Подробности по каждой фазе — `docs/design-sweep-archive.md`.

---

## Working Agreements

- Перед каждой задачей: перечитай PROJECT_BRIEF.md Section 4 (Architecture) и Section 11 (Anti-patterns).
- Plan mode обязателен если затрагивается >2 файлов.
- Не начинай кодить без плана — сначала покажи декомпозицию.
- Язык UI: русский. Язык кода: английский.
- Коммиты: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- **В commit messages никогда не упоминать `claude` / `AI` / `assistant` / `agent` / `LLM` / `GPT`** — ни в subject, ни в body, ни в scope. Для коммитов трогающих `CLAUDE.md` использовать scope `docs(rules)` / `docs(internal)` / `docs(arch)`, не `docs(claude)`. Commits должны читаться как написанные мной вручную.
- Никаких `TODO` без ID (`# TODO[CA-001]: описание`).
- После `git mv` + правок (sed/Edit) обязателен `git add -u` или явный re-add (см. memory `feedback_git_mv_sed_gotcha.md`).

### Pre-push checklist

Перед `git push` прогнать **полный** verify:

1. **`npm ci` ≠ `npm install`**. После добавления зависимости — `rm -rf node_modules package-lock.json && npm install`, потом `npm ci` локально чтобы воспроизвести CI-режим.
2. **`ruff check` + `mypy --strict` + `pytest`** обязательны перед push. Минимум: `docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest"`.
3. **Меняешь computed-from-X invariant — `grep -r` все тесты на эту semantic.** Локальный mapper-test может пропустить интеграционный тест.
4. **CI коммита перед твоим зелёный?** `gh run list --branch main -L 3` перед началом работы.

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
- Soliq данные — только через официальный экспорт/API, не scraping (исключение — публичный лукап `soliq.uz/services/search/` после legal review, см. CA-DS28).
- `.env` не в git, secrets через Vault в production.

---

## Operations playbooks

- **2FA smoke (4 пути, ~10 мин)** — `docs/operations/2fa-smoke.md`.

---

## Start of Session Command

```
Прочитай @PROJECT_BRIEF.md целиком, потом @CLAUDE.md.
Скажи на каком phase мы сейчас и какая следующая atomic задача.
Не начинай кодить — сначала покажи план.
```

Если нужна историческая глубина:
- `docs/session-log.md` — полная хронологическая история по сессиям с commit hashes
- `docs/design-sweep-archive.md` — детали Phase 1-9 (preview HTML, иттерации, lessons)
- `docs/operations/2fa-smoke.md` — пошаговая инструкция smoke 2FA
- `docs/adr/` — Architecture Decision Records (0001..0011)
