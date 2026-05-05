# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус проекта и рабочие соглашения.

---

## Current Status

**Phase:** 4 закрыта (Bank Mode UI) + UI Design System sweep 2026-05-13 (Phase 0-8 плана + Phase 9 partial) + post-plan design-parity sweep 2026-05-13 (CA-066) + post-CA-066 cleanup (CA-067) + CA-065 commit writer + Design Sweep 2026-05-13 (Phase 1 Login + Phase 2 Search + Phase 3 History done, 7 фаз pending). Specs: `docs/superpowers/specs/2026-05-11-phase-4-bank-mode-design.md`, `docs/superpowers/plans/2026-05-13-ui-design-system.md`, ADR-0009, ADR-0011.

**Активная ветка:** `main`. Серия CA-060..CA-063b (один design system + brand-layer): semantic tokens, ESLint guard hex, useAppMode shells, error boundaries, GlobalTopbar + ⌘K палитра, JetBrains Mono на KPI, pulse-dot draft-save, formatBusinessAge, login sync с brand, demo-seed 3 UZ MSB, i18n infra (next-intl + ru/uz) + полный sweep всех UI surfaces (8 ключевых в CA-063 + manual-input wizard + dossier sub-views + bank shell/settings/help + shared topbar + bank-api.recommendationLabel в CA-063b). + CA-066 post-plan design-parity: brand-context client-side, info-banner на state-info токены, ⌘K keyboard nav, dossier layout aligned with target preview (clean sub-header + Готовность как 4-й KPI, ActionBar удалён). Phase 5 (E2E папы / pilot-демо) ожидает старта.

**Verify status:** ruff + mypy --strict + 666 passed (3 skip: 2 PDF-WeasyPrint, 1 testcontainers) + tsc + eslint (no-restricted-syntax ban hardcoded hex/rgba в features/components) + next build (15 routes) + vitest (61 tests) — зелёные. CI зелёный после `fd005a1`. Docker smoke сохранён от CA-058 — real fixture папы (ИНН 201308534).

---

## Открытые TODO

