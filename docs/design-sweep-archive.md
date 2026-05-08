# Design Sweep 2026-05-13 — архив фаз

> Подробный per-phase narrative для всех фаз Design Sweep. Активный CLAUDE.md держит только таблицу статусов + текущую фазу; вся история здесь.
>
> **Процесс:** 1 фаза = preview HTML в `web/design-reference/2026-05-{date}-{phase}-preview.html` → user approves → 1 commit → переход к следующей.

## Таблица статусов

| # | Phase | Status | Preview file | Commit |
|---|---|---|---|---|
| 1 | Login | **DONE** | `2026-05-13-login-phase1-preview.html` | `0a1c86c`..`34d97f6` |
| 2 | Search | **DONE** (design statement + 4 hotfix) | `2026-05-13-search-phase2-preview.html` | `c9afbce` → `022dfcf` |
| 3 | History | **DONE** (design statement) | `2026-05-13-history-phase3-preview.html` | `8bbc154` |
| 4 | Help | **DONE** (design statement + 6 hotfix) | `2026-05-13-help-phase4-preview.html` | `cb8b046`..`91c4090` |
| 5 | Settings | **DONE** (визуально + 3 functional holes закрыты 2026-05-14) | — | `06f0ae4` + `d9387c0`/`6d625b1`/`59bb172` + `7d65e29`/`f9dc928`/`5e40acd` |
| 6 | Manual-input Step 1 (Borrower) | **DONE** 2026-05-15 (design statement) | `2026-05-15-step1-phase6-preview.html` | `d2fb869` + `c116908` |
| 7 | Manual-input Step 2 (Financial) | **DONE** 2026-05-15 (design statement + source-trail) | `2026-05-15-step2-phase7-preview.html` (4 итерации) | `40c770d` |
| 8 | Manual-input Step 3 (Loan) | **DONE** 2026-05-15 (design statement + section-card unification) | `2026-05-15-step3-phase8-preview.html` | `94229e8` |
| 9 | Dossier view | **DONE** 2026-05-14 (design statement + SectionCard global + no-icon variant) | `2026-05-15-dossier-phase9-preview.html` | `bcde558` |
| 10 | PDF document | pending | — | — |

---

## Cross-phase technical debt (отложенные находки)

Issues найдены в аудитах но user решил оставить — фиксируем чтобы не потерять. Можно вернуться к ним отдельным sweep после design-фаз.

- **CA-DS1 (login):** Brand «UB / Uzbekbank Credit / BANK MODE» захардкожены в `LoginView.tsx`. CA-066 brand-context до Login не дошёл. Fix: `useBrand()` для brand-mark + name + tagline.
- **CA-DS2 (login):** «Запомнить» checkbox + «Забыли пароль?» link — оба no-op (mock). Либо implement, либо удалить.
- **CA-DS3 (login):** Eyebrow «AUTHENTICATION» — единственный english string в UI.
- **CA-DS4 (login):** `© 2026 Uzbekbank` — год + tenant hardcoded. `placeholder="имя@uzbekbank.uz"` тоже. Заменить на `getFullYear()` + brand-config + i18n.
- **CA-DS5 (login CSS):** ~25 hex значений в `login.module.css` (dark-theme tokens), ESLint guard CSS не покрывает. Нужен dark-theme semantic слой.
- **CA-DS6 (help):** вынести `support` section в `brand-config.json` (phone/email/Slack/Docs/compliance_phone) — сейчас hardcoded в `help-view.tsx`.
- **CA-DS7 (help):** backend-endpoint для real operator-shift presence (`/api/bank/operators/current`).
- **CA-DS8 (help):** отдельный compliance-phone в brand-config + второй CTA в incident-band.
- ~~**CA-DS-LIVE (search):** Live-strip mock~~ — **закрыт `610a86d`/`4e9fcf0`**.

---

## Phase 1 — Login (DONE 2026-05-13)

