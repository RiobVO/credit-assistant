# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус, открытые задачи и рабочие соглашения.
> Историческая глубина: `docs/session-log.md` (полная история), `docs/design-sweep-archive.md` (per-phase narrative), `docs/operations/` (smoke-guides).

---

## Current Status

**Pre-demo MVP ready — closed 2026-05-18.** Tier 0/1/2/3 complete (32+ atomic commits в финальной сессии). Детальная chronology — `docs/session-log.md` + `git log --oneline` + `docs/adr/`.

### Tier closure summary

- **Tier 0 deal-breakers**: real fixtures (T0.1) · CBU API real integration (T0.2, ADR-0014) · ГНК Phase A manual upload (T0.3) · UZ-локализация PDF + 4 follow-up gaps + apostrophe sweep (T0.4, ADR-0015) · VAT parser real 10006_41/45/47 (T0.5).
- **Tier 1 prod-killers**: case_id seq BR-YYYY-NNNN (T1.1) · refresh-token rotation + Redis denylist (T1.2, ADR-0016) · PII encryption at rest Fernet/MultiFernet (T1.3, ADR-0017) · multi-tenant Approach A pure (T1.4, ADR-0018) · LDAP AuthnAdapter (T1.5, ADR-0019).
- **Tier 2 data quality**: dynamic units FORM_1/2 (T2.1) · VAT через T0.5 · PROFIT_TAX (T2.3) · faktura.uz honest stub (T2.4, ADR-0020). Все 5 xltx-форматов покрыты.
- **Tier 3 operational readiness (6/6)**: structured logging + correlation_id (T3.2) · Postgres backup + restore drill (T3.4) · on-prem tarball deploy (T3.6, ADR-0021) · audit-log CSV export (T3.5) · observability GlitchTip on-prem (T3.1, ADR-0022) · Prometheus + Grafana metrics (T3.3, ADR-0023). 3 ADR'а, 4 playbook'а, 7 ops-scripts/configs.

### Stack state (2026-05-18)

- Docker compose поднят: `credit-api` (8000), `credit-postgres` (5433), `credit-redis` (6379) — все healthy. Сегодня smoke'нул `credit-db-backup` sidecar (backup + restore_drill PASS exit=0).
- Backend env: `APP_MODE=bank`, `BRAND_ID=default`, `PII_ENC_KEYS` задан тестовым Fernet-ключом (`/tmp/pii_key.txt`, prefix `iEuuP5WADM_...`). БД зашифрована — без ключа restore из `backup-pre-t13.sql` (gitignored).
- Frontend Next dev (Turbopack) `npm run dev` в `web/` — порт 3000. После T3.6.1 production-image тоже билдится.
- Seeded analyst для smoke: **email `t04@bank.uz`** / **password `T04Smoke!`**, без MFA.
- Dossiers в БД: 49 (47 backfilled `BR-2026-0001..0047` + smoke `BR-2026-0048..0049`). Snapshot.payload + drafts.payload зашифрованы. Demo scenarios используют `BR-2026-0030/0040/0042/0046/0047` (см. `docs/demo/scenarios.md`).
- Backups: `./backups/` (gitignored) — 2 dump'а после T3.4 smoke.

### Active focus — выбор следующего шага

Pre-demo MVP ready. Открытые направления (НЕ блокеры, dispatch по сигналу):

1. **T4 compliance pack** (параллельно): pentest узб-лаборатории · аттестат УзСтандарта на ПДн (Закон РУз №547) · IT-Park / Uzinfocom резидентство · Admin Guide / Security Architecture / DRP/BCP RU+UZ. Старт за 2 мес до bank tender.
2. **Real-bank pilot trip**: install playbook `deploy/README.md` + demo walkthrough `docs/demo/scenarios.md` (5 готовых сценариев на существующих BR-2026-00XX) + onboarding session с пилот-банком.
3. **Pre-pilot smoke (✋ обязательно перед demo trip)** — playbook `docs/operations/pre-demo-smoke.md`: 8 routes × 3 темы + 4 пути 2FA + 8 edge-UX сценариев (Блок 5). Console-error gate, sign-off table. Прогон ~60–90 минут, повторный за 24 часа до выезда.
4. **Post-demo hardening backlog** (не блокеры):
   - CI Docker job (опционально — ubuntu-latest уже работает).
   - Sentry sourcemaps upload через release pipeline (`sentry-cli sourcemaps upload`).
   - AlertManager rules-as-code (сейчас в Grafana UI).
   - **T2.1b** real-fixture smoke на «млн / полные сум» multiplier branches FORM_1/2 (нет fixture от папы).
   - **T2.4b** faktura.uz real client — pre-condition: пилот-банк даёт OAuth-токен.
   - **T1.5b** OAuth2/OIDC AuthnAdapter — pre-condition: запрос пилот-банка на Okta/Azure AD.
   - **T1.5c** openldap testcontainer (T1.5 покрыт mock-only).