- TODO[CA-003]: реальный лукап ГНК для ИНН (сейчас pill «Проверено в ГНК» по 9-значной валидации формата).
- TODO[CA-015]: уточнить `vat_declaration_parser.py` под живые xltx 10006_45/10006_47 — детектор опознаёт через widened sentinel + structural fallback (CA-012), но cells F6/G6/F7-F11/G7 могут быть смещены. Ждём реальные файлы.
- TODO[CA-019]: refresh-token rotation + denylist (Redis) — в v1 refresh stateless 7д без инвалидации. ADR-0009 fixes path к v2.
- TODO[CA-020]: LDAP/OAuth AuthnAdapter для production-банка. AuthnPort готов (`application/ports/authn_port.py`), нужен новый adapter в `infrastructure/auth/`.
- TODO[CA-028]: dynamic unit detection для FORM_2 — сейчас hardcoded ×1000, читать B24 list01 («Единица измерения, …»).
- TODO[CA-029b]: парсер PROFIT_TAX (taxes_paid, 15 листов) — adapter raises UnsupportedFormatError. По образцу FORM_2/FORM_1 + реальные xltx папы.
- ~~TODO[CA-063b]: i18n sweep оставшихся surfaces~~ — **закрыт 2026-05-13**. Swept в 5 коммитов: manual-input wizard (14 файлов: page-head/stepper/form-footer/info-banner + step-1..3 + financial-table/dscr-summary/dscr-gauge/parsed-files-dropzone/soliq-upload/checklist; `lib/finance.classifyDscrRisk` теперь возвращает `key` вместо hardcoded label), dossier sub-views (sub-header/borrower-card/kpi-row/risk-signals/revenue-24m-chart/score-gauge/readiness-badge), bank shell (`(bank)/_components/topbar` + settings/help-view с FAQ через `t.rich`), shared `components/topbar.tsx` (draft badges), удалён `lib/bank-api.recommendationLabel` → callsites на `bank.history.rec_*`. Полный keyspace `accountant.manual_input.*` / `dossier.*` / `bank.{topbar,settings,help}.*` в ru+uz. См. `757d0ba..d923051`.
- TODO[CA-064]: ship error.tsx в real observability (Sentry / posthog) когда подключим. Сейчас только `console.error`.
- ~~TODO[CA-067]: rm orphaned `back-target.ts`~~ — **закрыт 2026-05-13** (`56ada78`). `web/src/features/dossier/back-target.ts` удалён + `rememberBackTarget("/search"|"/history")` убраны из search/history-view.
- ~~TODO[CA-065]: `scripts/seed_demo_borrowers.py --commit`~~ — **закрыт 2026-05-13** (`04665b1`). Пишет 3 demo bank-mode dossier'а через стандартный E2E (build_borrower_snapshot → run_rules → save). 2 годовых + 24 monthly из seasonality. `source_mode='bank'`, `created_by_analyst_id=NULL`. Smoke real Postgres: 3 dossiers score=0/approve (зелёный demo-borrower). Запуск: `docker compose exec api bash -c "cd /app && PYTHONPATH=/app/src uv run --no-sync python -m scripts.seed_demo_borrowers --commit"`.

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
- ~~**CA-055 back-target в досье**~~ — **удалён в CA-067** (`56ada78`). После CA-066 (нижний ActionBar удалён физически) consume-стороны не осталось — `back-target.ts` снесён, `rememberBackTarget()` в search/history тоже. Если вернём back-кнопку в шапку досье — можно перевнедрить тот же sessionStorage-pattern.
- **CA-058 prefill Шага 1:** при «Пересобрать с дополнениями» borrower-карточка из досье тянется через sessionStorage (`ca:manual-input-prefill-step1`). `rememberStep1Prefill(borrower)` в ActionBar.handleRebuild, `consumeStep1Prefill()` в manual-input-view.useEffect (только если нет draft — draft.payload приоритетнее, удаляется ключ при consume). Финансы (Шаг 2) и кредит (Шаг 3) остаются defaults — для них и пересобирают.
- **CA-060 design tokens (ADR-0011):** один design system на bank+accountant, brand-tenant через `config/brands/<id>.json` (default = blue, uzbekbank = terracotta). Loader `web/src/lib/brand.ts` через `fs.readFileSync` (server-only). BRAND_ID env → `data-brand` атрибут на `<html>` + inline cssVars. Semantic слой в `globals.css`: `--surface/-2/-3`, `--bg`, `--ink-1..4`, `--border`, `--border-strong`, `--nav-bg/-2/-hover/-border/-text/-2/-3`, `--state-{ok,warn,bad,info,neutral}-{fg,bg}` + `-border` (ok/warn/bad), `--brand-primary/-hover/-soft/-ink/-ring`. Чарт-палитра: `--chart-{red,orange,yellow,green,blue,grey,grid,track,track-light}`. Bank-tenant overrides в `:root[data-brand="uzbekbank"]`. Shadcn-defaults (`--primary`, `--ring`, `--accent`, `--accent-foreground`, `--sidebar-primary`) делегируют в brand. **Legacy `--ca-*`/`--ub-*` удалены — sed-mass-replace проведён 437c0d9/ab3a679.**
- **CA-061 mode-conditional (ADR-0011):** `if (mode === "bank")` запрещён глубже top-level shells. Хук `useAppMode()` (`web/src/lib/use-app-mode.ts`) — единственная точка для client-shells (AppShell, BankSidebar, ActionBar, DossierView — page-level). Server components (layouts) используют `APP_MODE` напрямую — `useAppMode` это client-only. Features принимают props (`backHref`/`backLabel`) — пример `DossierError`. **Settings-view внутри `(bank)/` имеет mode="bank" hardcoded** (route-group invariant, не conditional).
- **CA-062 ESLint hex guard:** `no-restricted-syntax` в `web/eslint.config.mjs` для `src/features/**` + `src/components/**`. Ловит `Literal[value=/^#[0-9A-Fa-f]{3,8}$/]` (whole-string hex), `TemplateElement` с `#hex` в backticks, `Literal[value=/^rgba?\(/]`. **Не ловит Tailwind utility-классы вида `bg-[#XXXXXX]` в обычных string literals** — там pattern `^#XXXXXX$` не сматчит, нужна ручная гигиена (CA-062 swept score-gauge/kpi-card/revenue-chart/dscr-gauge/dossier-skeleton/financial-table/step-1-borrower).
- **CA-066 brand-context client-side:** server `resolveBrand()` + `<html data-brand>` остаются source of truth для CSS-переменных, плюс `BrandProvider` + `useBrand()` (`web/src/lib/brand-context.tsx`) пробрасывают `{id, name, tagline, logoMark}` в client surfaces. Wired в `app/layout.tsx` через `Providers brand={...}`. Bank `Sidebar` + `BankTopbar` берут отображаемые строки из `useBrand()` — больше нет хардкода «Uzbekbank Credit / UB / Bank Mode · Андижон» в коде. Tagline в brand-config — **полная** строка (включая локацию филиала), один tenant = один config = одна tagline.
- **CA-066 dossier layout (design-parity):** `features/dossier/sub-header.tsx` — чистый `<h1>` + meta-line `ИНН · ОПФ · ОКВЭД` + правые [Пересобрать] [Скачать PDF]; убраны eyebrow `application_label`, status-badge, кнопки «Документы» / «Карточка клиента». `KpiRow` теперь 4 карточки `EBIT / ROE / Долг·EBIT / Готовность данных` (revenue_ltm выкинут — отдельная карточка не нужна, число всё равно в Раздел A карточке). `ReadinessBadge` → `ReadinessKpiCard` (4-я в KPI-row), отдельный pill сверху удалён. Нижний `ActionBar` удалён физически (`action-bar.tsx`); действия только в шапке. `back-target.ts` + `rememberBackTarget()` в search/history оставлены orphaned (no-op writes в sessionStorage), могут пригодиться при возврате back-кнопки в шапку — отдельный TODO[CA-067] на удаление если решим что не вернём.
- **CA-066 t.rich gotcha (history pagination fix):** `t.rich(key, {x: () => <b/>})` падает с «Functions are not valid as a React child» если в message используется value-плейсхолдер `{x}` (не tag-плейсхолдер `<x></x>`). next-intl пытается подставить функцию как value → React traceback. Правильно: либо value-плейсхолдер `{x}` + value-substitution через `t(key, {x: 42})` (но тогда нельзя ReactNode), либо tag-плейсхолдер `<x>{value}</x>` + `t.rich(key, {value, x: (chunks) => <b>{chunks}</b>})`. Применяй tag-syntax везде где нужна обёртка вокруг подстановки.
- **CA-063 i18n infra:** `next-intl` 4.4.1, статичная локаль через `NEXT_PUBLIC_LOCALE` env (ru | uz), один UI-язык на инсталляцию (без routing-switcher). Keys в `web/src/i18n/{ru,uz}.json`, keyspace разбит на `shared/bank/accountant/dossier`. Loader `web/src/i18n/index.ts`, server-config `web/src/i18n/request.ts`, plugin в `next.config.ts` (`createNextIntlPlugin("./src/i18n/request.ts")`). `NextIntlClientProvider` в `RootLayout` оборачивает `<Providers>`. `<html lang>` берётся из resolved locale. **Useпаттерн:** client → `import { useTranslations } from "next-intl"; const t = useTranslations("section");`. Server → `import { getTranslations } from "next-intl/server"; const t = await getTranslations("section");`. **Тесты:** RTL-тесты на компонент с `t()` оборачивать в `<NextIntlClientProvider locale="ru" messages={ru}>` (см. `global-topbar.test.tsx`). Swept ru-strings → keys в 8 surfaces (bank sidebar, search-view, history-view, login-view, accountant sidebar, GlobalTopbar, CommandPalette, DossierError + error/not-found pages); остальное — TODO[CA-063b]. **Brand-strings типа «Uzbekbank Credit», «CreditScope», «Bank Mode · Андижон» — НЕ локализуются**, это tenant-config (`config/brands/<id>.json#name|tagline`) или ad-hoc copy.

