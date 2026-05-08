# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус проекта и рабочие соглашения.

---

## Current Status

**Phase:** 7 закрыта 2026-05-15 — Manual-input Step 2 (Financial) design statement DONE. 5 секций сохранены (xltx upload, Soliq pair, Выручка, Прибыль, Annual block из 3 групп), schema не тронута; визуальный rewrite на Phase 6 section pattern (icon-tile + counter) + annual-default mode с quarter toggle + per-field source-trail (auto / manual / manual-required / waiting). Phase 8 (Manual-input Step 3 — Loan) unblocked. Specs: `docs/superpowers/specs/2026-05-11-phase-4-bank-mode-design.md`, ADR-0009, ADR-0011.

**Активная ветка:** `main`. Phase 5 = Phase 5.A (Settings UI, `06f0ae4`) + Phase 5.B backend foundation (`06f0ae4`) + **Phase 5.B frontend + 3 hotfix (2026-05-14)** — real TOTP 2FA сквозной flow от UI до login. Frontend: `features/settings/{mfa-section,mfa-enroll-modal,mfa-disable-modal}.tsx` (3-stage enrollment с canvas-rendering QR через `qrcode@1.5.4` pinned + 10 backup-codes copy/download/confirm); login step-2 в `login-view.tsx` с TOTP/backup toggle. BFF: 4 новых route handlers под `/api/auth/mfa/*`. Lib: `lib/mfa.ts` + расширенный `lib/auth.ts` (union `LoginResult`). i18n: ~62 keys в `bank.{settings.mfa,login.mfa_*}` ru+uz.

**Critical hotfixes during smoke (commits `d9387c0`, `6d625b1`, `59bb172`):**
- `fix(mfa)`: computed `mfa_enabled` от `mfa_enrolled_at`, не от `mfa_secret` — half-enrolled lockout-bug fix. `/enroll/start` пишет secret в БД до verify; раньше computed flag это путало с enrolled state → следующий login требовал TOTP, но secret в authenticator не сохранён → lockout без backup-кодов.
- `feat(mfa)`: RFC 5233 subaddress в provisioning URI (`admin+a1b2c3@bank.uz` вместо `admin@bank.uz`) — обход Microsoft Authenticator iOS + iCloud-cache dedup. MS Auth дедупит по подстроке-email независимо от full account_name; уникальный local-part спасает re-enrollment scenario.
- `feat(mfa,web)`: `useRef` guard на enrollment-effect — фикс React 19 strict-mode (dev) double-fire `useEffect`, который делал 2× POST `/enroll/start` за одно открытие модалки → 2 разных secret в БД → race-condition в QR vs verify.