5. **Active code-level TODOs** (`grep TODO\\[CA- src/ web/src/`):
   - **CA-001** ИНН checksum по ГНК-алгоритму (`src/domain/value_objects/inn.py`).
   - **CA-002** Circular invoicing — полноценная graph-детекция циклов через `networkx` для 3+ узлов (`src/domain/rules/counterparty/`).
   - **CA-003** Real ГНК lookup — pre-condition: legal review (см. также CA-DS28).
   - **CA-019** Access-token denylist для force-logout (formally T1.2 закрыта только refresh-rotation; access ttl 15м истекает сам).
   - **CA-031** Source-trail invasive refactor — `applyToForm` все ячейки формы (UX nice-to-have).
   - **CA-DS19** Pulse-dot motion cleanup в DSCR-summary (UI polish, frozen pre-demo).
   - **CA-DS25** KPI sparkline — pre-condition: monthly_turnover≥12 источник (VAT_DECL monthly chain или ESF). Не PROFIT_TAX (annual).
   - **CA-DS28** ГНК public lookup на soliq.uz/services/search/ — pre-condition: legal review.
   - **CA-DS30** Bulk anonymize 28 xltx fixtures через openpyxl script (1/28 anon на месте сейчас).

### Frozen scope (не трогать до post-demo)
- UI polish: новые цвета, шрифты, тени, анимации.
- Расширения dark theme, 4-я тема, accent variants.
- Новые design tokens, brand-tenant новые секции.
- CA-DS25 (KPI sparkline) до monthly_turnover-источника (VAT_DECL monthly chain или ESF), новые OKVED-каталог расширения сверх baseline.
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
- **T1.2 refresh rotation** (ADR-0016): каждый `/refresh` денилист'ит входящий jti в Redis (`SET NX EX`), выдаёт новую пару. `/logout` денилист'ит refresh из BFF cookie (optional `LogoutRequest.refresh_token`, cross-account guard). `REDIS_URL=None` → `NullRefreshTokenDenylist` no-op (stateless 7-day fallback для dev). `REDIS_URL` задан, Redis недоступен → fail closed на `/refresh` (compromised tokens не проскочат). BFF refresh route обновляет **обе** cookies из upstream response.
- **T1.3 PII encryption** (ADR-0017): `PII_ENC_KEYS` env (comma-separated Fernet keys, первый primary write, остальные read fallback). 6 columns шифруются через TypeDecorator: `analysts.{full_name,mfa_secret}`, `borrowers.director_name`, `borrower_snapshots.payload`, `drafts.payload`, `gnk_certificates.file_bytes`. Wrap pattern для JSONB — `{_encrypted: true, ciphertext: ...}`. `audit_log` emails через `infrastructure/auth/email_mask.py`. Sentinel `gAAAAA` для backward-compat plain reads. `PII_ENC_KEYS=None` → `NullPiiEncryptor` passthrough (dev fallback). Production startup-assertion crash при отсутствии ключа. ИНН/name/red_flags оставлены plain. Rotation runbook — `docs/operations/pii-key-rotation.md`.
- **T1.5 LDAP authn** (ADR-0019, LDAP-only): `AUTHN_MODE=seeded|ldap` env (default `seeded`). `LdapAuthnAdapter` использует `ldap3` (pure Python, async via `asyncio.to_thread`) — service-bind по `LDAP_BIND_DN/PASSWORD`, search по `LDAP_USER_SEARCH_FILTER`, user-bind для verify password, role resolution по `memberOf` (senior precedence над analyst). Lazy upsert через `analyst_repo.upsert_from_ldap(email, full_name, role)` — новый row с `password_hash=NULL`, `authn_source='ldap'`; existing — update full_name/role, mfa-state сохраняется, `authn_source='seeded'` НЕ перетирается (break-glass invariant). `BreakGlassAuthnAdapter` — для email из `ADMIN_BREAK_GLASS_EMAILS` whitelist использует SeededAdapter, source override на `break_glass`. `AuthnPort.authenticate` возвращает `AuthnResult(identity, source)`; audit-log payload login event'а содержит `authn_source` для compliance trail. `_validate_runtime_config` (T1.4) ловит missing LDAP_* env при `AUTHN_MODE=ldap` на boot. `change-password` endpoint блокируется 400 `ldap_user_cannot_change_password` для users с `password_hash IS NULL`. Playbook `docs/operations/ldap-setup.md`. OAuth2/OIDC → T1.5b, openldap testcontainer → T1.5c backlog.
- **T1.4 multi-tenant isolation** (ADR-0018, Approach A pure): single-tenant per deployment. `Settings.brand_id` (env `BRAND_ID`, default `"default"`) — single source of truth. `_validate_runtime_config(settings)` helper в `interfaces/api/app.py` обобщает startup-asserts: BRAND_ID резолвится в `config/brands/<id>.json` (RuntimeError при mismatch) + PII_ENC_KEYS prod-mandatory. `load_brand(brand_id)` mandatory arg, env-fallback внутри loader убран — каждый call-site обязан явно пробросить `settings.brand_id`. `audit_log.brand_id VARCHAR(50) NOT NULL DEFAULT 'default'` + index `(brand_id, created_at)` для forensics — repository конструктор принимает brand_id, DI factory `get_audit_log_repo` пробрасывает `settings.brand_id`. 4 не-DI callsite ('shared/dossier × 2, dossier_pdf, bank/search) — instantiate с `brand_id=get_settings().brand_id`. Deploy playbook `docs/operations/multi-tenant-deploy.md`: separate compose-project per bank, offset host-ports, dedicated volumes, per-brand `.env`. brand_id в `borrowers/dossiers/snapshots/drafts/analysts` НЕ добавлен — out of scope для Approach A.
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

### PDF i18n conventions (T0.4 / ADR-0015)
- **PdfMessages DTO + JSON loader**: `application/dto/pdf_messages.py` — frozen dataclass со scalar + `Mapping[str, str]` (severity/recommendation/legal_form_full/short/kpi_label/evidence_label/gnk_status/gnk_source/tax_episode/business_age_year/page_footer/signal_breakdown) + `tuple[str, ...]` (month_full/short) полями. Loader `infrastructure/i18n/pdf_messages.py` парсит `config/pdf-i18n/{ru,uz}.json`, группирует dotted-keys (`severity.critical`) в Mapping и валидирует missing-key strict через `IncompletePdfMessagesError`. Singleton `default_pdf_messages(locale)` с `lru_cache(maxsize=2)`.
- **Closure-инжектные Jinja filters**: `make_fmt_uzs(messages)`, `make_fmt_date(messages)`, `make_severity_label(messages)` и т.д. — пересобираются в `WeasyPrintPdfRenderer.render` через `_register_locale_filters(bundle.messages)` per-render. Locale-independent (fmt_pct / fmt_inn / severity_color/bg) остаются module-level.
- **observations_builder messages parameter**: `build_observations(snapshot, kpis, red_flags, registry, messages)`. F-strings заменены на `messages.X.format(pct=..., year=...)` для head/num/ctx. UZ-rule_names резолвятся в `RenderDossierPdf` через `_rule_name_for_lang(rule, lang)`.
- **Rule.name_uz required**: `RuleSpecYaml.name_uz: str = Field(min_length=1)` — schema-strict, fail-fast на load_registry. `domain/rules/rule.py` имеет soft default `name_uz = ""` для inline test-fixtures; `RenderDossierPdf` fallback на `rule.name` в UZ-ветке если name_uz пуст.
- **Endpoint `?lang=`**: `GET /api/dossier/{id}/pdf?lang=ru|uz` с fallback chain `query → brand.default_lang → "ru"` через `_resolve_lang`. Audit-log `download_pdf` payload содержит `{"lang": resolved}`.
- **BrandConfig.default_lang**: optional поле в `config/brands/<id>.json` (`defaultLang: "ru"|"uz"|null`). `default.json` оставлен без — fallback на "ru"; `uzbekbank.json` получит `"defaultLang": "uz"` отдельным таском после UZ-демо validation.

### Frontend conventions
- **CA-053** strict-mode useEffect: `cancelled`-guards в `.finally()` опасны для terminal UI-flags (loading/error). Для UI-flags `setIsLoading(false)` ставь безусловно.
- **CA-058** prefill Шага 1: при «Пересобрать с дополнениями» — borrower-карточка через sessionStorage (`ca:manual-input-prefill-step1`). Финансы и кредит остаются defaults.
- **CA-060** Design tokens (ADR-0011): один design system, brand-tenant через `config/brands/<id>.json`. Semantic слой в `globals.css`: `--surface/-2/-3`, `--ink-1..4`, `--state-{ok,warn,bad,info,neutral}-{fg,bg,border}`, `--brand-primary/-hover/-soft/-ink/-ring`. Chart-палитра 9 токенов. **CA-DS5 / ADR-0013**: `[data-theme="dark"]` блок переопределяет все семантик-токены под slate/anthracite. `[data-theme="system"]` живёт под `@media (prefers-color-scheme: dark)` + live matchMedia listener в `useAppearance`. SSR no-FOUC inline script в `<head>`. PDF досье locked light forever — `dossier_pdf.py` игнорит current theme.
- **CA-061** mode-conditional (ADR-0011): `if (mode === "bank")` запрещён глубже top-level shells. Хук `useAppMode()` (`web/src/lib/use-app-mode.ts`) — единственная точка для client-shells.
- **CA-062** ESLint hex guard: `no-restricted-syntax` для `src/features/**` + `src/components/**`. **Не ловит** Tailwind utility `bg-[#XXXXXX]` — ручная гигиена.
- **CA-063 / CA-DS29** i18n infra: `next-intl` 4.4.1, runtime locale switcher через `ca_locale` cookie (CA-DS29) с fallback на `NEXT_PUBLIC_LOCALE` env → `DEFAULT_LOCALE`. Keys в `web/src/i18n/{ru,uz}.json` (keyspace `shared/bank/accountant/dossier`). RTL-тесты обёртывать в `<NextIntlClientProvider locale="ru" messages={ru}>`. **Server reads cookie через `next/headers cookies()`** — layout.tsx и i18n/request.ts: единый source of truth. Smena локали → server action `setLocaleAction` → `revalidatePath('/', 'layout')`, без page reload. **Trade-off**: `cookies()` в layout делает все routes dynamic — не страшно для bank-internal tool. **Brand-strings (имена, теглайны) не локализуются** — это tenant-config. **PDF endpoint игнорит current UI locale (`ca_locale` cookie)** — templates bilingual (T0.4 / ADR-0015), но фронтенд при download'е пока **не пробрасывает** cookie в `?lang=` query → рендер берёт `brand.default_lang` (uzbekbank → uz, default → ru fallback). Wire-up cookie→query — backlog CA-DS29-pdf.
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

- **Pre-demo smoke (gate перед pilot trip, ~60–90 мин)** — `docs/operations/pre-demo-smoke.md`.
- **Demo scenarios walkthrough (5 готовых borrower'ов, ~25–30 мин)** — `docs/demo/scenarios.md`.
- **2FA smoke (4 пути, ~10 мин)** — `docs/operations/2fa-smoke.md`.
- **PII key rotation + recovery** — `docs/operations/pii-key-rotation.md` (T1.3 / ADR-0017).
- **Multi-tenant deploy (separate compose-project per bank)** — `docs/operations/multi-tenant-deploy.md` (T1.4 / ADR-0018).
- **LDAP setup + ops runbook** — `docs/operations/ldap-setup.md` (T1.5 / ADR-0019).

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