**Final values:** subtle scale-up (≤+9%, card-width только −7.5%, padding unchanged). Card footprint компактнее, content (title/inputs/CTA) увеличен.

Изменения (9 значений):
- Card `max-width` 384px → **355px** (focused-positioning: Stripe/Linear/Tinkoff territory)
- Title (h1) 28px → **30px** (+7%)
- Subtitle 13px → **13.5px** (+4%)
- Input height 44px → **48px** (+9%), font 13.5px → **14px** (+4%)
- Label font 10.5px → **11px** (+5%)
- CTA height 46px → **50px** (+9%), font 13.5px → **14px** (+4%)
- Form gap 14px → **15px** (+7%)

**Files changed:** `web/src/app/login/_components/login.module.css`.

**Follow-ups:** `-webkit-autofill` override (`4997d5b`) — inset box-shadow 1000px держит dark theme. Card fine-tune (`8dc74cb` 395→380, `34d97f6` 380→355).

---

## Phase 2 — Search (DONE 2026-05-13)

**Решение:** design statement (не subtle scale-up). Премиум private-bank эстетика — Loewe/Brunello Cucinelli, не SaaS-стартап.

*Backend:* `/api/bank/borrowers/search` расширен `card: SearchCardData | null` — `legal_form`, `recommendation`, `revenue_ltm`, `yoy_pct`, `business_age_months`, `signals_total`, `signals_evaluated`, `monthly_revenue_12m`. Реализовано через `LoadDossierForView` use case + KPI calculator.

*Frontend foundation:*
- `globals.css`: bank-tenant override `--nav-bg: #FAF9F5` (warm cream), keyframes `pulse-ring-ok`/`rise`/`ds-orb-drift-a/b`, utility `.ds-grid-pattern`.
- 4 новых компонента: `GridPattern`, `AmbientOrbs` (two-layer wrap: JS parallax + CSS keyframe), `ScoreRing` (112px + count-up 0→score 1.2s), `RevenueSparkline` (SVG Bezier + hover tooltip).
- Хук `lib/use-reduced-motion.ts`.

*Sidebar:* warm cream `#FAF9F5`, premium-card «+ Новая заявка» (rotating plus 90° on hover) — **не filled CTA**, Linear/Notion/Mercury pattern. Active nav-item: `inset 2px 0 0 brand-primary` + white bg.

*Topbar:* trust-pill «● Все системы работают».

*Search-view rewrite:* 34px h1, LiveStrip pill, 56px form, RecentChips с active-spark, ResultCard (ScoreRing + 4 mini-meta + RevenueSparkline + subtle radial gradient).

*i18n:* ~20 новых ключей в `bank.search.*`.

**Initial:** `c9afbce` (16 файлов). Verify: ruff/mypy + 55 backend integration + tsc + eslint + 77 vitest + next build (15 routes).

**Hotfix series:**
- `610a86d` — ring tone из `recommendation` (не display_score); tick marks убраны; **backend `/api/bank/stats/today` + repo + DTO + LiveStrip useQuery** (+5 stats tests).
- `4e9fcf0` — BFF route + drop-shadow halo убран.
- `f9d2ec5` — lazy-load AmbientOrbs/GridPattern через `next/dynamic`.
- `4f6ebb1` — showcase-bar (3 кнопки «Найдено/Не найдено/Пустой» с preset ИНН для real backend flow — product feature, не debug).
- `022dfcf` — Next dev-indicator → bottom-left.

**Decision:** showcase-bar остаётся в production — это product feature.

---

## Phase 3 — History (DONE 2026-05-13)

**Решение:** design statement (full overhaul). Premium data-grid, не hero.

*Backend:* без изменений (переиспользуем `/api/bank/stats/today`).