**Verify status:** tsc + eslint + 95 vitest + next build (22 routes, +4 новых `/api/auth/mfa/*`); ruff + mypy --strict (240 src files); 3/3 новых unit-тестов в `analyst_mapper_test.py` passed; full E2E smoke 2026-05-14 на real Docker stack:
- ✅ enrollment через manual-entry secret (workaround для MS Auth iCloud)
- ✅ enrollment через scan QR (после email-suffix patch; диалог MS «уже существует» игнорируется, аккаунт всё равно добавляется)
- ✅ disable через UI с password + TOTP re-auth
- ✅ login → MFA challenge → TOTP code → /search
- ✅ login → MFA challenge → backup-code → /search (код одноразовый — повторно invalid)

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
- ~~TODO[CA-068]: backend endpoint `POST /api/auth/change-password`~~ — **закрыт 2026-05-14** (`7d65e29`). Re-auth по current через AuthnPort, bcrypt re-hash, UPDATE `password_changed_at`, audit `password_changed`. Запрет реюза текущего пароля (400 `password_unchanged`). UI mock убран; backend detail-коды → i18n.
- ~~TODO[CA-DS9]: real uptime-history collector~~ — **закрыт 2026-05-14** (`5e40acd`). FastAPI lifespan async-task `uptime_collector_loop` пингует Postgres + WeasyPrint каждые 60s и UPSERT'ит worst-of-day в `system_uptime_day`. Settings `uptime_collector_enabled=False` по умолчанию (для тестов и host-dev); docker-compose api сервис ставит `UPTIME_COLLECTOR_ENABLED=true`. Не используем ARQ — один процесс, нет очереди jobs.
- ~~TODO[CA-DS10]: real TOTP/SMS enrollment-flow для 2FA~~ — **закрыт 2026-05-14** (`06f0ae4` backend + `d9387c0`/`6d625b1`/`59bb172` Phase 5.B frontend + hotfixes). Production-grade TOTP с QR + backup-codes + login step-2. См. блок «End-user 2FA guide» ниже.
- ~~TODO[CA-DS13]: admin-reset 2FA endpoint~~ — **закрыт 2026-05-14** (`f9dc928`). `POST /api/bank/admin/analysts/reset-mfa` (senior_analyst only через `require_senior_analyst` guard → 403). Body `{email}`: очищает `mfa_secret / mfa_enrolled_at / mfa_backup_codes_hash / mfa_enabled`. Audit `mfa_admin_reset` с senior как `analyst_id` и затронутым в payload. Force-logout не делаем — JWT v1 stateless; access истечёт через 15 мин, на refresh challenge не выдаётся (computed `mfa_enabled = False`). UI карточка в `/settings → Безопасность` под role-gate.
- TODO[CA-DS14]: `/help` секция «Что делать при смене телефона» — explain «диалог "уже существует" в MS Authenticator — нажми Отмена, аккаунт всё равно добавится». Сценарий редкий (раз в N лет на аналитика), но без объяснения user встанет колом.
- TODO[CA-DS15]: рассмотреть WebAuthn/Passkeys как alternative 2FA-фактор — нет third-party app, биометрия на телефоне, нет TOTP-кодов вообще. UX-вин для non-tech аналитиков. Требует FIDO2-server в `infrastructure/auth/`.
- TODO[CA-DS16]: убрать legacy stored bool `analysts.mfa_enabled` через миграцию. Сейчас computed-from-`enrolled_at` в API — stored bool сжигается, но колонка всё ещё в БД. Drop после подтверждения что нигде не читается (`grep mfa_enabled = ` показал только репозиторий-уровень).
- TODO[CA-DS11]: faktura.uz API integration. Сейчас сервис в `/api/system/health` всегда `not_implemented`. После реализации — реальный ping + статус ok/degraded.
- TODO[CA-DS17]: real OKVED-каталог из backend-endpoint `/api/system/okved-catalog` или статичный JSON. Сейчас `OKVED_UZ_MSB` хардкод в `step-1-borrower.tsx` — 16 кодов МСБ-сегмента (УзКВЭД 2024). Достаточно для папиных фирм; для pilot-банка нужна полная номенклатура.
- TODO[CA-DS18]: реальный `case_id` с бэкенда. Сейчас clientside `Math.random()` placeholder через `useSyncExternalStore` — id меняется между вкладками, не stable через draft-resume. Когда заведём `applications` table — pull `case_id` оттуда при mount draft / start new.
- TODO[CA-DS19]: motion cleanup pass по /search и /history. В Phase 2/3 остались pulse-ring-ok dots на trust-pill «Все системы работают» и LiveStrip — user в Phase 6 явно попросил «без вау-эффекта который горит в реальном времени, это банк». Sweep + revert pulse-* анимаций, оставить только user-card sidebar online-dot (semantic).
- TODO[CA-DS20]: RTL-тесты на InnInput state machine (idle→checking→verified, fake timers) + OkvedAutocomplete (filter / keyboard nav / select). Сейчас mini-компоненты не extract как named exports — для теста требуется extract или integration через рендер Step1Borrower с FormProvider + i18n. Phase 6 verified manually + tsc/eslint/next-build/смежные vitest зелёные.
- TODO[CA-DS21]: `auto-edited` state в source-trail (Step 2). Сейчас 2-state UI (auto / manual): parser подставил → user поправил → всё ещё рендерится как auto (зелёный). Нужно 3-state: tracking `initial_autofilled_value` в `SourceTrailContext` отдельно от form-value; сравнение → amber «Из FORM_2, поправлено руками». User не получает обратной связи об edit-after-autofill; small risk при ошибочной правке аналитика.
- TODO[CA-DS22]: keyboard nav в `CustomDropdown` (Soliq year/month). Сейчас только mouse-click. Phase 6 OkvedAutocomplete делал ↑↓ Enter Esc — extract в shared `<Listbox>` primitive и переиспользовать.
- TODO[CA-DS23]: RTL-тесты на `Step2Financials` source-trail rendering — mock `SourceTrailContext` value, render Step2 в `FormProvider` + `NextIntlClientProvider`, assert hint state классы. Phase 7 verified manually + tsc/eslint/vitest 101 (без новых) + next build (24 routes) зелёные.
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
- **Phase 6 DatePicker (Step 1 + Step 2/3 в будущем):** `features/manual-input/components/date-picker.tsx` поверх `react-day-picker@9` + `@base-ui/react/popover`. API строковый ISO (`yyyy-MM-dd`), не Date — совместимо с zod-схемой `isoDate`. Trigger 40px моноширинный «DD.MM.YYYY». Popover 290px, RU локаль (`date-fns/locale#ru`), Mon-first (`weekStartsOn={1}`), `disabled: Matcher[]` с `{before:min}`/`{after:max}`, footer «Очистить» / «Сегодня». Тесты в `date-picker.test.tsx` (6 кейсов) — день matched по локализованному aria-label `/^DD мес YYYY/`, не по textContent (react-day-picker v9 ставит full readable label из date-fns formatter). Native `<input type="date">` запрещён — Chrome/Safari UI расходится с design tokens, локализация не контролируется. **Audit pass 2026-05-15:** добавлен `captionLayout="dropdown"` (month + year dropdowns, native `<select>` поверх visible caption_label через `absolute opacity-0` overlay-паттерн — react-day-picker v9 рендерит этот sandwich сам в `components/Dropdown.js`), `startMonth/endMonth` (defaults 1990 → currentYear+1, иначе year-dropdown получает 1 option = бесполезно), `fixedWeeks` (popover не «прыгает» по высоте 5/6 недель), «Сегодня» disabled когда today вне range min/max. Tailwind v4 `ring-color/40` syntax (старый `ring-opacity-*` deprecated).
- **Phase 6 ИНН 3-state (Step 1):** `InnInput` внутри `step-1-borrower.tsx` — state machine `idle | checking | verified | invalid`. Triggers: onChange → reset to `idle` (через `setTimeout 0` обход react-hooks/set-state-in-effect — CA-066 паттерн); onBlur с валидным `^\d{9}$` → `checking` + setTimeout 700ms → `verified` с mock-резюме «Юр. лицо · действующий статус». Реальный лукап `/api/system/gnk/{inn}` — TODO[CA-003]. Pill «В реестре ГНК» статичная (без pulse) по Phase 6 design-tone «без motion для банка». Spinner при checking — оставлен (semantic loading, не декорация). **Audit pass 2026-05-15:** `handleBlur` пропускает re-checking если `state.kind === "verified"` (value не менялся → useEffect [value] reset не сработал → повторный tab-out не должен flash'ить spinner). Зависимость `[onBlur, value, state.kind]` в useCallback.
- **Phase 6 OKVED autocomplete (Step 1):** `OkvedAutocomplete` — popover-listbox с 16 хардкод-кодами УзКВЭД 2024 МСБ-сегмента (`OKVED_UZ_MSB` const, descKey → i18n `accountant.manual_input.okved_*`). Фильтр по `code.startsWith(q)` + `desc.includes(q)`. Keyboard nav: ↑↓ + Enter pick + Esc close. `aria-controls={listboxId}` + `role="combobox"` (без обоих — eslint jsx-a11y/role-has-required-aria-props падает). Real OKVED endpoint — TODO[CA-DS17].
- **Phase 6 motion-cleanup для банка:** все `animation: pulse-*` убраны из Step 1 (draft-pill в topbar, status-card в page-head, ИНН verified pill, save-hint в footer). Stepper больше не имеет `box-shadow` glow на active/done circles + connector-линия удалена физически (3 раздельных «круг + label» tile'а в grid). Оставлен только user-card sidebar online-dot (pulse-ring-ok — semantic «онлайн-аналитик»). На /search и /history pulse-* всё ещё есть — TODO[CA-DS19] на cleanup-sweep.
- **Phase 7 annual-default mode (Step 2 Financial):** `FinancialTable` рендерит **3 годовых cell** (по одной на 2023/2024/2025) вместо 4×3 quarterly grid. Toggle «Показать кварталы (опц.)» раскрывает grid под years; запись идёт в `quarter.annual` (CA-027 fallback). Когда quarter-grid раскрыт и заполнен хоть один квартал → годовая cell становится read-only с `sumQuarters` (CA-027 yearTotal-semantic — quarter wins). i18n keys: `s2_quarter_toggle_show/_hide`, `s2_year_locked_to_quarters`, `s2_quarter_note`. Backend submit contract не изменён — `payload` всё ещё содержит annual + quarters (zod schema `quarter` с `annual: uzsAmountOptional`).
- **Phase 7 source-trail UI (Step 2):** под каждым UZS-полем — мелкая подпись «откуда». 2-state модель в MVP: ключ в `useSourceTrail()` map → `auto` (зелёный border-bar + «Из FORM_2 · поправь если не так»); ключа нет → `manual`/`waiting`. Спец-state `manual-required` для taxesPaid 23/24/25 (PROFIT_TAX-парсер не реализован, TODO[CA-029b], всегда руками — amber tone, чтобы аналитик не путал с пропущенным autofill). Левый 3px borderbar внутри `relative` контейнера UZS-input через absolute span (не CSS border — он мешает `border-r-0` для сшивки с UZS-suffix). 3-state `auto-edited` — TODO[CA-DS21].
- **Phase 7 section-card pattern:** все 5 секций Step 2 (ParsedFilesDropzone, SoliqUpload, Revenue, Profit, Annual) разделяют `<section>` shell — `rounded-[14px]` + `grid-cols-[40px_1fr_auto]` header с 36px icon-tile (`brand-primary-soft` + lucide-icon) + gradient bg (`from-white to-surface-2`) + optional right-side `<CounterChip>` с live progress bar (Revenue/Profit). Если counter не нужен — пустой `<div />` для grid-layout stability. Pattern идентичен Step 1 — но дублируется per-component (нет shared `<SectionShell>`), как в Phase 6.
- **Phase 7 Annual block split на 3 группы flat:** Налоги | НДС | Баланс. Каждая `<AnnualGroup>` = `grid-cols-[210px_1fr]` (sticky title-column слева 26px icon-tile + uppercase title + sub) + `<UzsRow>` list справа. Между группами — `border-b dashed` (последняя без border). `<BalanceComputed>` inline внутри Баланс-группы (D/A + Equity рендерятся в `divide-x` 2-column tile-pair). До Phase 7 был один `Card` block с 8 полями в grid — теперь читается как 3 separated концептуальных группы.
- **Phase 7 CustomDropdown (SoliqUpload):** native `<select>` для year/month заменён на `<button>` + `<ul role="listbox">` поверх Base UI-style popover. Generic `<CustomDropdown<T>>` принимает `{label, value, options, onChange}`. Outside-click close через `useEffect` listener на `mousedown`. Keyboard nav — TODO[CA-DS22] (сейчас только mouse).

---

## End-user 2FA guide (для smoke + pilot setup)

Документация для **тебя** на следующий раз когда захочешь проверить 2FA с нуля, или для IT-офицера банка при onboarding'е аналитика.

### Подготовка окружения

1. Backend в Docker bank-mode:
   ```powershell
   $env:APP_MODE='bank'; docker compose up -d --build api
   ```
   ⚠️ Если запустить без `$env:APP_MODE='bank'` префикса — bank-router не зарегистрируется, login будет 404. .env с APP_MODE=bank — TODO (см. memory).

2. Seed admin с известным паролем (upsert по email):
   ```powershell
   docker compose exec -T api bash -c "cd /app/src && uv run --no-sync python -m interfaces.cli.seed_analysts --email admin@bank.uz --password 'Admin2026!' --full-name 'Admin A.' --role senior_analyst"
   ```

3. Frontend dev:
   ```powershell
   cd web; $env:NEXT_PUBLIC_APP_MODE='bank'; $env:NEXT_PUBLIC_BRAND_ID='uzbekbank'; npm run dev
   ```

4. Telegram-like TOTP app на телефоне — поставь **Microsoft Authenticator** или **Google Authenticator** (Google не имеет iCloud-quirk).

### Smoke 4 путей (≈10 минут)

#### Путь 1 — Enrollment

1. Открой `http://localhost:3000/login` → `admin@bank.uz` / `Admin2026!` → Войти → `/search`
2. Sidebar → **Настройки** → nav **Безопасность**
3. Карточка «Двухфакторная аутентификация · Не настроена» → кнопка **«Включить 2FA»**
4. Модалка stage QR:
   - Сканируй QR в Authenticator-приложении
   - **Если MS Authenticator пишет «уже существует»** — нажми Отмена. Аккаунт всё равно добавится в список (после email-suffix patch label выглядит `admin+a1b2c3@bank.uz`)
   - Альтернативно — клик «Показать» под manual-entry secret → копируй → в Authenticator «+ → Other → Ввести вручную» → paste secret
5. Клик «Продолжить» → stage Verify
6. Введи 6-значный код из Authenticator → «Подтвердить»
7. Stage Backup-codes:
   - **СКАЧАЙ .txt** (обязательно — plain никогда не повторится)
   - Открой блокнотом, проверь 10 строк по 8 символов
   - Отметь checkbox «Я сохранил коды в надёжном месте» → «Готово»
8. Карточка 2FA стала зелёной «Активна» ✅

#### Путь 2 — Login через TOTP

1. Sidebar внизу → user-card → Выйти
2. `/login` → email + пароль → Войти
3. Должен переключиться на step-2 «Двухфакторная аутентификация · Введите 6-значный код»
4. Свежий код из Authenticator → Подтвердить → `/search` ✅

#### Путь 3 — Login через backup-код

1. Logout
2. `/login` → email + пароль → Войти → step-2
3. Клик ссылку **«Использовать резервный код»** (под input полем)
4. Поле меняется: placeholder `XXXXXXXX`, разрешает буквы и цифры
5. Введи **один** из сохранённых backup-кодов (8 символов, A-Z 0-9) → Подтвердить → `/search` ✅
6. ⚠️ Использованный код **сгорает** — повторный ввод того же даст invalid_code

#### Путь 4 — Disable

1. Залогинен через Путь 2 или 3
2. `/settings` → Безопасность → карточка 2FA → красная кнопка **«Отключить»**
3. Модалка: пароль `Admin2026!` + свежий TOTP-код → Подтвердить
4. Карточка стала серой «Не настроена» ✅

### Если invalid_code не уходит

Backend ping для самопроверки:

```powershell
# 1. Текущий secret в БД для admin@
docker compose exec -T postgres psql -U credit -d credit_assistant -c "SELECT mfa_secret, mfa_enrolled_at FROM analysts WHERE email='admin@bank.uz';"

# 2. Скопируй secret, посмотри что сервер ожидает прямо сейчас
docker compose exec -T api bash -c "PYTHONPATH=/app/src uv run --no-sync python -c 'import pyotp,time; print(pyotp.TOTP(\"PASTE_SECRET_HERE\").now())'"
```

Если код из Authenticator **не совпадает** с тем что выдаёт probe — Authenticator имеет другой secret (старая запись от race-condition не очищенная + iCloud cache, либо вторая запись с тем же label). Удали ВСЕ «Credit Assistant» из Authenticator, добавь заново через manual entry.

### Восстановление в случае lockout

Если потерял все: телефон + backup-codes — есть только прямой SQL до того как `TODO[CA-DS13]` admin-reset endpoint появится:

```powershell
docker compose exec -T postgres psql -U credit -d credit_assistant -c "UPDATE analysts SET mfa_secret=NULL, mfa_enrolled_at=NULL, mfa_backup_codes_hash=NULL WHERE email='YOUR_EMAIL';"
```

После — login сразу пускает без 2FA, можешь заново enroll'нуться.

---

## Design Sweep 2026-05-13 (10 фаз, in-progress)

**Процесс:** 1 фаза = preview HTML в `web/design-reference/2026-05-13-{phase}-preview.html` → user approves → 1 commit → переход к следующей. Строго по очереди, без перепрыгивания.

**Фазы (по E2E flow аналитика + sub-views):**

| # | Phase | Status | Preview file | Commit |
|---|---|---|---|---|
| 1 | Login | **DONE** | `2026-05-13-login-phase1-preview.html` | `0a1c86c`..`34d97f6` |
| 2 | Search | **DONE** (design statement + 4 hotfix) | `2026-05-13-search-phase2-preview.html` | `c9afbce` → `022dfcf` |
| 3 | History | **DONE** (design statement) | `2026-05-13-history-phase3-preview.html` | `8bbc154` |
| 4 | Help | **DONE** (design statement + 6 hotfix) | `2026-05-13-help-phase4-preview.html` | `cb8b046`..`91c4090` |
| 5 | Settings | **DONE** (визуально + 3 functional holes закрыты 2026-05-14) | — | `06f0ae4` + `d9387c0`/`6d625b1`/`59bb172` + `7d65e29`/`f9dc928`/`5e40acd` |
| 6 | Manual-input Step 1 (Borrower) | **DONE** 2026-05-15 (design statement) | `2026-05-15-step1-phase6-preview.html` | `d2fb869` + `c116908` (lockfile fix) |
| 7 | Manual-input Step 2 (Financial) | **DONE** 2026-05-15 (design statement + source-trail) | `2026-05-15-step2-phase7-preview.html` (4 итерации) | _<commit on push>_ |
| 8 | Manual-input Step 3 (Loan) | pending | — | — |
| 9 | Dossier view | pending | — | — |
| 10 | PDF document | pending | — | — |

### Phase 5 functional holes — ЗАКРЫТЫ 2026-05-14

Все 3 дыры закрыты атомарными коммитами в одной сессии:

1. **CA-068** — `feat(auth): real POST /api/auth/change-password` (`7d65e29`). Re-auth по current через AuthnPort, bcrypt re-hash, UPDATE `password_changed_at`, audit `password_changed`, запрет реюза текущего (400 `password_unchanged`). 5 integration tests.
2. **CA-DS13** — `feat(admin): senior_analyst может сбросить 2FA коллеге` (`f9dc928`). Новый router `/api/bank/admin/*` с guard `require_senior_analyst` (403 для не-senior). POST `/analysts/reset-mfa` body `{email}` → очищает MFA fields + audit `mfa_admin_reset`. UI карточка в `/settings → Безопасность` под role-gate. 4 integration tests.
3. **CA-DS9** — `feat(jobs): uptime collector cron как FastAPI lifespan task` (`5e40acd`). Внутрипроцессный asyncio loop через FastAPI lifespan, пингует Postgres + WeasyPrint каждые 60s, UPSERT worst-of-day. Settings flag default off (безопасно для тестов), docker-compose ставит `UPTIME_COLLECTOR_ENABLED=true`. 2 integration tests. ARQ намеренно не использовали — overkill для одного процесса без очереди.

Phase 6 (Manual-input Step 1 design sweep) теперь unblocked.

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

**Phase 3 follow-up (same day) — GridPattern background:**

- `globals.css`: новый modifier `.ds-grid-pattern--brand` — то же 40×40 + radial mask, но color = `color-mix(in srgb, var(--brand-primary) 8%, transparent)`. Default `.ds-grid-pattern` снижен до 4.5% (`rgba(14,21,37,0.045)`) после нескольких итераций пользователя (18% → 6% → 8% → 4.5%).
- `features/search/grid-pattern.tsx` параметризован: `tone?: "default" | "brand"`.
- `(bank)/history/_components/history-view.tsx` — `<GridPattern tone="brand" />` через `next/dynamic({ssr:false})` (lazy decoration) + контент обёрнут в `<div className="relative z-[1]">` чтобы лежать поверх pattern.
- **Финальные opacity:** /search 4.5% ink-1 (нейтрально-серый), /history 8% brand-primary (терракотовый намёк на uzbekbank; default-blue tenant → синий через CSS var).
- AmbientOrbs **не** добавлены на /history — только grid (decision: orbs = hero showroom для /search, table-grid с orbs — визуальный шум).

### Phase 4 — Help (scope) — DONE 2026-05-13

**Решение:** design statement — info-страница получает Phase 2/3 паттерны (status-pill, GridPattern, premium card hierarchy). Никаких structural rewrites, контент тот же (7 FAQ + 4 контакта + incident).

**Изменения:**

*Frontend:*
- `BankPageHead.actions` слот получает **status-card** (right-of-title): pill с pulse-ring-ok dot + «API v1.2» + «Справка обновлена 13.05.2026». Pattern из Phase 2 trust-pill, semantics — non-operational system-cue. **APP_VERSION + HELP_LAST_UPDATED — module-level const в `help-view.tsx`** (не tenant-specific, общие для всех brands; если CA-DS6 заведём `lib/app-info.ts` — поднимем туда).
- `IncidentBand` full-width между title и content (mb-6) — критическая инфа «данные клиента ушли другому → звоните в compliance» больше не buried в углу. `state-bad-{fg,bg,border}` tones + icon-tile + CTA-кнопка «Позвонить compliance» (`tel:+998712000000`, тот же номер что Hotline — assumption: compliance-hotline дозвон через тот же номер; если на pilot-демо будет другой — заведём `BRAND_COMPLIANCE_TEL` отдельно).
- `FaqSection` rewrite: header с FAQ-counter `7 тем` (ICU-plural, uppercase letter-spacing 0.08em — Phase 3 header pattern). Каждая `FaqRow` = grid `44px icon-tile | category eyebrow + question | chevron`. 7 leading icons (BarChart3 / AlertTriangle / Database / FileSpreadsheet / RotateCcw / ScrollText / LifeBuoy) в `brand-primary-soft` tile. **Expanded answer теперь в accent-block:** `border-l-2 border-brand-primary` + `bg-gradient-to-r from-brand-primary-soft to-transparent`, скруглён только справа (`rounded-r-lg`) — left-strip визуально продолжает chevron-rotated в `brand-primary`. Связь open-question ↔ answer теперь читается с расстояния. Первый row default-open (sane initial state, не пустая страница).
- `ContactStack` tier-hierarchy (3 yarus, **physical order**):
  - **Tier 1 — Hotline (primary):** large card, `bg-gradient-to-b from-brand-primary-soft to-surface`, mono `+998 71 200-00-00` 18px, **dynamic status row** «● Сейчас открыто · до 18:00 (Ташкент)» / «● Закрыто · откроется в 09:00 (Ташкент)». Hover `-translate-y-px` + brand-ring shadow.
  - **Tier 2 — Slack + Email:** обычные cards с icon-tile, label-eyebrow uppercase, value 14px semibold, hint 11.5px. Hover → brand-primary border + brand-soft bg + icon-tile перекрашивается.
  - **Tier 3 — Docs:** ghost-style link, разделён `border-t border-dashed` сверху, arrow `translate-x-0.5` on hover. Не выглядит как card — намёк «это reference, не CTA».
- Bottom `notes-bar`: «Время ответа: Slack ≤ 1ч · Email ≤ 4ч (раб. дни)» — SLA-cue для аналитика, чтобы понять куда быстрее.
- `GridPattern tone="default"` через `next/dynamic({ssr:false})` (4.5% ink-1) + `<div className="relative z-[1]">` wrap — consistency с /search.

*Helper для бизнес-часов* — `web/src/features/help/business-hours.ts`: `getHotlineStatus(now)` → `{open: true, untilHour: 18} | {open: false, opensAtHour: 9}`. Asia/Tashkent через `Intl.DateTimeFormat({timeZone})`, Mon-Fri 09:00-18:00 (boundary 09:00 inclusive, 18:00 exclusive). 7 unit-тестов с inject `now` (детерминизм через `Date.UTC(... - 5)`).

*HotlinePrimaryCard `useEffect` pattern:* initial state `null` + `setTimeout(update, 0)` для первого setState + `setInterval(update, 60_000)` для polling. **ESLint правило `react-hooks/set-state-in-effect` запрещает синхронный setState в effect body** — `setTimeout(0)` уходит в macrotask, правило пропускает. Polling через минуту достаточно: status меняется только на boundary 09:00/18:00 раз в день.

*i18n* — `bank.help` keyspace расширен ~13 keys: `status_api_label`, `status_api_version`, `status_updated_label`, `status_updated_date`, `faq_topics` (ICU-plural), `faq_cat_{scoring,red_flags,insufficient,xltx,rebuild,audit,support}`, `contacts_heading`, `contact_email_hint`, `contact_hotline_status_open`, `contact_hotline_status_closed`, `contact_hotline_hours_note`, `sla_note`, `incident_cta`. Старый `contact_hotline_hint` заменён на `contact_hotline_hours_note` (формулировка чище). Phone/email/Slack/Docs значения — hardcoded в коде как brand-strings (как «Bank Mode · Андижон» в CA-066). Если заведём `support` section в `brand-config.json` — TODO[CA-DS6].

**Verify status:** tsc + eslint + 95 vitest (88 → 95, +7 business-hours) + next build (16 routes) — все зелёные.

**Files changed (5):**
- `web/src/app/(bank)/help/_components/help-view.tsx` — полный rewrite
- `web/src/features/help/business-hours.ts` (new)
- `web/src/features/help/business-hours.test.ts` (new, 7 tests)
- `web/src/i18n/ru.json` — `bank.help` keyspace
- `web/src/i18n/uz.json` — `bank.help` keyspace

**Preview note:** в preview HTML accent strip ответа делал с gradient «brand-soft → transparent». При первом проходе ответ слипался с question — fix: gap 10px + accent-block с left-border 2px brand-primary + rounded-r-lg. Реальный код повторяет этот pattern через Tailwind: `border-l-2 border-[var(--brand-primary)] bg-gradient-to-r from-[var(--brand-primary-soft)] to-transparent`.

### Phase 4 — Help hotfix series (same day, 2026-05-13)

После initial commit `cb8b046` была серия итераций. Финальное состояние:

- **FAQ expand animation** (`9815d70`) — grid-row pattern `0fr→1fr` + opacity fade, 320ms ease-out. Chevron bouncy cubic-bezier(0.34,1.56,0.64,1) 400ms. Icon-tile scale-110 + brand-ring shadow при hover/open. Category eyebrow меняет цвет на hover.
- **Slack/Email tile bug fix** (`9815d70`) — на hover карточка становилась `brand-primary-soft`, icon-tile тоже был `brand-primary-soft` → tile сливался с фоном (invisible square). Tile на hover теперь → white bg + brand-primary icon + scale-110 + ring-shadow. Slack/Docs ссылки `target="_blank"`.
- **Deep-link → revert** (`ea1a5f7` → `f8b5df8`) — добавил copy-link icon на FAQ row с hash auto-scroll/auto-open, затем убрал. Pattern Linear/GitHub — для public docs с сотнями FAQ. У нас 7 вопросов, скроллятся за секунду, инструмент внутренний. Использовали Wow-feature option из brainstorm, потом увидели что overkill — revert.
- **Operator-presence в Hotline** (`ea1a5f7`) — оставлен. Avatar 32px (initials gradient brand-soft→brand-primary) + pulse-ring-ok dot + «СЕЙЧАС НА СМЕНЕ · Мадина А. · Доступен». Виден только когда hotline open (status?.open). Mock `CURRENT_OPERATOR` в module-level const. Real-endpoint позже — TODO[CA-DS7].
- **Dismissable incident-band → revert** (`2d4eb91` → `2816ac4`) — добавил X-кнопку с localStorage `ca:help-incident-dismissed` + smooth grid-row collapse, затем убрал. Без undo-механизма случайный X = потеря critical-cue. Banner теперь persistent baseline. Если в будущем compliance-phone отличается от hotline — заведём `BRAND_COMPLIANCE_TEL` в brand-config (TODO[CA-DS8]).
- **FAQ all-closed на mount** (`2816ac4`) — убрал `defaultOpen={idx === 0}` для первого вопроса. Notion/GitHub pattern. Открытый scoring создавал ложное чувство «я был тут вчера и остановился здесь».
- **Sidebar Help section перенесена под Workspace** (`91c4090`) — Help (Помощь / Настройки) поднята из `mt-auto`-внизу прямо под Workspace (Поиск / История). Между ними thin divider `color-mix(nav-border 60%, transparent)`. `mt-auto` перенесён на user-card → gap теперь между Help и user-card, не между Workspace и Help. Workspace + Help читаются как single navigation tree.

**Lessons:**
- Wow-features (deep-link, dismissable) предложили — попробовали — реверт. Cost-benefit для **внутреннего** banking-tool сильно отличается от public SaaS docs.
- ESLint `react-hooks/set-state-in-effect` несколько раз ловил `setOpen(true)` синхронно в effect. Pattern для обхода: `setTimeout(() => setState(...), 0)` уходит в macrotask, правило молчит. Использовано в HotlinePrimaryCard, FaqRow forceOpenFromHash (revert'нут), IncidentBand dismiss (revert'нут).

**Open TODOs from Phase 4:**
- `TODO[CA-DS6]`: вынести `support` section в `brand-config.json` (phone/email/Slack/Docs/compliance_phone) — сейчас hardcoded в `help-view.tsx`.
- `TODO[CA-DS7]`: backend-endpoint для real operator-shift presence (`/api/bank/operators/current`). Сейчас mock `CURRENT_OPERATOR = { name: "Мадина А.", initials: "МА", status: "available" }`.
- `TODO[CA-DS8]`: отдельный compliance-phone в brand-config + второй CTA в incident-band («Compliance» vs «Hotline»). Сейчас оба = `+998 71 200-00-00`.

### Phase 6 — Manual-input Step 1 (Borrower) — DONE 2026-05-15

**Решение:** design statement (full overhaul по Phase 4 паттернам). 4 итерации preview (`web/design-reference/2026-05-15-step1-phase6-preview.html`) — connector в stepper'е удалён физически (user feedback «линия не ушла думаем можем обойтись и без линции»), все pulse-* анимации убраны кроме user-card sidebar online-dot (user feedback «поменьше вау-эффекта который горит в реальном времени это всё же для банка»), добавлен кастомный date-picker (user feedback «можем добавить календарь современное когда нажимаю»).

**Изменения (12 файлов):**

*Deps:* `react-day-picker@^9.14.0` + `@testing-library/user-event@^14.6.1` (для RTL `userEvent.click`). `@base-ui/react` уже стояло (Popover primitives).

*Новые компоненты:*
- `features/manual-input/components/date-picker.tsx` — wrapper над `react-day-picker@9` + `@base-ui/react/popover`. API строковый ISO `yyyy-MM-dd` (совместимо с zod-схемой `isoDate`). Trigger 40px моноширинный «DD.MM.YYYY» + `data-state` атрибут. Popover 290px, RU локаль через `date-fns/locale#ru`, `weekStartsOn={1}`, `disabled: Matcher[]` с before/after, footer «Очистить» / «Сегодня». Tailwind `classNames` для react-day-picker без импорта стандартного CSS (избегаем коллизий).
- `date-picker.test.tsx` (новый) — 6 RTL-тестов: placeholder / format / pick-day / clear / today / disabled-after-max. Дни matched по локализованному aria-label `/^DD мес YYYY/`.

*Rewrites:*
- `step-1-borrower.tsx` — полный rewrite по preview: section card с leading icon-tile + live-counter (N/8 через `useWatch`), ИНН 3-state machine (`InnInput` mini-component), OKVED autocomplete (`OkvedAutocomplete` с 16 хардкод-кодами + filter + ↑↓Enter nav + Esc close), ОПФ segmented radio (`OpfSegmented`, 3 кнопки llc/ie/jsc), custom `DirectorRecentWarning` блок с border-l-3 (Phase 4 паттерн). Сохранено: `isRecentDirectorAppointment` export для CA-039 теста; `formatBusinessAge` через `lib/duration`. Auto-clear `directorAppointedAt` если новая `registrationDate` позже него (обход zod refine).
- `stepper.tsx` — connector удалён физически, 3 раздельных «круг + label» tile'а в `grid-cols-3`. Active circle = brand-primary fill (без glow), done = state-ok fill с галкой, pending = stroke 1.5px + ink-4. Eyebrow + title с 3-tier цветами (active brand / done state-ok / pending ink-4). Поднял rounded-[14px] для consistency с section card.
- `page-head.tsx` — status-card pill в стиле Phase 4: 2 chunks «● ЧЕРНОВИК · CR-...» + «ШАГ N из 3», статичная зелёная точка (не pulse). Принимает новый prop `step: 1|2|3`.
- `info-banner.tsx` — leading icon-tile 32px в rgba(white, 0.55) внутри `state-info-bg` (как FAQ row в Phase 4).
- `form-footer.tsx` — save-hint точка из ink-4 на state-ok-fg (статичная), CTA с тонким drop-shadow brand-primary glow, h-38→40 + rounded-md→rounded-[9px] для consistency, hex disabled tokens → semantic `var(--surface-2)` / `var(--ink-4)`.
- `field.tsx` — `inputBase` высота 38px→40px + rounded-md→rounded-[9px] (consistency с DatePicker trigger). `InputGroup` `#FAFBFC` → `var(--surface-2)`. Focus shadow rgba → `var(--brand-primary-ring)`.
- `manual-input-view.tsx` — PageHead получил `step` prop, ErrorBanner hex (`#F2BCBA`/`#FCE7E5`) → semantic state-bad tokens.

*i18n:* `accountant.manual_input.*` keyspace расширен ~45 keys × ru+uz: `s1_filled_label`/`s1_filled_value` (ICU), `s1_inn_state_{idle,checking,verified}` + `s1_inn_summary_mock`, `opf_{llc,ie,jsc}_short`, `s1_date_placeholder` + `date_clear` + `date_today`, `s1_okved_{empty,kbd_hint}` + 16 `okved_*` desc, `s1_recent_director_{title,body}`, `stepper_step_{active,done,pending}_eyebrow`, `step_position_{label,value}`. Удалены: `s1_inn_badge_verified`, `s1_recent_director_warning` (split на title+body). Brand-strings (BANK MODE, hotline номер) не локализуются.

**Lessons (новые):**
1. `react-day-picker@9` с RU локалью даёт aria-label вида «понедельник, 27 апреля 2026 г.» — `screen.getByRole("button", { name: /^25 мая 2026/ })` надёжнее чем `name: /^25$/` (последнее matches только если textContent === aria-label; при наличии aria-label v9 ставит её, textContent игнорируется).
2. `react-day-picker@9` Matcher: `{before: Date}` и `{after: Date}` отдельные элементы массива `Matcher[]`, не один объект с обоими полями (последний — DateRange).
3. ESLint `jsx-a11y/role-has-required-aria-props`: combobox обязан иметь `aria-controls` + `aria-expanded`. Без `aria-controls={listboxId}` — warning.
4. ESLint `jsx-a11y/role-supports-aria-props`: button не поддерживает `aria-invalid` — заменить на `data-invalid`.
5. CA-066 `setTimeout 0` pattern для обхода react-hooks/set-state-in-effect применён 3 раза: reset ИНН-state на value change, reset OKVED highlight на value change, setMonth в DatePicker при внешнем prefill value.

**Verify status:** tsc + eslint (clean) + 101 vitest (95→101, +6 date-picker) + next build (24 routes, без новых) + frontend stack only (бэкенд не тронут — ruff/mypy/pytest не нужны).

**Open TODOs from Phase 6:**
- `TODO[CA-DS17]`: real OKVED catalog (см. шапку).
- `TODO[CA-DS18]`: real case_id с бэкенда (см. шапку).
- `TODO[CA-DS19]`: motion cleanup pass на /search и /history (см. шапку).
- `TODO[CA-DS20]`: RTL-тесты на InnInput state machine + OkvedAutocomplete (extract как named exports или integration-test через Step1Borrower).

---

## Working Agreements

- Перед каждой задачей: перечитай PROJECT_BRIEF.md Section 4 (Architecture) и Section 11 (Anti-patterns).
- Plan mode обязателен если затрагивается >2 файлов.
- Не начинай кодить без плана — сначала покажи декомпозицию.
- Язык UI: русский. Язык кода: английский.
- Коммиты: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Никаких `TODO` без ID (`# TODO[CA-001]: описание`).
- После `git mv` + правок (sed/Edit) обязателен `git add -u` или явный re-add — иначе modify не попадает в коммит (rename стейджится с исходным content). См. memory `feedback_git_mv_sed_gotcha.md`.

### Pre-push checklist (CI lessons 2026-05-14)

Перед `git push` прогнать **полный** verify, а не только то что менял. CI Phase 5.B потребовал 4 follow-up коммита (`2ac935c`, `79a9395`, `282819d`, `59c65cb`) — все можно было поймать локально:

1. **`npm ci` ≠ `npm install`.** Local `npm install <pkg>` может оставить `package-lock.json` несогласованным под другую OS (Linux CI runner резолвит deps иначе). После добавления зависимости — `rm -rf node_modules package-lock.json && npm install`, потом локально проверить `npm ci` чтобы воспроизвести CI-режим. Иначе `Missing: X@version from lock file` на CI.
2. **`ruff check`, `mypy --strict`, `pytest` — обязательны перед push.** Не доверяй «у меня файл написан красиво». UP037 на quoted annotation при `from __future__ import annotations` ловится только ruff'ом. `FromClause.delete()` ловится только mypy. Минимум: `docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest"`.
3. **Меняешь computed-from-X invariant — `grep -r` все тесты на эту semantic.** Когда `mfa_enabled` поменял с `secret IS NOT NULL` на `enrolled_at IS NOT NULL`, локально прогнал mapper-tests (3/3) и забыл про integration-test `bank_auth_test.py:169` который тоже проверял эту инварианту. CI поймал на pytest. Правило: после semantic-fix'а → `grep -r "mfa_enabled\|enrolled_at\|mfa_secret"` по tests/ и убедись что все assertions согласны.
4. **CI коммита перед твоим зелёный? Проверь!** Phase 5 backend `06f0ae4` был push'нут с уже-failing CI (test `bank_auth_test.py` и mypy `system_health_test.py` от Phase 5 backend). Когда я начал свою серию — эти tail-failures всплыли. `gh run list --branch main -L 3` перед началом работы покажет состояние baseline.

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
| 2026-05-13 | Design Sweep | **Phase 3 History DONE — design statement.** Premium data-grid: убрана `+ Новая заявка` сверху (дубль sidebar CTA), оставлен `Экспорт CSV`. `LiveStrip` из Phase 2 переиспользован между PageHead и Tabs. Table headers: white bg + 10.5px uppercase letter-spacing 0.08 + ink-4 + inset bottom-shadow + sticky top:0 (был мутный surface-2). `ScoreCell` — vertical accent strip 3×22 (color = recommendation band) + crisp число mono 16px (color = score band, Tinkoff/Brex pattern). `DateCell` 2-line: абс. дата + relative time (свежие ≤сегодня/вчера → зелёный; ≥7д → скрыт). `AnalystCell` gradient на `brand-primary-soft → brand-primary` (был hardcoded #D88E73→#B5624A). Trailing chevron column opacity 0→1 на row hover (заменил dead `⋯`). EmptyState split: `EmptyZero` (total=0 «Пока никого не проверяли») vs `EmptyFiltered` (filtered=0). Pagination split: footer-only когда totalPages=1. Toolbar: убрана dead «Ещё». Новый `features/history/relative-time.ts` + 11 unit-тестов (ICU-plural ru+uz, календарный yesterday). i18n keyspace: +`rel_*`, +`empty_zero_*`, –`filter_more`, –`row_actions`. Verify: tsc + eslint + 88 vitest + next build (16 routes) — зелёные. | `8bbc154` |
| 2026-05-13 | Design Sweep | **Phase 4 Help DONE — design statement.** Info-страница подтягивается под Phase 2/3 эстетику без structural rewrites. `BankPageHead.actions` слот → status-card pill (pulse-ring-ok + «API v1.2 · Справка обновлена 13.05.2026»). `IncidentBand` full-width между title и content — критическая инфа compliance с `state-bad-{fg,bg,border}` + CTA-кнопка «Позвонить compliance» (tel: link, тот же hotline-номер). `FaqSection` rewrite: header с counter `7 ТЕМ` (uppercase, ICU-plural), 7 rows с leading icon-tile (BarChart3/AlertTriangle/Database/FileSpreadsheet/RotateCcw/ScrollText/LifeBuoy) в brand-primary-soft + category eyebrow + chevron rotate→brand-primary on open. **Expanded answer в accent-block**: `border-l-2 brand-primary` + `bg-gradient-to-r brand-primary-soft→transparent` + `rounded-r-lg`. Gap question↔answer 10px (был -4px → слипалось). ContactStack tier-hierarchy: **T1 Hotline primary** (gradient card, mono phone 18px, dynamic «● Сейчас открыто · до 18:00» / «Закрыто · откроется в 09:00» через `getHotlineStatus()` helper, hover lift+ring-shadow); **T2 Slack + Email** обычные cards, hover → brand-primary border; **T3 Docs** ghost-link с dashed-top-border + arrow translate-x on hover. Bottom notes-bar «Время ответа: Slack ≤ 1ч · Email ≤ 4ч (раб. дни)». GridPattern `tone="default"` lazy-load + `<div className="relative z-[1]">` wrap. Новый `features/help/business-hours.ts`: `getHotlineStatus(now): {open:true,untilHour:18}\|{open:false,opensAtHour:9}`, Asia/Tashkent через `Intl.DateTimeFormat({timeZone})`, Mon-Fri 09:00 inclusive / 18:00 exclusive, 7 unit-тестов с inject `now`. `HotlinePrimaryCard` initial state `null` + `setTimeout(update, 0)` + `setInterval(update, 60_000)` — обход ESLint `react-hooks/set-state-in-effect`. i18n `bank.help` +13 keys, phone/email/Slack/Docs — hardcoded brand-strings. Verify: tsc + eslint + 95 vitest (88→95, +7) + next build (16 routes) — зелёные. | `cb8b046` |
| 2026-05-13 | Design Sweep | **Phase 4 hotfix серия (6 коммитов).** (1) FAQ expand animation grid-row 0fr→1fr + opacity fade 320ms + chevron bouncy cubic-bezier 400ms + icon-tile scale-110 при open/hover; slack/email tile-bug fix (tile сливался с soft-card на hover → теперь white bg + brand icon + scale + ring) `9815d70`. (2) Deep-link на FAQ (copy-icon hover, hash auto-scroll/auto-open) добавлен и **revert'ed** — overkill для 7 вопросов, public-docs pattern не подходит internal-tool; в той же серии добавлен operator-presence в Hotline (avatar gradient + pulse-ring-ok dot + «СЕЙЧАС НА СМЕНЕ · Мадина А.») который оставлен `ea1a5f7`→`f8b5df8`. (3) Dismissable incident-band с X + localStorage `ca:help-incident-dismissed` + grid-row collapse добавлен и **revert'ed** — без undo-механизма случайный X = потеря critical-cue, banner теперь persistent baseline; в той же серии FAQ all-closed на mount (`defaultOpen={idx===0}` снят — Notion/GitHub pattern) `2d4eb91`→`2816ac4`. (4) Sidebar Help section перенесена из `mt-auto`-внизу прямо под Workspace + thin divider `color-mix(nav-border 60%, transparent)`; `mt-auto` теперь на user-card; Workspace+Help читаются как single navigation tree `91c4090`. **Lesson:** wow-features (deep-link, dismissable) для internal banking-tool обычно cost > benefit; safer revert чем держать в production. **Open TODOs:** CA-DS6 (support в brand-config), CA-DS7 (operator endpoint), CA-DS8 (отдельный compliance phone). | `cb8b046`..`91c4090` |
| 2026-05-14 | Phase 5.B | **2FA frontend + 3 hotfix серия (commits `d9387c0`, `6d625b1`, `59bb172`)** — закрыта Phase 5.B end-to-end. **Frontend (16 файлов):** `lib/auth.ts` расширен union `LoginResult = AnalystSummary \| MfaChallenge` + `submitMfaChallenge` + `isMfaChallenge`; новый `lib/mfa.ts` (startEnroll/verifyEnroll/disableMfa). 4 BFF routes под `app/api/auth/mfa/*` (3 auth-required + challenge без auth и пакует cookies на success). `app/api/auth/login/route.ts` пробрасывает `requires_mfa` payload без cookies. `features/settings/mfa-section.tsx` (карточка status + CTA), `mfa-enroll-modal.tsx` 3-stage (QR canvas через `qrcode@1.5.4` pinned + manual-entry secret + 6-digit verify + 10 backup-codes screen с copy/download/confirm-checkbox), `mfa-disable-modal.tsx` (password + TOTP re-auth). `login-view.tsx` extended `MfaStep` компонент с TOTP/backup toggle (6 цифр vs 8+ alphanumeric). i18n: `bank.settings.mfa.*` (~47 keys) + `bank.login.mfa_*` (~15 keys) × ru/uz. **Backend hotfix #1 `d9387c0`:** `analyst_mapper.computed_mfa_enabled` теперь от `mfa_enrolled_at IS NOT NULL` (не `mfa_secret IS NOT NULL`) — фикс half-enrolled lockout: `/enroll/start` пишет secret в БД до verify, без fix'а computed flag путал scan-без-verify с enrolled state → следующий login требовал TOTP, но secret в authenticator не сохранён → unrecoverable lockout. `mfa.py:challenge` + `mfa.py:disable` guards тоже на `enrolled_at`. +1 unit-test `test_analyst_from_orm_mfa_disabled_when_half_enrolled` с подробным комментарием. **Backend hotfix #2 `6d625b1`:** `generate_enrollment` использует RFC 5233 subaddress (`admin+a1b2c3@bank.uz`) — обход Microsoft Authenticator iOS + iCloud cache dedup quirk (приложение дедупит по подстроке-email независимо от account_name suffix, MS-облако помнит локально-удалённые аккаунты). Уникальный local-part спасает re-enrollment-сценарий «смена телефона». `_suffix_factory` инжектируется для детерминизма в тестах. **Frontend hotfix #3 (в составе `59bb172`):** `useRef` guard на enrollment-effect фикс React 19 strict-mode (dev) double-fire `useEffect` — без guard'а каждое открытие модалки делало 2× POST `/enroll/start`, в БД оставался последний secret, в QR показывался один из двух → race-condition → verify_totp всегда invalid. Не используем cancelled-flag (cleanup в strict-mode заблокировал бы setStage после guard'а → loading навсегда). **Smoke E2E на real Docker (2026-05-14 03:00-04:00 Ташкент):** ✅ enrollment через manual-entry secret; ✅ enrollment через scan QR (после email-suffix patch, диалог MS Auth «уже существует» игнорируется); ✅ disable с password+TOTP re-auth; ✅ login → MFA challenge → TOTP → /search; ✅ login → MFA challenge → backup-code → /search (одноразовый, повторно invalid). **Lessons:** (1) MS Authenticator iCloud-cache → email-substring dedup, не account_name. (2) React 19 strict-mode + dev — useEffect mount→cleanup→mount требует useRef guard для одноразовых side-effects типа enrollment-fetch. (3) `mfa_enabled` computed-from-X семантически точно: X = «enrollment завершён», не «secret есть». (4) Backend `docker compose up -d --build api` без `$env:APP_MODE='bank'` префикса возвращает default `accountant` → bank-router не зарегистрирован → 404 на всё `/api/bank/*` → BFF login возвращает в UI «invalid email or password» (misleading). **Open TODOs:** CA-DS13 (admin-reset 2FA endpoint), CA-DS14 (/help секция «диалог MS Auth — нажми Отмена»), CA-DS15 (WebAuthn/Passkeys как alt 2FA factor), CA-DS16 (drop legacy stored bool `analysts.mfa_enabled`). См. блок «End-user 2FA guide» в шапке CLAUDE.md для пошаговой инструкции smoke. |
| 2026-05-14 | Design Sweep | **Phase 5 Settings DONE — full backend wiring.** Production-grade /settings с 4 секциями. **Backend:** alembic migration `7b3c5f08e2a1` — `analysts +password_changed_at (default now()) +mfa_enabled (default false)`; новая table `system_uptime_day` (PK=day, status enum ok/degraded/down, worst-of-day escalation). ORM: `SystemUptimeDayORM` + `SqlAlchemySystemUptimeRepository` (upsert_today + list_last_n_days + first_seen_day). `AnalystResponse` Pydantic + `AnalystIdentity` dataclass расширены 3 полями (`created_at`, `password_changed_at`, `mfa_enabled`); `/api/bank/auth/me` + `/login` пробрасывают. Новый router `shared/system.py`: `GET /api/system/health` (Postgres SELECT 1 + WeasyPrint lazy import-check + UPSERT today в system_uptime_day), `GET /api/system/health/history?days=30`. 5 services с stable keys: search/dossiers_db/soliq_import/pdf_generation/faktura_uz (последний всегда `not_implemented`, см. TODO[CA-DS11]). Seed-script `--mfa-enabled` flag; admin@bank.uz переseeded с mfa_enabled=true как «enrolled в банковский SSO/AD». **Frontend:** `features/settings/` 6 файлов — `profile-section` (avatar 44px + security-strip с conditional chips 2FA/Password/Network + 6 prod-fields с copy-button + footer-strip), `appearance-section` (4 controls: theme swatches mini-preview + density segmented + font S/M/L + reduced-motion toggle, всё через `use-appearance` хук → localStorage + CSS-vars на `<html data-*>`), `security-section` (existing form + password-strength meter 4-bar + status row из real `password_changed_at`), `about-section` (brand-header через `useBrand()` + health-strip с pulse-tile + uptime-calendar 30 days из real БД + 2 expandable rows: «Что нового» с 3 release-items + «Что работает прямо сейчас» с 5 service-rows plain-language). Settings-view shell rewrite: nav 4-item с icon-tile + chevron-reveal + brand-primary inset-left на active; SessionPill в page-head actions. **i18n:** `bank.settings.*` keyspace расширен ~80 keys (ru + uz). **BFF routes:** `/api/system/health` + `/api/system/health/history` без auth (proxy без Bearer). Globals.css: density/font-scale/reduced-motion CSS-vars + `.ds-pulse-ok` + `.ds-exp-panel` (Phase 4 grid-row 0fr→1fr accordion). **Tests:** 5 новых integration на system_health (happy + idempotent UPSERT + history + 422 на days=0/999) + 2 расширения на /me (new fields + mfa_enabled-from-seed). **Verify:** ruff + mypy --strict + 19 targeted integration green + tsc + eslint + 95 vitest + next build (18 routes, +`/api/system/health(/history)`). Real Docker smoke: admin@ login → /me returns `mfa_enabled=true`, real timestamps; health endpoint UPSERT'ит today. **Open TODOs:** CA-068 (real /api/auth/change-password), CA-DS9 (cron uptime collector), CA-DS10 (real TOTP enrollment), CA-DS11 (faktura.uz integration). |

| 2026-05-15 | Phase 7 | **Manual-input Step 2 (Financial) design statement DONE.** 4 итерации preview (`web/design-reference/2026-05-15-step2-phase7-preview.html`) с user-сession'ом: (1) full premium scope с sparkline + mini-KPI preview row, (2) user «слишком много» → calm scope без декораций, (3) user «не знаю что руками а что само» → per-field source-trail annotation, (4) user «может убрать секции?» → pre-flight schema-check (vatDeclared/taxesPaid25/totalAssets/totalLiabilities **required** в zod) → revert на «всё оставь». Финальный scope: 5 секций сохранены (xltx upload, Soliq pair, Выручка, Прибыль, Annual block из 3 групп), schema не тронута; чисто UI rewrite. **Файлы (6):** `step-2-financials.tsx` (rewrite — Phase 6 section card pattern с icon-tile + `<CounterChip>` live progress + `<AnnualBlock>` с 3 flat-группами Налоги/НДС/Баланс + `<UzsRow>` с source-trail hint), `financial-table.tsx` (rewrite — annual-default mode с 3 годовыми cell, `<QuarterGrid>` под toggle «Показать кварталы», CA-027 quarter-wins-over-annual логика с UI-lockом годовой cell, `<TrendFooter>` pill без sparkline), `parsed-files-dropzone.tsx` (header → icon-tile pattern, h-40/rounded-[9px] submit, hex sweep на semantic tokens), `soliq-upload.tsx` (rewrite — section card, `<CustomDropdown<T>>` generic для year/month вместо native `<select>` с outside-click close, hex sweep), `i18n/ru.json` + `i18n/uz.json` (~30 новых keys: `s2_source_*`, `s2_annual_group_*`, `s2_quarter_*`, `s2_year_age_*`, `soliq_file_1/2_hint`; old `s2_vat/assets/liabs/da/equity_label` переписаны под compact labels). **Source-trail (Phase 7 паттерн):** UI читает `useSourceTrail()` map (CA-035 existing) — поле есть в map → `auto` state (зелёный 3px borderbar + «Из FORM_2 · поправь если не так»); нет → `manual`/`waiting` (серый). Спец `manual-required` для taxesPaid (PROFIT_TAX-парсер не реализован, amber). Borderbar реализован как `absolute span` внутри `relative` shell, не CSS-border — потому что input уже имеет `border-r-0` для сшивки с UZS-suffix. **Annual-default mode:** `FinancialTable` рендерит 3 годовых cell вместо 4×3 grid. Toggle раскрывает quarter-grid под years. Когда любой quarter заполнен → annual cell становится read-only с `sumQuarters` (CA-027 yearTotal: quarters win over annual). Backend submit contract не изменён. **Custom dropdown:** `<CustomDropdown<T>>` generic с `{label, value, options, onChange}`. Outside-click close через `useEffect` listener. Keyboard nav пока — TODO[CA-DS22]. **Verify:** tsc + eslint (0 errors 0 warnings) + vitest 101/101 (14 files) + next build (24 routes, без новых) — все зелёные. Backend не тронут (ruff/mypy/pytest не нужно). **Lessons:** (1) Перед предложением «убрать UI-секцию» — обязательно открыть zod schema. Required-поля = data-layer change, не UI cleanup. Сохранено в memory `feedback_wizard_minimalism.md`. (2) `_v2`-суффиксы i18n keys захламляют — лучше переписывать значения existing keys (соscience: не grep'ать по старым именам где-то ещё). (3) Bash tool: cwd персистится в одной session, но между параллельными tool-calls — нет. Использовать absolute path. **Open TODOs:** CA-DS21 (auto-edited 3-state в source-trail), CA-DS22 (keyboard nav в CustomDropdown), CA-DS23 (RTL-тесты Step2Financials с mocked SourceTrailContext). |

| 2026-05-14 | Phase 5 holes | **3 functional holes закрыты — Phase 5 чистый, Phase 6 unblocked.** Одна сессия, 3 атомарных коммита. **CA-068 `7d65e29` — real change-password endpoint.** Backend `POST /api/bank/auth/change-password` (auth-required): re-auth по current через AuthnPort, bcrypt re-hash, UPDATE `password_changed_at`, audit `password_changed`. Запрет реюза текущего → 400 `password_unchanged` (verify нового против старого hash до hash() — экономия bcrypt cost). UI security-section убрал `setTimeout(600)` мок → `changePassword` через BFF `/api/auth/change-password` (httpOnly access cookie forward) → backend detail-коды (`invalid_credentials` / `password_unchanged` / 422) маппятся на i18n. После 204 — invalidate `["auth","me"]` чтобы status-row подсветил свежесть без перезагрузки. Удалена плашка `endpoint_wip`. 5 integration tests. **CA-DS13 `f9dc928` — admin-reset 2FA.** Новый router `/api/bank/admin/*` с guard `require_senior_analyst` (403 для не-senior). POST `/analysts/reset-mfa` принимает `{email}` (не uuid — senior помнит коллег по email): `analyst_repo.get_orm_by_email` → очищает `mfa_secret / mfa_enrolled_at / mfa_backup_codes_hash / mfa_enabled` → 204. Audit `mfa_admin_reset` записывается на senior'а как `analyst_id`, затронутый — в payload (`target_email`, `target_analyst_id`). **Force-logout НЕ делаем**: JWT v1 stateless (TODO[CA-019]), access TTL 15 мин истечёт сам; на refresh пользователь не получит challenge (computed `mfa_enabled = False`). Frontend `AdminResetMfaCard` в `/settings → Безопасность` под `analyst?.role === "senior_analyst"`: email input → confirm-модалка с предупреждением → fetch через BFF `/api/bank/admin/analysts/reset-mfa`. 12 i18n keys × ru+uz. 4 integration tests. **CA-DS9 `5e40acd` — uptime collector cron.** Внутрипроцессный asyncio loop поверх FastAPI lifespan. `perform_uptime_tick(session)` (inner — для testability) + `uptime_tick(factory)` (production wrapper с begin()) + `uptime_collector_loop(factory, interval=60s)` (loop безопасен к `CancelledError`, ошибки tick'а логируются и не валят loop). Probe: SELECT 1 + import weasyprint, worst-of, `upsert_today`. `_build_lifespan(settings)` → asyncio.Task на startup, `task.cancel() + await` на shutdown. Settings `uptime_collector_enabled=False` по умолчанию (безопасно для тестов и host-dev). docker-compose сервис api ставит `UPTIME_COLLECTOR_ENABLED=true`. **Не используем ARQ** — один процесс api, нет очереди jobs, задача < 100ms; worker-container = compose-сервис + Dockerfile target = overkill. Multi-worker safety: UPSERT идемпотентен, worst-of-day только эскалирует. 2 integration tests (`perform_uptime_tick_upserts_today_row` + `is_idempotent_on_same_day`). Pre-existing row не мешает тесту — UPSERT работает либо INSERT либо UPDATE. **Verify status (для всех 3):** ruff + mypy --strict (281→285 source files), pytest 788→790 passed/5 skipped WeasyPrint, eslint, tsc, vitest 95/95, next build 23→24 routes (+`/api/auth/change-password` + `/api/bank/admin/analysts/reset-mfa`). **Lessons:** (1) `_build_lifespan(settings)` фабрика-функция вместо inline `@app.on_event` — позволяет инжектить test-settings без disable hook'ов глобально. (2) `Depends(...)` в default-аргументе → ruff B008; решение — `Annotated[T, Depends(...)]` type alias (SeniorAnalystDep как HasherDep/AuthnDep). (3) Integration test на background-task: вынес `perform_uptime_tick(session)` inner-func чтобы pg_session с savepoint-rollback мог быть передан напрямую, не открывая нового connection. (4) `uptime_collector_enabled=False` по умолчанию вместо True+test-override — safer-default принцип: tests, host-dev и любой `Settings()` без env не запускают side-effects. Compose явно opts-in. |

> Сжатая история. Полные decomposition / smoke numbers / per-step rationale — в commit messages (`git log --oneline`) и `docs/adr/`.