---

## Design Sweep 2026-05-13 (10 фаз, in-progress)

**Процесс:** 1 фаза = preview HTML в `web/design-reference/2026-05-13-{phase}-preview.html` → user approves → 1 commit → переход к следующей. Строго по очереди, без перепрыгивания.

**Фазы (по E2E flow аналитика + sub-views):**

| # | Phase | Status | Preview file | Commit |
|---|---|---|---|---|
| 1 | Login | **DONE** | `2026-05-13-login-phase1-preview.html` | `0a1c86c`..`34d97f6` |
| 2 | Search | **DONE** (design statement + 4 hotfix) | `2026-05-13-search-phase2-preview.html` | `c9afbce` → `022dfcf` |
| 3 | History | **DONE** (design statement) | `2026-05-13-history-phase3-preview.html` | pending commit |
| 4 | Help | pending | — | — |
| 5 | Settings | pending | — | — |
| 6 | Manual-input Step 1 (Borrower) | pending | — | — |
| 7 | Manual-input Step 2 (Financial) | pending | — | — |
| 8 | Manual-input Step 3 (Loan) | pending | — | — |
| 9 | Dossier view | pending | — | — |
| 10 | PDF document | pending | — | — |

### Phase 1 — Login (scope) — DONE 2026-05-13

**Final values (decided 2026-05-13):** subtle scale-up (≤+9%, card-width только +2.9%, padding unchanged). Card footprint почти оригинальный, content — title/inputs/CTA — увеличен. Все animations сохранены (drift A/B, mousemove spotlight, parallax card, pulse-dot, focus rings).

Изменения (9 значений):
- Card `max-width` 384px → **355px** (−7.5%, card compacted — content внутри scaled-up = плотный focused card)
- Card padding 36/32 → **36/32** (unchanged)
- Title (h1) 28px → **30px** (+7%)
- Subtitle 13px → **13.5px** (+4%)
- Input height 44px → **48px** (+9%), font 13.5px → **14px** (+4%)
- Label font 10.5px → **11px** (+5%)
- CTA height 46px → **50px** (+9%), font 13.5px → **14px** (+4%)
- Form gap 14px → **15px** (+7%)

**Out-of-scope (отложено на cross-phase tech-debt, см. ниже):** #1 brand-context wiring, #2 mock-кнопки (Remember-me/Forgot-password), #3 outline CTA → filled, #4 «AUTHENTICATION» i18n, #5 hardcoded © 2026 + tenant.