*Frontend:*
- Новый `features/history/relative-time.ts` — pure helper `formatRelativeTime(iso, now)`, ICU-plural ru+uz, календарный yesterday (не «24-48 часов»). `isFreshTime()` подкрашивает зелёным. 11 unit-тестов с inject `now`.
- HistoryView rewrite:
  - Page head: убрана `+ Новая заявка` (дубль sidebar CTA). Остался `↓ Экспорт CSV`.
  - LiveStrip между PageHead и Tabs.
  - Toolbar: убрана dead «Ещё». Search 38px→40px.
  - Table headers: white bg + 10.5px uppercase + ink-4 + inset bottom-shadow + sticky top:0.
  - `ScoreCell`: vertical accent strip 3×22 (recommendation band) + crisp mono 16px (score band). Tinkoff/Brex pattern.
  - `DateCell` 2-line: абс. дата + relative time (свежие → зелёный; ≥7д → скрыт).
  - `AnalystCell` brand-primary-soft → brand-primary gradient (был hardcoded #D88E73→#B5624A).
  - Trailing chevron column opacity 0→1 на row hover.
  - EmptyState split: `EmptyZero` (total=0) / `EmptyFiltered` (filtered=0).
  - Pagination split: footer-only когда totalPages=1.

*i18n:* `bank.history` keyspace: +`rel_*`, +`empty_zero_*`, –`filter_more`, –`row_actions`.

Verify: tsc + eslint + 88 vitest + next build (16 routes).

**Follow-up — GridPattern background:**
- `.ds-grid-pattern--brand` — color = `color-mix(brand-primary 8%, transparent)`. Default снижен до 4.5%.
- `(bank)/history/_components/history-view.tsx` — `<GridPattern tone="brand" />` lazy-load.
- /search 4.5% ink-1 (нейтральный), /history 8% brand-primary.
- AmbientOrbs **не** добавлены на /history (orbs = hero showroom для /search).

---

## Phase 4 — Help (DONE 2026-05-13)

**Решение:** design statement без structural rewrites — info-страница получает Phase 2/3 паттерны.

*Frontend:*
- `BankPageHead.actions` → status-card pill (pulse-ring-ok + «API v1.2 · Справка обновлена 13.05.2026»).
- `IncidentBand` full-width с `state-bad-*` tones + CTA-кнопка «Позвонить compliance» (`tel:+998712000000`).
- `FaqSection` rewrite: header с counter `7 ТЕМ` (ICU-plural uppercase). 7 rows с leading icon-tile (BarChart3 / AlertTriangle / Database / FileSpreadsheet / RotateCcw / ScrollText / LifeBuoy). Expanded answer в accent-block: `border-l-2 brand-primary` + `bg-gradient brand-primary-soft → transparent` + `rounded-r-lg`.
- `ContactStack` tier-hierarchy:
  - **T1 Hotline primary:** large card, mono phone 18px, dynamic «● Сейчас открыто · до 18:00» / «Закрыто · откроется в 09:00».
  - **T2 Slack + Email:** обычные cards, hover → brand-primary border.
  - **T3 Docs:** ghost-link с dashed-top-border + arrow translate-x.
- Notes-bar «Время ответа: Slack ≤ 1ч · Email ≤ 4ч».
- GridPattern lazy-load + z-1 wrap.

*Helper:* `features/help/business-hours.ts` — `getHotlineStatus(now)` через Asia/Tashkent. Mon-Fri 09:00 inclusive / 18:00 exclusive. 7 unit-тестов с inject `now`.

*`useEffect` pattern:* initial `null` + `setTimeout(update, 0)` + `setInterval(update, 60_000)` — обход ESLint `react-hooks/set-state-in-effect`.

*i18n:* `bank.help` keyspace +13 keys.

Verify: tsc + eslint + 95 vitest (+7) + next build (16 routes).

**Hotfix серия (6 коммитов, same day):**
- FAQ expand animation grid-row 0fr→1fr + chevron bouncy cubic-bezier; slack/email tile-bug fix (`9815d70`).
- Deep-link → revert (`ea1a5f7`→`f8b5df8`) — overkill для 7 вопросов, public-docs pattern не подходит internal-tool. **Operator-presence в Hotline оставлен** (mock `CURRENT_OPERATOR`, TODO[CA-DS7]).
- Dismissable incident-band → revert (`2d4eb91`→`2816ac4`) — без undo случайный X = потеря critical-cue. FAQ all-closed на mount (Notion/GitHub pattern).
- Sidebar Help под Workspace + thin divider (`91c4090`).

**Lesson:** wow-features (deep-link, dismissable) для internal banking-tool обычно cost > benefit; safer revert.

---

## Phase 5 — Settings (DONE 2026-05-14)

**Backend:**
- Alembic migration `7b3c5f08e2a1` — `analysts +password_changed_at +mfa_enabled`; новая `system_uptime_day` table (PK=day, status enum ok/degraded/down, worst-of-day escalation).
- ORM: `SystemUptimeDayORM` + `SqlAlchemySystemUptimeRepository` (upsert_today + list_last_n_days).
- `AnalystResponse` + `AnalystIdentity` расширены 3 полями (`created_at`, `password_changed_at`, `mfa_enabled`).
- Новый router `shared/system.py`: `GET /api/system/health` (Postgres SELECT 1 + WeasyPrint check + UPSERT today), `GET /api/system/health/history?days=30`. 5 services с stable keys (search/dossiers_db/soliq_import/pdf_generation/faktura_uz).
- Seed-script `--mfa-enabled` flag.

**Frontend:** `features/settings/` 6 файлов:
- `profile-section` (avatar 44px + security-strip с conditional chips 2FA/Password/Network + 6 prod-fields с copy-button).
- `appearance-section` (theme swatches mini-preview + density segmented + font S/M/L + reduced-motion toggle — всё через `use-appearance` хук → localStorage + CSS-vars на `<html data-*>`).
- `security-section` (password-strength meter 4-bar + status row из real `password_changed_at`).
- `about-section` (brand-header через `useBrand()` + health-strip + uptime-calendar 30 days + 2 expandable rows: «Что нового» + «Что работает прямо сейчас»).

Settings-view shell rewrite: nav 4-item с icon-tile + chevron-reveal + brand-primary inset-left на active.

**i18n:** `bank.settings.*` keyspace ~80 keys.

**Globals.css:** density/font-scale/reduced-motion CSS-vars + `.ds-pulse-ok` + `.ds-exp-panel` (Phase 4 grid-row accordion).

Verify: ruff + mypy --strict + 19 targeted integration + tsc + eslint + 95 vitest + next build (18 routes).

### Phase 5 functional holes — закрыты 2026-05-14

3 атомарных коммита в одной сессии:

1. **CA-068** `7d65e29` — real `POST /api/bank/auth/change-password`. Re-auth через AuthnPort, bcrypt re-hash, UPDATE `password_changed_at`, audit. Запрет реюза (400 `password_unchanged`). 5 integration tests.
2. **CA-DS13** `f9dc928` — admin-reset 2FA. Новый router `/api/bank/admin/*` с `require_senior_analyst` guard. POST `/analysts/reset-mfa` body `{email}` → очищает MFA fields + audit `mfa_admin_reset`. UI карточка в `/settings → Безопасность` под role-gate. 4 integration tests.
3. **CA-DS9** `5e40acd` — uptime collector cron. Внутрипроцессный asyncio loop поверх FastAPI lifespan (`perform_uptime_tick` + `uptime_collector_loop`, interval=60s). Settings `uptime_collector_enabled=False` default (safer-default), docker-compose ставит `UPTIME_COLLECTOR_ENABLED=true`. **Не используем ARQ** — overkill для одного процесса. 2 integration tests.

Lessons:
- `_build_lifespan(settings)` фабрика-функция вместо inline `@app.on_event` — позволяет инжектить test-settings.
- `Depends(...)` в default-аргументе → ruff B008; решение — `Annotated[T, Depends(...)]` type alias.
- `uptime_collector_enabled=False` по умолчанию — safer-default принцип: tests / host-dev / любой `Settings()` без env не запускают side-effects.

### Phase 5.B — 2FA frontend (2026-05-14)

**Commits:** `06f0ae4` (backend) + `d9387c0`/`6d625b1`/`59bb172` (frontend + 3 hotfix).

**Frontend (16 файлов):** `lib/auth.ts` расширен union `LoginResult = AnalystSummary | MfaChallenge`. Новый `lib/mfa.ts`. 4 BFF routes под `app/api/auth/mfa/*`. `features/settings/mfa-{section,enroll,disable}-modal.tsx` (3-stage enrollment: QR canvas через `qrcode@1.5.4` pinned + manual-entry secret + 6-digit verify + 10 backup-codes). `login-view.tsx` extended `MfaStep` с TOTP/backup toggle. i18n `bank.settings.mfa.*` (~47 keys) + `bank.login.mfa_*` (~15 keys) × ru/uz.

**Critical hotfixes during smoke:**
- `d9387c0` — computed `mfa_enabled` от `mfa_enrolled_at`, не от `mfa_secret`. Half-enrolled lockout fix: `/enroll/start` пишет secret в БД до verify; раньше computed flag путал scan-без-verify с enrolled state → login требовал TOTP, но secret в authenticator не сохранён → unrecoverable lockout.
- `6d625b1` — RFC 5233 subaddress в provisioning URI (`admin+a1b2c3@bank.uz`). Обход Microsoft Authenticator iOS + iCloud cache dedup quirk (приложение дедупит по подстроке-email независимо от account_name suffix).
- `59bb172` — `useRef` guard на enrollment-effect. React 19 strict-mode (dev) double-fire `useEffect` — без guard'а 2× POST `/enroll/start` → 2 разных secret в БД → race-condition.

**Smoke E2E на real Docker (2026-05-14 03:00-04:00 Ташкент):** все 4 пути зелёные (enrollment manual + scan, disable, login TOTP, login backup).

См. `docs/operations/2fa-smoke.md` для пошаговой инструкции.

---

## Phase 6 — Manual-input Step 1 (Borrower) — DONE 2026-05-15

**Решение:** design statement (full overhaul по Phase 4 паттернам). 4 итерации preview.

**Изменения (12 файлов):**

*Deps:* `react-day-picker@^9.14.0` + `@testing-library/user-event@^14.6.1`.

*Новые компоненты:*
- `date-picker.tsx` — wrapper над `react-day-picker@9` + `@base-ui/react/popover`. API строковый ISO `yyyy-MM-dd`. Trigger 40px моноширинный «DD.MM.YYYY». Popover 290px, RU локаль, Mon-first, footer «Очистить» / «Сегодня». 6 RTL-тестов (день matched по локализованному aria-label `/^DD мес YYYY/`).
- `date-picker.test.tsx` — 6 кейсов.

*Rewrites:*
- `step-1-borrower.tsx` — section card с leading icon-tile + live-counter (N/8 через `useWatch`), `InnInput` 3-state machine, `OkvedAutocomplete` (16 хардкод-кодов УзКВЭД 2024 + ↑↓Enter nav + Esc close), `OpfSegmented` (3 кнопки llc/ie/jsc), `DirectorRecentWarning` блок с border-l-3. Auto-clear `directorAppointedAt` при изменении `registrationDate`.
- `stepper.tsx` — connector удалён физически, 3 раздельных «круг + label» tile'а в `grid-cols-3`.
- `page-head.tsx` — status-card pill (статичная зелёная точка, не pulse). Новый prop `step: 1|2|3`.
- `info-banner.tsx` — leading icon-tile 32px на state-info-bg.
- `form-footer.tsx` — save-hint статичная точка, CTA с тонким drop-shadow brand glow, h-38→40 + rounded-md→rounded-[9px], hex → semantic.
- `field.tsx` — input высота 38→40, rounded-md→rounded-[9px], focus shadow → `var(--brand-primary-ring)`.
- `manual-input-view.tsx` — PageHead `step` prop, ErrorBanner hex → semantic state-bad.

*i18n:* `accountant.manual_input.*` +~45 keys × ru+uz.

**Lessons (новые):**
1. `react-day-picker@9` RU локаль даёт aria-label «понедельник, 27 апреля 2026 г.» — `name: /^25 мая 2026/` надёжнее чем `name: /^25$/`.
2. `react-day-picker@9` Matcher: `{before: Date}` и `{after: Date}` отдельные элементы массива.
3. ESLint `jsx-a11y/role-has-required-aria-props`: combobox обязан иметь `aria-controls` + `aria-expanded`.
4. ESLint `jsx-a11y/role-supports-aria-props`: button не поддерживает `aria-invalid` — заменить на `data-invalid`.
5. CA-066 `setTimeout 0` pattern для обхода react-hooks/set-state-in-effect — применён 3 раза.

Verify: tsc + eslint + 101 vitest (95→101, +6 date-picker) + next build (24 routes).

**Open TODOs:** CA-DS17 (real OKVED catalog), CA-DS18 (real case_id), CA-DS19 (motion cleanup /search /history), CA-DS20 (RTL тесты InnInput + OkvedAutocomplete).

---

## Phase 7 — Manual-input Step 2 (Financial) — DONE 2026-05-15

**4 итерации preview с user-сессией:**
1. Full premium scope с sparkline + mini-KPI preview row.
2. User «слишком много» → calm scope без декораций.
3. User «не знаю что руками а что само» → per-field source-trail annotation.
4. User «может убрать секции?» → pre-flight schema-check (vatDeclared/taxesPaid25/totalAssets/totalLiabilities **required** в zod) → revert на «всё оставь».

Финальный scope: 5 секций сохранены (xltx upload, Soliq pair, Выручка, Прибыль, Annual block из 3 групп). Schema не тронута, чисто UI rewrite.

**Файлы (6):**
- `step-2-financials.tsx` — section card pattern + `<CounterChip>` live progress + `<AnnualBlock>` с 3 flat-группами Налоги/НДС/Баланс + `<UzsRow>` с source-trail hint.
- `financial-table.tsx` — annual-default mode с 3 годовыми cell, `<QuarterGrid>` под toggle, CA-027 quarter-wins-over-annual логика, `<TrendFooter>` pill без sparkline.
- `parsed-files-dropzone.tsx` — header icon-tile pattern, h-40/rounded-[9px], hex sweep.
- `soliq-upload.tsx` — section card, `<CustomDropdown<T>>` generic для year/month вместо native `<select>`, hex sweep.
- `i18n/ru.json` + `i18n/uz.json` — ~30 новых keys.

**Source-trail (Phase 7 паттерн):** UI читает `useSourceTrail()` map — поле есть в map → `auto` state (зелёный 3px borderbar + «Из FORM_2 · поправь если не так»); нет → `manual`/`waiting`. Спец `manual-required` для taxesPaid (PROFIT_TAX-парсер не реализован, amber). Borderbar реализован как `absolute span` внутри `relative` shell (не CSS-border — мешает `border-r-0` для UZS-suffix).

**Annual-default mode:** `FinancialTable` рендерит 3 годовых cell вместо 4×3 grid. Toggle раскрывает quarter-grid. Когда любой quarter заполнен → annual cell становится read-only с `sumQuarters` (CA-027 yearTotal: quarters win over annual). Backend submit contract не изменён.

**CustomDropdown:** `<CustomDropdown<T>>` generic с `{label, value, options, onChange}`. Outside-click close через `useEffect` listener. Keyboard nav — TODO[CA-DS22].

Verify: tsc + eslint + 101/101 vitest + next build (24 routes). Backend не тронут.

**Lessons:**
1. Перед предложением «убрать UI-секцию» — обязательно открыть zod schema. Required-поля = data-layer change, не UI cleanup.
2. `_v2`-суффиксы i18n keys захламляют — лучше переписывать значения existing keys.
3. Bash tool: cwd персистится в одной session, но между параллельными tool-calls — нет. Использовать absolute path.

**Open TODOs:** CA-DS21 (auto-edited 3-state в source-trail), CA-DS22 (keyboard nav в CustomDropdown), CA-DS23 (RTL-тесты Step2Financials).

---

## Phase 8 — Manual-input Step 3 (Loan) — DONE 2026-05-15

**Один preview-cycle без переделок.** Финальный scope: три section-card — «Условия кредита» / DSCR pre-score / «Перед отправкой на скоринг». Schema invariant (5 required) не тронута.

**Файлы (9 — 7 modified + 2 new):**
- `step-3-loan.tsx` — `<SectionCard>` shell + live `<CounterChip>` N/5 + `<CategoryBlock>` nested на surface-2. Native `<select>` для term → `<CustomDropdown<number>>`.
- `dscr-summary.tsx` — section-card с TrendingUp + `<StaticPill>` «Обновлено · {date}» без pulse-dot. Sparkbars удалены физически.
- `checklist.tsx` — section-card с ClipboardCheck + counter ok/total. Hex tri-state palette → semantic state-tokens.
- `components/section-card.tsx` (new) — `SectionCard` + `CounterChip` + `StaticPill` visual-only без i18n bindings.
- `components/custom-dropdown.tsx` (new) — extracted из soliq-upload с optional label-prop.
- `soliq-upload.tsx` — cleanup imports → импорт из shared.
- `step-2-financials.tsx` — заменены inline `SectionCard`/`CounterChip` на shared. Signatures `titleKey/subKey/counter` → `title/sub/aux`.
- `i18n/ru.json` + `i18n/uz.json` — новые keys + удалены устаревшие.

**Shared extraction rationale:** 5+ consumer'ов SectionCard/CounterChip (Step 2 ×3, Step 3, DSCR, Checklist) — extract после третьего consumer'а. CustomDropdown — 2 consumer'а, extracted как parity.

**Hex sweep:** ~20 замен в 4 файлах. Semantic tokens. ESLint hex-guard не ловит Tailwind utility-class — гигиена ручная.

**Counter logic:** Step 3 — 5 предикатов `filled` (loanAmount digits>0, termMonths>0, ratePct non-empty, purpose ≥20 симв, category truthy default). Checklist — okCount/totalRows где warn/pending не считаются ok.

Verify: tsc clean, eslint 0 warnings, vitest 101/101 (без новых), next build 24 routes (без новых). Backend не тронут. CI `25887254792` → success 1m4s.

**Lessons:**
1. Когда чистишь imports — внимательно проверь, что `ReactNode` ещё не нужен файлу (TSC поймал моментально).
2. В preview HTML counter logic может расходиться с runtime — runtime = source of truth.
3. Single-cycle preview-approval — впервые без правок: Phase 6/7 паттерны устоялись.

**Open TODOs:** CA-DS24 (real /api/system/cbu/usd-rate).

---

## Phase 9 — Dossier view — DONE 2026-05-14

**Preview HTML** `web/design-reference/2026-05-15-dossier-phase9-preview.html` с 3 сценариями вдоль скролла (happy / partial / risk-heavy).

**После reality-check 4 правки до implementation:**
1. Убрали misleading «Проверено в ГНК» pill — был mock по 9-знач. валидации формата, не реальный ГНК-lookup → дезинформация на decision-screen.
2. Status-eyebrow brand-primary → ink-4 — read-only metadata не должна тянуть глаз (CTA-цвета только для actionable/clickable).
3. Section-card без icon-tile на dossier — banking-минимализм Bloomberg/Tinkoff Бизнес; wizard'ы оставили с icon (там user взаимодействует).
4. Accordion expanded-block: gradient `brand-primary-soft → transparent` → чистый `surface-2` + `border-l-2 brand-primary` — Phase 4 FAQ pattern работал на эмоциональном answer-тексте, на evidence-dl рич.

**Файлы (17 — 1 new + 1 rename + 15 modified):**
- `web/src/components/section-card.tsx` (new, moved из `features/manual-input/components/`; `icon` prop optional → wizard передаёт, dossier нет, header grid `40px_1fr_auto` → `1fr_auto`).
- 4 Phase 8 callsites обновили импорт на `@/components/section-card`.
- Dossier 10 файлов: sub-header rewrite (status-eyebrow + buttons 40/rounded-[9px]); borrower-card в SectionCard без pill; score-gauge в SectionCard; kpi-card без sparkline блока + recharts imports; kpi-row sparkline-prop removal × 3; readiness-badge h-[36px] removal; revenue-24m-chart в SectionCard с period-selector как aux + EmptyChart; risk-signals в SectionCard с CounterChip + semantic severity-pills + accordion clean + source-line в footer; dossier-skeleton KPI heights 120→100; dossier-view passes `application`/`asOf` props.

**i18n:** + `dossier.sub_header.eyebrow_application` / `eyebrow_as_of`; `action_rebuild` «Пересобрать» → «Пересобрать с дополнениями»; + `borrower_card.section_title` / `section_sub`; убраны orphan `borrower_card.title/inn_prefix/verified` (verified — критично, чтобы будущие переводы не вернули misleading); + `score.section_title` / `section_sub`; reco-labels короче; убран orphan `score.label`; + `risk.counter_eyebrow`; risk.title «Сигналы риска» → «Красные флаги».

**Engineering calls:**
- **KpiCard sparkline:** backend `KpiValueOutput.sparkline` всегда `[]` для EBIT/ROE/Debt (3 годовые точки FORM_2 = ломаная, не волна). YAGNI: «UI которая никогда не отрисуется = удалить физически». Reversible: контракт `KpiValueDto.sparkline` остался, frontend просто не консумит; вернуть 5 минут когда backend подаст monthly EBIT projection (TODO[CA-DS25]). Прецедент: Phase 8 убрал sparkbars в DSCR.
- **ГНК pill (CA-003 roadmap):** не смешиваем design-sweep с feature-work. Pill убран физически + TODO[CA-DS28] на hybrid решение (~3-4 рабочих дня отдельный ticket, **legal review обязателен**): public lookup `soliq.uz/services/search/` через scraping + manual upload справки ГНК.

Verify: tsc clean + eslint 0 warnings + vitest 101/101 + next build 24 routes. Backend не тронут. CI `25888968381` → success 1m1s.

**Lessons:**
1. Read-only data screens **не** = wizard surfaces. Phase 6/7/8 паттерны (icon-tile, brand-eyebrow, gradient accordion) придумывались для interactive flows — переносить 1-в-1 на dossier неправильно.
2. Mock-pills на decision-screens (где аналитик принимает решение) категорически опаснее чем на форме-ввода — на форме user видит mock-фидбек, на дотье он **доверяет** «зелёной галке». Mock = убирать или переформулировать на честное.
3. `as_of: date` ≠ `created_at: datetime`. Когда хочешь показать «когда создано» — проверь DTO. На Phase 9 переименовал eyebrow в «ДАННЫЕ НА dd.mm.yyyy» — honest по семантике, нет backend change.
4. Shared shell extraction — при 5+ consumer'ах переноси в global `components/`, не оставляй в `features/<feature>/components/`.

**Open TODOs:** CA-DS25 (real backend sparkline), CA-DS28 (hybrid CA-003 ГНК lookup + manual upload).

Phase 10 (PDF document) — финальная фаза Design Sweep, unblocked.