**Files changed:** `web/src/app/login/_components/login.module.css`.

**Phase 1 follow-ups (same day):**
- `-webkit-autofill` override (`4997d5b`) — Chrome autofill белил dark input. Inset box-shadow 1000px + `transition: background-color 9999s` держит dark theme.
- Card fine-tune (`8dc74cb` 395→380, `34d97f6` 380→355) — user итерировал размер до final **355px** (focused-positioning: Stripe/Linear/Tinkoff territory, не enterprise wide как TBC/Chase).

### Cross-phase technical debt (открытый список)

Issues которые я нашёл в аудитах но user решил оставить — фиксируем чтобы не потерять. Можно вернуться к ним отдельным sweep после design-фаз.

- **CA-DS1 (login):** Brand «UB / Uzbekbank Credit / BANK MODE» захардкожены в `LoginView.tsx`. CA-066 brand-context до Login не дошёл. На любом не-UB tenant сломает Phase 5 pilot demo. Fix: `useBrand()` для brand-mark + name + tagline.
- **CA-DS2 (login):** «Запомнить» checkbox + «Забыли пароль?» link — оба no-op (mock). Либо implement, либо удалить.
- **CA-DS3 (login):** Eyebrow «AUTHENTICATION» — единственный english string в UI. CA-063b sweep пропустил.
- **CA-DS4 (login):** `© 2026 Uzbekbank` — год + tenant hardcoded. `placeholder="имя@uzbekbank.uz"` тоже. Заменить на `getFullYear()` + brand-config + i18n.
- **CA-DS5 (login CSS):** ~25 hex значений в `login.module.css` (dark-theme tokens), ESLint guard CSS не покрывает. Нужен dark-theme semantic слой.
- ~~**CA-DS-LIVE (search):** Live-strip mock~~ — **закрыт `610a86d`/`4e9fcf0`**. Backend endpoint `/api/bank/stats/today` + BFF route + useQuery wiring. Real-time numbers из реальной БД.

### Phase 2 — Search (scope) — DONE 2026-05-13

**Решение:** design statement (не subtle scale-up). Phase 2 переходит от косметики к premium-bank эстетике — частный банк Loewe/Brunello Cucinelli, не SaaS-стартап.

**Изменения:**

*Backend* — `GET /api/bank/borrowers/search` расширен `card: SearchCardData | null` (заполнено только когда есть bank-mode досье). Новые поля: `legal_form`, `recommendation`, `revenue_ltm` (Decimal-str), `yoy_pct`, `business_age_months`, `signals_total`, `signals_evaluated`, `monthly_revenue_12m: list[{month: "YYYY-MM", revenue: "..."}]`. Реализовано через `LoadDossierForView(repo).execute(dossier_id)` в `search.py` — переиспользует существующий use case + KPI calculator, никакой бизнес-логики в endpoint. +2 integration теста.

*Frontend foundation:*
- `globals.css`: bank-tenant override `--nav-bg: #FAF9F5` (warm cream) + nav-text-* для light sidebar; новые keyframes `pulse-ring-ok`, `rise`, `rise-card`, `ds-orb-drift-a/b`; utility class `.ds-grid-pattern` (40×40 квадраты с radial mask).
- 4 новых компонента в `features/search/`: `GridPattern`, `AmbientOrbs` (two-layer wrap — JS-параллакс снаружи, CSS-keyframe drift внутри), `ScoreRing` (112px donut + 4 tick marks + count-up 0→score 1.2s + reco-pill), `RevenueSparkline` (SVG smooth Bezier + hover tooltip с реальным месяцем+value).
- Хук `lib/use-reduced-motion.ts` — отключает count-up/sweep при OS-prefer-reduced-motion.

*Sidebar (warm cream pattern):*
- `bg: #FAF9F5` (тёплый off-white).
- «+ Новая заявка» → **premium-card pattern**: белая карточка + brand-soft icon-tile (rotating plus 90° on hover, bouncy cubic-bezier) + dark label. **Не filled CTA**. Pattern: Linear/Notion/Mercury «Create new».
- Active nav-item: `inset 2px 0 0 var(--brand-primary)` + white bg. Visual tie между навигацией и CTA-цветом.
- User-card: gradient bg + online-dot (pulse-ring-ok keyframe) + «Кредитный аналитик · онлайн».

*Topbar:* trust-pill «● Все системы работают» (state-ok pulse-dot) слева от bell — bank-grade reliability cue.

*Search-view (полный rewrite):*
- h1 «Поиск компании» 34px (без маркетинга про «8 секунд»).
- LiveStrip pill: «● Сегодня · 247 · 84% · 12» (mock data, TODO[CA-DS-LIVE]).
- Search form 56px height, terracotta CTA.
- RecentChips — sparkline ТОЛЬКО на active chip (синхронизирован с `result.card.monthly_revenue_12m`). Inactive chips — просто моноширинный ИНН.
- ResultCard — оркестрирует ScoreRing + 4 mini-meta KPI + RevenueSparkline. Subtle radial brand-tinted gradient в углу. Sparkline tooltip отдаёт реальный месяц + млн сум.
- NotFound + Idle — обновлённый дизайн с radial gradient orb behind icon-tile.
- AmbientOrbs + GridPattern — page-level decoration (только на /search, не на других экранах).

*i18n* — ~20 новых ключей в `bank.search.*` (live_label, mini_*, recommendation_*, month_short_1..12, business_age_template с ICU-plural, spark_value_format) + `bank.topbar.systems_ok` + `bank.sidebar.online`. ru + uz.

**Verify status:** ruff + mypy --strict (233 source files) + 55 backend integration (3 skip PDF) + tsc + eslint + vitest 77 tests (61 existing + 16 новых format.test.ts) + next build (15 routes) — все зелёные.

**Files changed (16):**
- Backend: `search.py`, `search_schema.py`, `bank_search_test.py`
- Frontend foundation: `globals.css`, `bank-api.ts`, `lib/use-reduced-motion.ts`
- New components: `features/search/{ambient-orbs,grid-pattern,score-ring,revenue-sparkline,result-card,recent-chips,live-strip,format}.tsx` + `format.test.ts`
- Shell: `(bank)/_components/sidebar.tsx`, `(bank)/_components/topbar.tsx`, `(bank)/search/page.tsx`, `(bank)/search/_components/search-view.tsx`
- i18n: `i18n/ru.json`, `i18n/uz.json`

**Phase 2 hotfixes (после первого визуального теста):**

* **`610a86d` — ring tone + real live-strip data.** Score-ring color теперь из `recommendation` (approve→green / review→yellow / reject→red), не из display_score band. Это убрало визуальный конфликт «зелёное кольцо + 'На проверку' лейбл» при display_score=79 + recommendation=review. Также убраны tick marks (r=47-50 перекрывались с ring stroke r=42-50 → создавался «глюк» на скрине). Backend: новый `/api/bank/stats/today` endpoint + repo `get_bank_daily_stats(date)` + DTO `BankDailyStats` + 5 integration тестов. LiveStrip frontend переведён с mock-чисел на `useQuery(fetchBankDailyStats)` со staleTime 60s. **Удалён TODO[CA-DS-LIVE]** — реализовано.
* **`4e9fcf0` — BFF route + clean ring.** Добавлен `web/src/app/api/bank/stats/today/route.ts` — explicit Next-route handler (был забыт; без него catch-all proxy не передавал cookie→Authorization → backend 401 → live-strip показывал «—» постоянно). Также убран `drop-shadow` filter с score-ring stroke — создавал color halo вокруг кольца («сглажено» на скрине).
* **`f9d2ec5` — lazy-load AmbientOrbs + GridPattern.** Через `next/dynamic({ssr:false})`. Эти компоненты — pure decoration без бизнес-логики; убраны из initial JS bundle → быстрее route transitions в dev-mode (после моих изменений Turbopack долго recompiles все routes; production-build не страдает).
* **`4f6ebb1` — showcase-bar.** Bottom-center pill с 3 кнопками «Найдено / Не найдено / Пустой» — как в preview HTML. Каждый клик триггерит **реальный backend-flow** с предзаготовленным ИНН (`301234567` для found / `999999999` для not-found / clear для idle). Полноценные анимации — count-up + sparkline draw + result mount. При ручном вводе showcase сбрасывается. Решение пользователя — оставляем bar **всегда видимой**, не в production-гейте: это product feature (быстрое демо клиенту), не debug.
* **`022dfcf` — Next dev-indicator → bottom-left.** «Rendering…» badge в верхнем углу перекрывал hero — сдвинул в bottom-left. Production его не имеет, только dev.

**Решение принципиальное:** showcase-bar и live-strip остаются в production — это product features, не debug-panel.

### Phase 3 — History (scope) — DONE 2026-05-13

**Решение:** design statement (full overhaul). Phase 3 — premium data-grid, не hero. Цель — уменьшить визуальный шум таблицы и поднять иерархию data → analyst.

**Изменения:**

*Backend* — без изменений. Переиспользуем `GET /api/bank/stats/today` (Phase 2 hotfix `610a86d`).

*Frontend foundation:*
- Новый файл `web/src/features/history/relative-time.ts` — pure helper `formatRelativeTime(iso, now)` возвращает `{key, values}` для подстановки в `t()`. Поддержка ICU-plural (минуты/часы/дни в ru+uz). «Вчера» — календарный yesterday (не «24-48 часов»), для корректного отображения 02:00→23:00. `isFreshTime()` true для сегодня/вчера → подкрашивает relative зелёным. 11 unit-тестов с inject `now` для детерминизма.
- `LiveStrip` импортируется напрямую из `features/search/live-strip.tsx` (namespace `bank.search.live_*` переиспользуется). Если 3+ surfaces — extract в shared.

*HistoryView (полный rewrite):*
- **Page head:** убрана `+ Новая заявка` (дублировалась с premium-card sidebar CTA — pure visual noise). Осталась только `↓ Экспорт CSV`.
- **LiveStrip** между `BankPageHead` и `Tabs` — те же 3 метрики «● Сегодня · N проверок · M% одобрено · K в проверке».
- **Tabs** — оставлен pill-pattern; rounded-md → rounded-lg/rounded-md, ink-3 → ink-1 на hover.
- **Toolbar:** убран dead «Ещё» filter button (mock без onClick). Search 38px→40px, rounded-md→rounded-lg.
- **Table:**
  - **Header (`Th`)** — чистый white bg + 10.5px uppercase letter-spacing 0.08 + ink-4 text + inset bottom-shadow 1px + sticky top:0. Без тёмной плашки, без bg-surface-2 (был мутным с row-hover).
  - **ScoreCell** — vertical accent strip 3×22 (color = recommendation band, как ScoreRing /search) + crisp число mono 16px (color = score band). Tinkoff/Brex pattern. Без bar, без круга, без ticks.
  - **RecBadge** — оставлен с pulse-dot; rounded → rounded-full.
  - **DateCell** — две строки: абсолютная дата (13px, ink-2) + relative time (11px). Свежие ≤сегодня/вчера → relative подкрашен `state-ok-fg` semibold; старше → ink-4. ≥7 дней → relative не показываем.
  - **AnalystCell** — gradient на `linear-gradient(135deg, brand-primary-soft 0%, brand-primary 100%)`. CA-066 brand-aware (был hardcoded `#D88E73 → #B5624A`). На default-blue tenant получит синий avatar, на uzbekbank — терракотовый.
  - **Trailing chevron column** — `ChevronRight` opacity 0→1 + translate-x -4→0 на row hover. Affordance «click → open». Заменяет dead `⋯` actions cell.
  - **Row hover** — `var(--surface-2)` + group-hover для chevron.
- **EmptyBlock split:** `EmptyZero` (когда total=0 → "Пока никого не проверяли" + FileSearch icon) и `EmptyFiltered` (когда filtered=0 но total>0 → "Ничего не найдено" + Search icon). Оба — icon-tile 72px + radial brand-primary-soft orb + linear-gradient surface→brand-primary-soft bg.
- **Pagination split:** `Pagination` для totalPages > 1; `PaginationFooter` (just «Показано N из M») когда totalPages = 1 — убирает мёртвый «‹ 1 ›» control.

*i18n (ru+uz)* — `bank.history`: убраны `filter_more`, `row_actions`, `empty` (старый плоский); добавлены `empty_title/empty_desc` (filtered) + `empty_zero_title/empty_zero_desc` (нет вообще), `rel_just_now/rel_minutes/rel_hours/rel_yesterday/rel_days` (ICU-plural). `col_company` «Название компании» → «Компания» (короче для density). `subtitle` дополнен «Жми на строку, чтобы открыть полное досье.». `export` «Экспорт» → «Экспорт CSV».

**Verify status:** tsc + eslint (no-restricted-syntax clean) + 88 vitest tests (61 → 77 после Phase 2 → 88 теперь, +11 relative-time) + next build (16 routes) + ruff (Phase 3 не трогает backend) — все зелёные.

**Files changed (5):**
- `web/src/app/(bank)/history/_components/history-view.tsx` — полный rewrite
- `web/src/features/history/relative-time.ts` (new)
- `web/src/features/history/relative-time.test.ts` (new, 11 tests)
- `web/src/i18n/ru.json` — `bank.history` keyspace
- `web/src/i18n/uz.json` — `bank.history` keyspace

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
| 2026-05-13 | UI sweep | **ADR-0011 + design system (CA-060/061/062)** — `config/brands/<id>.json` (default + uzbekbank), semantic+brand tokens в globals.css, sweep `--ca-*` (234 hits) + `--ub-*` → semantic, удаление legacy. `useAppMode()` hook + lift mode-conditional из features в shells. ESLint `no-restricted-syntax` ban hardcoded hex/rgba в features+components. Chart-палитра 9 токенов. State-border tokens. | `fa986bf`..`6dae856`, `536b0a1` |
| 2026-05-13 | UI sweep | **Error boundaries + GlobalTopbar + ⌘K** — `app/error.tsx` + `(bank)/error.tsx` + `(accountant)/error.tsx` + `not-found.tsx`. `GlobalTopbar` (breadcrumbs + Cmd+K trigger + bell) wired в `AppShell` (`showTopbar={false}` для manual-input — там свой Topbar). `CommandPalette` skeleton с 5 пунктами навигации. | `3476aed`, `2e091a7`, `4bbda8a`, `a7ee62a` |
| 2026-05-13 | UI sweep | **KPI / manual-input polish** — mono+tabular-nums на YoY pill, semantic state-tokens в KPI cards. Pulse-dot для draft-save (`@keyframes pulse-dot` в globals.css). `formatBusinessAge` lib + 8 unit-тестов; wire через `formatBusinessAgeHint`. Убран fabricated «норма для отрасли ≤ 0.55» (D/A) без source. | `0cf5a48`, `b06babf`, `f8ee976`, `628a9f2` |
| 2026-05-13 | UI sweep | **Login sync с brand + TLS-signal (Phase 6)** — gold accent (`#D4B26A`) → `var(--brand-primary)` (terracotta для uzbekbank). Footer TLS-signal: зелёный dot + «Безопасное соединение · TLS 1.3 · AES-256-GCM». Spotlight / drift / vignette / grid pattern сохранены (рабочая Phase F-инвестиция). | `a3d1280` |
| 2026-05-13 | UI sweep | **Demo seed 3 UZ MSB (CA-065/Phase 7)** — `scripts/seed_demo_borrowers.py` с retail (Q4 пик) / agro (Q2-Q3 пик) / services (flat). TDD 4 теста, smoke `uv run python -m scripts.seed_demo_borrowers` → JSON в stdout. `--commit` raises NotImplementedError (TODO[CA-065]). | `e68d313` |
| 2026-05-13 | UI sweep | **Financial-table hex hygiene** — sed-replace `#FAFBFC/#F4F6F9/#F4F8FF/#FCE7E5` на `var(--surface-2)/--brand-primary-soft/--state-bad-bg`. ESLint правило не ловит Tailwind utility-классы — гигиена ручная. | `ee568c1` |
| 2026-05-13 | UI sweep | **i18n infra + 8 surfaces (CA-063)** — `next-intl` 4.4.1, `web/src/i18n/{ru,uz}.json` (4 sections: shared/bank/accountant/dossier, ~120 keys), Provider в RootLayout, `NEXT_PUBLIC_LOCALE` env. Swept: bank+accountant sidebars, bank search-view, history-view, login-view, GlobalTopbar, CommandPalette, DossierError, error/not-found pages. Manual-input components + dossier sub-views + `recommendationLabel` → TODO[CA-063b]. | `65264d0`, `a79007e`, `aa5c12f`, `d949dea`, `da683e9`, `283d82c`, `6ee96e3` |
| 2026-05-13 | UI sweep | **CI hotfix** — ruff RUF059 в seed-test (q5..q8 unused) → переписан unpacking. `package-lock.json` desync (`@swc/helpers 0.5.15` < peer-req `>=0.5.17`) → fresh `rm node_modules && npm install`. | `fd005a1` |
| 2026-05-13 | post-plan | **Design-parity sweep (CA-066)** — после смотра против локального target-state-preview закрыты 4 расхождения: (1) `BrandProvider` + `useBrand()` для client surfaces — bank `Sidebar` + `BankTopbar` тянут name/tagline/logoMark из `config/brands/<id>.json` (uzbekbank tagline → «Bank Mode · Андижон»). (2) Dossier layout: новый `SubHeader` (чистый title + meta-line ИНН/ОПФ/ОКВЭД + правые [Пересобрать] [Скачать PDF]), `ReadinessBadge` → `ReadinessKpiCard` как 4-я карточка `KpiRow` (revenue_ltm выкинут), нижний `ActionBar` удалён физически (`action-bar.tsx`). (3) Manual-input `info-banner` на `--state-info-{bg,fg}` + border через `color-mix` — теперь uzbekbank-tenant даёт терракотово-коричневую плашку вместо синей. (4) ⌘K палитра: keyboard nav (↑↓Enter), `↵` kbd на active item. Bug fix во время прохода: `t.rich(key, {x: () => <b/>})` с value-плейсхолдером `{x}` падал «Functions are not valid as a React child» в `bank/history` пагинации — переделан на tag-syntax `<b>{shown}</b>` + formatter `(chunks) => <b>{chunks}</b>`. Verify: tsc + eslint + 61 vitest зелёные. |
| 2026-05-13 | post-CA-066 | **CA-067 + CA-065** — rm orphaned `back-target.ts` (`56ada78`); `scripts/seed_demo_borrowers.py --commit` E2E писатель (`04665b1`): 3 demo bank-mode dossier'а через build_snapshot→rules→save. Dockerfile + COPY scripts/. Real smoke на real Postgres: 3 dossiers score=0/approve. **Запуск scripts:** `cd /app && PYTHONPATH=/app/src` (scripts/ это пакет в root, не в src/). |
| 2026-05-13 | Design Sweep | **Phase 1 Login DONE** — план фаз (`6c45af3`), subtle scale-up (`0a1c86c`: title 30/inputs 48/CTA 50, +4..9%), `-webkit-autofill` override (`4997d5b`), card final 355px (`8dc74cb` 395→380, `34d97f6` 380→355 — focused-positioning, Stripe/Linear territory). 5 cross-phase tech-debt issues (CA-DS1..CA-DS5) отложены. Готово к Phase 2 Search в новой сессии. |
| 2026-05-13 | Design Sweep | **Phase 2 Search DONE — design statement** — переход с subtle scale-up на full overhaul (premium private-bank эстетика). Backend: `/api/bank/borrowers/search` расширен `card: SearchCardData` (legal_form / recommendation / revenue_ltm / yoy_pct / business_age_months / signals_* / monthly_revenue_12m) — переиспользует `LoadDossierForView` use case. Frontend: warm-cream sidebar (#FAF9F5) + premium-card «+ Новая заявка» с rotating plus + active left-border + online-dot. Topbar trust-pill «● Все системы работают». Search-view: 34px h1, 56px form, recent chips с active-spark synced на result data. ResultCard: ScoreRing 112px + count-up 0→score (1.2s) + reco-pill (color из recommendation); 4 mini-meta KPI; RevenueSparkline 12 мес с hover tooltip отдающим реальный месяц+млн сум (smooth Bezier path, draw animation 1.6s). AmbientOrbs (mouse parallax ±14px + CSS drift 36/48s, lazy-load) + GridPattern (40×40 squares с radial mask, lazy-load). Хук `useReducedMotion` отключает animations при OS preference. i18n ~20 новых ключей ru+uz. **Initial**: `c9afbce` (16 файлов). **Hotfix series**: ring tone+real live-strip backend `610a86d` (+5 stats tests, /api/bank/stats/today + repo + DTO + LiveStrip useQuery), BFF route + clean ring `4e9fcf0` (drop-shadow halo убран, app/api/bank/stats/today/route.ts), lazy decoration `f9d2ec5` (dynamic AmbientOrbs/GridPattern), showcase-bar `4f6ebb1` (3 кнопки внизу триггерят реальный flow с preset ИНН — product feature, не debug), dev-indicator `022dfcf` (bottom-left). Verify final: ruff/mypy strict 234 src + 60 backend integration + tsc + eslint + 77 vitest + next build (16 routes incl. /api/bank/stats/today) — зелёные. |
| 2026-05-13 | UI sweep | **i18n sweep — финал (CA-063b)** — 5 коммитов закрыли все оставшиеся surfaces. (1) `recommendationLabel` удалён из `bank-api.ts`, callsites на `bank.history.rec_*`. (2) shared `components/topbar.tsx` (draft-state badges). (3) bank shell: `(bank)/_components/topbar` (TITLE_MAP→keys), `settings-view` (4 секции), `help-view` (FAQ через `t.rich` с тегами `b/code/good/warn/bad`). (4) dossier sub-views: sub-header / borrower-card / kpi-row / risk-signals (19 rule labels через `t.has`+fallback) / revenue-24m-chart / score-gauge / readiness-badge (тест обёрнут в Provider). (5) manual-input wizard (14 файлов: page-head/stepper/form-footer/info-banner + step-1..3 + financial-table/dscr-summary/parsed-files-dropzone/soliq-upload/checklist). `classifyDscrRisk` теперь возвращает `key`, не `label`. ICU-plural для files/fields counts, `t.rich` для FAQ. Brand-strings (Bank Mode, DSCR, UZS, ИНН, my3.soliq.uz, ops@uzbekbank.uz) не локализованы. | `757d0ba`..`d923051` |
| 2026-05-13 | Design Sweep | **Phase 3 History DONE — design statement.** Premium data-grid: убрана `+ Новая заявка` сверху (дубль sidebar CTA), оставлен `Экспорт CSV`. `LiveStrip` из Phase 2 переиспользован между PageHead и Tabs. Table headers: white bg + 10.5px uppercase letter-spacing 0.08 + ink-4 + inset bottom-shadow + sticky top:0 (был мутный surface-2). `ScoreCell` — vertical accent strip 3×22 (color = recommendation band) + crisp число mono 16px (color = score band, Tinkoff/Brex pattern). `DateCell` 2-line: абс. дата + relative time (свежие ≤сегодня/вчера → зелёный; ≥7д → скрыт). `AnalystCell` gradient на `brand-primary-soft → brand-primary` (был hardcoded #D88E73→#B5624A). Trailing chevron column opacity 0→1 на row hover (заменил dead `⋯`). EmptyState split: `EmptyZero` (total=0 «Пока никого не проверяли») vs `EmptyFiltered` (filtered=0). Pagination split: footer-only когда totalPages=1. Toolbar: убрана dead «Ещё». Новый `features/history/relative-time.ts` + 11 unit-тестов (ICU-plural ru+uz, календарный yesterday). i18n keyspace: +`rel_*`, +`empty_zero_*`, –`filter_more`, –`row_actions`. Verify: tsc + eslint + 88 vitest + next build (16 routes) — зелёные. | pending commit |

> Сжатая история. Полные decomposition / smoke numbers / per-step rationale — в commit messages (`git log --oneline`) и `docs/adr/`.
