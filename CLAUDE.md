# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус, открытые задачи и рабочие соглашения.
> Историческая глубина: `docs/session-log.md` (полная история), `docs/design-sweep-archive.md` (per-phase narrative), `docs/operations/` (smoke-guides).

---

## Current Status

**T3.2 (Structured logging + correlation_id) complete 2026-05-18** (commits `43aaef5` + `44ea91e` + `493fb71` + `baf616c` + this). 4 атомарных коммита. Foundation для T3.1 (Sentry tags) / T3.3 (Prometheus labels) / T3.5 (audit-export forensics). **T3.2.1** `config/logging.py` переписан на `structlog.stdlib.ProcessorFormatter` + `LoggerFactory` — stdlib и structlog делят один pipeline (foreign_pre_chain прогоняет stdlib records через те же processors, включая `merge_contextvars`). `setLogRecordFactory` глобальный hook инжектит `structlog.contextvars` в `LogRecord.__dict__` до filters/handlers (root-`Filter` не подошёл: Python design не применяет parent filters к propagated records от child loggers). Idempotent guard через module-flag `_CONFIGURED` (повторный `configure_logging` обновляет только level, не плодит handlers и не сносит pytest caplog). **T3.2.2** `RequestIDMiddleware` (`BaseHTTPMiddleware`): X-Request-ID echo / auto-gen `uuid4().hex` 32 chars, `bind_contextvars(request_id=...)` вокруг handler-call, `unbind` в `finally` (между запросами context чистый). **T3.2.3** wire в `create_app` последним `add_middleware` → outer в LIFO-стеке (bind ДО CORS/error-handler, echo header в финальном response включая 4xx/5xx). `shared/health.py` получил instrumental `logger.info("health_check")` для integration probe. **T3.2.4** `audit_log.request_id VARCHAR(32) NULL` колонка (Alembic `a7c1e4d8b3f5`) + index. Repo читает из `structlog.contextvars.get_contextvars()` best-effort — CLI/jobs/background-tasks без middleware пишут NULL (валидно). Forensics: при инциденте оператор знает X-Request-ID из support ticket → `SELECT * FROM audit_log WHERE request_id = 'xxx'` дотягивает полный сюжет. Tests: 4 unit (logging) + 5 unit (middleware) + 4 integration (in-src TestClient roundtrip) + 2 integration (testcontainers repo). 844 unit pass, ruff + mypy strict clean. **Active — T3.x приоритизация next (T3.4 backup / T3.6 on-prem deploy — deal-breakers).**

**T2.4 (faktura.uz honest stub, CA-DS11) complete 2026-05-18** (commits `b7b96df` + this). ADR-0020 «Defer faktura.uz real integration until bank-provided token». Без OAuth-токена пилот-банка mock-only client с придуманным форматом JSON = fake-green risk; решено сделать honest stub messaging вместо технического стаба. Backend tip /api/system/health для `faktura_uz` явно упоминает OAuth-токен ЮЛ + альтернативный путь (Excel my3.soliq.uz, VAT_REGISTRY_ILOVA на T0.5+T2.1). Frontend badge `service_status_not_implemented` переименован: RU «В разработке» → «Опционально», UZ «Ishlab chiqilmoqda» → «Ixtiyoriy». Status enum в API contract не меняется. Tests: +1 integration assert на tip mentions OAuth/токен/my3.soliq.uz. 858 unit pass, ruff + mypy strict clean. Real-client integration → T2.4b backlog с pre-condition «банк-пилот предоставил OAuth-токен», pattern по ADR-0014. **Tier 2 complete — переход к Tier 3 (Operational readiness).**

**T2.1 (Dynamic unit detection FORM_2 + FORM_1, CA-028) complete 2026-05-18** (commits `5721b02` + `c5565fc` + `4f175f0` + `ad53109`). 4 атомарных TDD-коммитов. `parse_unit_multiplier(wb, fmt) -> (Decimal, str | None)` helper в `header_parser.py` динамически читает «Единица измерения»-cell (FORM_2 B24 / FORM_1 B23). Поддержанные варианты: «тыс. сум.» (×1000, default), «млн. сум.» (×1_000_000), «сум.» полные (×1). Unknown / empty → fallback ×1000 + warning (банк-friendly, не теряем файл). Matching case-insensitive substring, защита от «ТЫС.» / «Млн». Узбекские `soʻm` / `so'm` placeholder для будущих локализаций. PROFIT_TAX / VAT_DECLARATION / VAT_REGISTRY_ILOVA → `UnsupportedFormatError` (их парсеры ×1, helper защищён от misuse). `form2_parser.py` + `form1_parser.py` потребляют multiplier через arg-параметр в `_money_kx` / `_signed_money` / `_aggregate_debt` (16 money-cells FORM_2, 22 балансовых FORM_1, 5 долговых компонент). Backward compat: 13/13 real fixtures = «тыс. сум.» (×1000), поведение не меняется. Real-fixture smoke на «млн / полные сум» — backlog (T2.1b, нет fixture от папы). Tests: 10 unit helper + 5 FORM_2 + 5 FORM_1. 336/336 pytest pass (28 real fixtures включительно), ruff + mypy strict (73 файла) clean. Closes CA-028. **Active — T2.4 faktura.uz integration (CA-DS11).**

**T2.3 (PROFIT_TAX parser, CA-029b) complete 2026-05-18** (commits `76be44d` + `e99bc2b` + `4221eea` + `d281ef6` + `39f02e7`). 5 атомарных TDD-коммитов. `ProfitTaxData` DTO (минимум — header + `taxable_profit` (L31, код 030 signed) + `profit_tax_total` (L39, код 080 gross computed)). `parse_profit_tax(wb)` читает сводку list01 rows 28-46 (column K код, L значение), multiplier ×1 (полные сум, в отличие от FORM_2 ×1000) — cross-check L29 ≈ FORM_2 F6 × 1000 подтверждён на ZAMIN (305002665). `SoliqXltxAdapter._dispatch` диспетчит PROFIT_TAX, `ParseManualInputFilesUseCase._merge_profit_tax` пишет в `taxes_paid_by_year[year]` через `_set_once` (single-source, FORM_2 G30 в use-case не мерджится). Quarterly (Q1/Q2/Q3) — silent skip с warning, mirror FORM_2 CA-027 option b (защита от Q1 layout drift, L36 в Q1-фикстуре содержит мусор=233801 вместо ставки 15). Closes 4 xfail в `tests/parsers/real_xltx_test.py` — все 28 real fixtures pass. Tests: 8 unit parser + 6 unit use-case. 316/316 pytest (application + adapters + parsers), ruff + mypy strict clean. **Heads-up CA-DS25 correction:** roadmap утверждал «T2.3 замыкает CA-DS25 (KPI sparkline)» — corrected: sparkline требует monthly_turnover≥12 (VAT_DECL chain / ESF), не annual PROFIT_TAX. CA-DS25 frozen с обновлённым pre-condition. **Active — T2.1 dynamic units FORM_2 (CA-028).**

**T1.5 (LDAP AuthnAdapter, LDAP-only) complete 2026-05-18** (commits `dec6332` + `9c43245` + this). ADR-0019. `AUTHN_MODE=seeded|ldap` env switch (default `seeded`). `LdapAuthnAdapter` (ldap3 pure Python, service-bind → search → user-bind verify, memberOf → role mapping, async via `asyncio.to_thread`) + `BreakGlassAuthnAdapter` (email whitelist → seeded fallback, source override на `break_glass`). `AuthnPort.authenticate` теперь возвращает `AuthnResult(identity, source)` — audit-log login payload содержит `authn_source` для compliance trail. Alembic `f4a2d6c9e3b8`: `analysts.password_hash` NULLABLE + `authn_source` column + CHECK constraint. `analyst_repo.upsert_from_ldap()` для lazy provisioning. `_validate_runtime_config` extended. `change-password` endpoint блокируется для LDAP-users. Playbook `docs/operations/ldap-setup.md`. 17 unit + 3 integration tests новых. OAuth → T1.5b backlog, openldap testcontainer → T1.5c backlog. **Tier 1 complete — переход к T2 (Data quality).**

**T1.4 (Multi-tenant runtime isolation, Approach A pure) complete 2026-05-18** (commits `44c42a6` + `80e8cfc` + this). ADR-0018. PROJECT_BRIEF Sec 11 review сузил scope — single-tenant per deployment без brand_id в data-tables. `Settings.brand_id` + `_validate_runtime_config(settings)` helper в `app.py` (обобщает BRAND_ID resolve + PII_ENC_KEYS prod check). `load_brand(brand_id)` mandatory arg, env-fallback убран. `audit_log.brand_id` колонка (Alembic `e7f9a3c2b8d1`, VARCHAR(50) NOT NULL DEFAULT 'default' + index) для forensics. Repository конструктор принимает brand_id, 5 callsites через `settings.brand_id`. Playbook `docs/operations/multi-tenant-deploy.md` — separate compose-project per bank (offset ports, dedicated volumes, per-brand `.env`). 6 unit + 3 integration tests новых. **Active — T1.5 LDAP/OAuth (CA-020).**

**T1.3 (PII encryption at rest) complete 2026-05-18** (commit `e153be3`, CI ✓ run 26029032045). ADR-0017. `PiiEncryptorPort` + `FernetPiiEncryptor` (`MultiFernet` rotation) + `NullPiiEncryptor` fallback. SQLAlchemy TypeDecorator: `EncryptedString` / `EncryptedJsonb` (wrap `{_encrypted: true, ciphertext: ...}`) / `EncryptedBytea`. 6 PII columns: `analysts.{full_name, mfa_secret}`, `borrowers.director_name`, `borrower_snapshots.payload`, `drafts.payload`, `gnk_certificates.file_bytes`. `audit_log` emails masked через shared `infrastructure/auth/email_mask.py` (3 callsites: mfa, authenticate_analyst, admin). Alembic `c5d2f3a7e1b4`: VARCHAR length expansions (mfa 200, full_name/director 500) + data encrypt pass + idempotent (sentinel `gAAAAA` / `_encrypted:true` skip). `PII_ENC_KEYS` env. Production startup-assertion (staging/prod без ключа → crash). Closes CA-DS12. Tests: 5 unit (Null) + 8 unit (Fernet rotation/invalid) + 9 unit (TypeDecorator backward-compat) + 5 unit (email_mask) + 6 integration (testcontainers raw SELECT vs ORM SELECT). Migration verified roundtrip: downgrade decrypt → upgrade re-encrypt → idempotent re-run. **Backup `backup-pre-t13.sql` лежит на хосте (gitignored) — restore-точка если в БД что-то пойдёт не так.**

**T1.2 (refresh-token rotation + Redis denylist) complete 2026-05-18.** ADR-0016. `RefreshTokenDenylistPort` + Redis adapter (`SET NX EX`, TTL clamp до 1s) + `NullRefreshTokenDenylist` fallback при `REDIS_URL=None`. `/refresh` rotation: decode → `is_denied` → `is_active` → `deny` NX → выдаём новые access+refresh. `/logout` денилист'ит активный refresh из optional `LogoutRequest` body (best-effort, cross-account guard по `claims.analyst_id == analyst.id`). BFF refresh route обновляет **обе** cookies (access + ca_refresh); logout прокидывает refresh upstream. Fail closed при Redis недоступности с заданным `REDIS_URL`. Closes CA-019. Tests: 8 unit (`null` 2 + `redis` 6 fakeredis) + 2 integration (testcontainers redis) + 7 интеграционных (4 новых на rotation/double-use/cross-account + расширение 3 существующих).

**T1.1 (case_id monotonic sequence) complete 2026-05-18** (commit `4c77d7c`, hotfix `65827f1`, CI ✓ run 26006304031). Banking-grade BR-YYYY-NNNN на `dossiers.case_id` колонке (compromised B без Phase 4 application entity). Existing 47 dossiers backfilled `BR-2026-0001..0047` по `created_at` ASC. Allocator: `pg_advisory_xact_lock(year)` + `ALTER SEQUENCE RESTART` на year boundary + `nextval`. Закрывает CA-DS18b/c. Драйверы изменений: `_application_id`/`_format_application_id` derived helpers удалены, frontend `formatCaseId` + test удалены. E2E smoke (BR-2026-0048 на новый dossier) ✓.

**Hotfix 65827f1 (T0.4 B1 регрессия в тестах):** `test_registry_factory.py` inline YAML не получил `source_uz` placeholder после T0.4 B1 commit `6db0061` — CI был красным 5 коммитов подряд начиная с T0.4. Pydantic ValidationError раздавался раньше проверяемой ветки (unknown rule / missing rule / invalid severity / missing name_uz). Поправил 4 inline YAML с `source_uz: src_uz`. Lesson: **pre-push checklist пункт 4** («CI коммита перед твоим зелёный? `gh run list --branch main -L 3`») игнорирование стоит сессии — следующий push наследует красный baseline.

**T0.4 (UZ-локализация PDF) + follow-up complete 2026-05-18.** Все 4 gaps live-browser walkthrough'а закрыты (B1+B2 source/message_uz сквозь стек, B3 OKVED PDF picker, B4 UZS-форматтеры) + CA-DS29-apostrophe (355 ASCII apostrophes → U+02BB ʻ в uz.json). Tier 0 целиком closed.

**T1.4 closed 2026-05-18.** См. roadmap.

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

Закрыто 15 из 15 Design Sweep tail items 🎉. Frontend stack: 27 test files, 224 vitest tests (после T0.4 follow-up). Backend pytest на B2 zone: 215 ✓. Открытые TODO с pre-conditions: **CA-003** (real ГНК lookup ждёт CA-DS28 legal review), **CA-DS18b/c** → перенесены в T1.1 (compromised B: sequence на dossiers, не Phase 4 application entity), **CA-DS25** (KPI sparkline ждёт CA-029b cashflow parser), **CA-DS28** (ГНК ждёт legal review).

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

**Stack state на 2026-05-18 (после Tier 0–2 closure):**
- Docker compose поднят: `credit-api` (8000), `credit-postgres` (5433), `credit-redis` (6379). Все healthy.
- Backend `APP_MODE=bank`, `BRAND_ID=default`, **`PII_ENC_KEYS` задан тестовым Fernet-ключом** (хранится в `/tmp/pii_key.txt` на dev-машине, prefix `iEuuP5WADM_sxwy7pgjU...`). БД сейчас зашифрована этим ключом. Без него — restore из `backup-pre-t13.sql` (pre-T1.3 plaintext snapshot, gitignored).
- Frontend Next dev (Turbopack) `npm run dev` в web/ — порт 3000.
- Seeded analyst для smoke: **email `t04@bank.uz`** / **password `T04Smoke!`**, без MFA. `full_name` хранится зашифрованным; API возвращает decrypted транспарентно.
- Существующих dossier'ов в БД: 48 (47 backfilled `BR-2026-0001..0047` + 1 smoke `BR-2026-0048`). Snapshot.payload + drafts.payload теперь зашифрованы JSONB wrap pattern.
- Папка `smoke-pdfs/` (в .gitignore) — три PDF сравнения ru/uz/nolang.
- Папка `backup-pre-t13.sql` (в .gitignore) — restore-точка pre-encryption snapshot, при потере PII_ENC_KEYS используется для recovery.

**Hotfix внутри сессии 2026-05-18:**
- `5eccce6` — T0.3 integration test auth contract (URL prefix `/api/auth/login` → `/api/bank/auth/login` + Authorization header instead of cookie). CI с T0.3 closure был красный 5 коммитов подряд.
- `5a873d0` — `httpx` в production deps (T0.2 regression: cbu_client делал `import httpx` на runtime, а dep лежал только в `[dependency-groups.dev]` → Docker `uv sync --no-dev` падал на ModuleNotFoundError при первом импорте). Pyproject + uv.lock обновлены.

---

## Pre-Demo Roadmap

> **Полный документ:** `docs/pre-demo-roadmap.md` (Tier-декомпозиция, acceptance, заблокированные, backlog).
> **Critical rule:** работаю ТОЛЬКО над активным Tier. Всё что не в Tier 0–4 — Frozen.

### Active — Tier 3 (Operational readiness)

**Tier 0 / Tier 1 / Tier 2 ✅ closed 2026-05-18.** Полная история закрытий — `docs/pre-demo-roadmap.md` + ADR-0014..0020. Sweep по deal-breakers / prod-killers / data-quality завершён.

**Tier 3 items (приоритезированный порядок):**
1. ~~**T3.2** Structured logging~~ ✅ **DONE 2026-05-18** — `correlation_id` через `setLogRecordFactory` + `RequestIDMiddleware` + `audit_log.request_id`. См. Current Status выше.
2. **T3.4** Postgres backup — `pg_dump` daily + retention 30d + restore drill, `docs/operations/db-backup.md`. **Deal-breaker** для on-prem demo. Dev = local volume + retention 7d, prod-playbook опишет A/B/C (local/NFS/S3-compat) — выбор банка при onboarding.
3. **T3.6** On-prem deploy — bundled tarball (`docker save | gzip` + install.sh + `db-init.sql.gz` + `.env.example`). **Deal-breaker** zero-internet install для узб mid-tier банков (internal registry mirror у них обычно нет). ADR-0021.
4. **T3.1** Observability — Sentry / GlitchTip on-prem (CA-064). Backend + frontend `error.tsx` hook. ADR-0022. Зависит от T3.2 (correlation_id для tags).
5. **T3.3** Prometheus `/metrics` + Grafana dashboard pack — latency p50/p99, error rate, PDF gen time, parser warnings rate. ADR-0023. Low demo-gating для mid-tier банков.
6. **T3.5** Audit log export — `GET /api/admin/audit-log/export?from=...&to=...` → CSV. Cheapest, no ADR, не блокирует.

Tier 4 (Compliance pack: pentest, аттестат УзСтандарта на ПДн, IT-Park резидентство, Admin Guide / Security Architecture / DRP/BCP) идёт **параллельно** Tier 3, начинается за 2 месяца до подачи в банк-tender.

**Lessons из закрытых Tier 0–2 (post-mortem):**
- Перед claim «X everywhere» обязательно `grep -rn` на hardcoded strings — `feedback_nested_anchor_rtl_blind` extends на shared-зону consumers.
- Pre-impl scope-review через grep на callers — `feedback_pre_impl_grep_all_callers`. План T1.1 underestimate'нул scope 10 → реально 22 файла.
- TDD-цикл поймал bug в `CaseIdAllocator`: `max_year=None` (пустая БД) не должен trigger'ить ALTER SEQUENCE RESTART. Без integration-теста выпустил бы 0001/0001/0001.
- ADR-0014 pattern переиспользован 3 раза (T0.2 CBU, T0.3 ГНК Phase A, sketch для T2.4b). ADR-0020 defer-decision принёс понимание fake-green risk без real-data.
- Vitest jsdom singleton — `fireEvent.click()` без `afterEach(cleanup)` ломает соседние файлы (`feedback_vitest_dom_leak_cleanup`).

<details>
<summary>Historical context (раскрыть при необходимости): T0.4 follow-up + T1.1 closure narrative</summary>

После закрытия T0.4 base scope (8 коммитов до `a7de8a3`) live-browser walkthrough на BR-EDFD (UZ-mode dossier UI + PDF) выявил, что **«UZ everywhere»** не достигнут — ADR-0015 покрыл PDF chrome + observations, но пропустил несколько кластеров hardcoded RU. Closer audit нашёл 5 багов:

**Уже закрыто follow-up'ом:**
- `0d29e58` — frontend `?lang=` forwarding из cookie `ca_locale` в SubHeader + BFF route.
- `8985ac3` — LocaleSwitcher в BankTopbar (был только в GlobalTopbar — bank-shell не покрывался).
- `8de5b95` — `/settings` «Язык интерфейса» row реагирует на `useLocale()` (был хардкод `t("locale_ru_full")`).
- `23fb311` — **B3 + B4** одним коммитом:
  - B3: `_resolve_okved(code, messages)` переключает на `short_uz/full_uz` для UZ-PDF. Catalog UZ-пары с CA-DS17 наконец используются.
  - B4 (scope расширен в pre-impl review): `formatBigUzs(amount, locale)` + `formatRevenueShort(decimalStr, locale)` required-param — UZ-суффиксы «mlrd / mln / ming soʻm» (U+02BB). Callers (kpi-row, revenue-24m-chart, result-card) читают `useLocale()`. Convention: **RU-числа + UZ-суффикс** (banking UZ habit, консистентно с pdf-i18n/uz.json). `uz.json spark_value_format` ASCII `'` → U+02BB ʻ.
  - Тесты: 3 pytest (pdf_renderer_okved_resolver_test, новый pure-Python без WeasyPrint) + 10 vitest (format.test.ts dossier, новый) + 4 vitest (format.test.ts search, extend).
  - **Heads-up CA-DS29-apostrophe**: grep по `web/src/i18n/uz.json` нашёл **340 occurrences** ASCII apostrophe в latin-узб словах (`bo'lmadi`, `noto'g'ri`, `ma'lumot`, …). Systemic orthographic regression на весь UZ-каталог. Требует отдельного коммита-fix (bulk sed `'` → `ʻ` с проверкой каждой строки на false-positive в RU/EN тексте). **Не входит в B4 scope.**
- `6db0061` — **B1** одним атомарным коммитом (~16 файлов):
  - `RuleSpecYaml.source_uz` required в YAML schema; `Rule.source_uz` + `RedFlag.source_uz` (soft default="" для test-fixtures); `registry_factory` пробрасывает.
  - **Snapshot persistence backward-compat**: `_red_flag_from_dict` fallback `d.get("source_uz", d["source"])` для старых JSONB-snapshot'ов без UZ-ключа — re-render досье на UZ покажет RU-cite (acceptable trade-off).
  - PDF renderer: `_build_red_flags_view` switch по `messages.locale`.
  - API: `RedFlagOutput.source_uz` + mapper fallback. Frontend: `RedFlagDto.source_uz`, SignalRow через `useLocale()` + safe fallback на пустую строку.
  - Tabular review закрыл compliance-конвенцию: 5/19 identical (ЦБ РУз, Базель III, Group-IB, supply-chain risk practice, AML compliance), 14/19 переведены (КОʻБ kreditlash standart amaliyoti, banklarning ichki uslublari, aylanmani sunʼiy oshirish итд).
  - Тесты: yaml_schema_test (новый), dossier_mapper_test extend (round-trip + fallback), pdf_renderer_red_flags_view_test (новый), risk-signals.test.tsx (новый, 3 кейса). **Lesson `feedback_vitest_dom_leak_cleanup`**: vitest jsdom singleton — `fireEvent.click()` без явного `afterEach(cleanup)` ломает другие тест-файлы (custom-dropdown.test failed pre-fix). testing-library auto-cleanup не покрывает все случаи в полной vitest run.
- `10e91c2` — **B2** одним атомарным коммитом (31 файл):
  - Strategy D (выбран в pre-impl review): `FiringEvidence.message_uz` + `RedFlag.message_uz` параллельно — симметрия с B1. Domain rule-функции формируют **обе** строки рядом через двойной f-string. Pure domain держит UZ-литералы (но это уже делается с RU — semantic-wise neutral).
  - 20 messages в 16 rule-функциях: 19 чистых добавлений + `LOW_MARGIN_HIGH_TURNOVER` с double `revenue_str_ru` / `revenue_str_uz` (RU числа + «mlrd soʻm» суффикс, консистентно с `formatBigUzs`/`formatRevenueShort`).
  - Snapshot persistence backward-compat (`message_uz` fallback to `message`), PDF `description` switch, API `RedFlagOutput.message_uz` с RU fallback, frontend SignalRow рендерит `messageText` через `useLocale()`.
  - Тесты: dossier_mapper_test extend (round-trip + B1+B2 dual fallback), pdf_renderer_red_flags_view_test extend (description picks по locale), risk-signals.test.tsx extend (message + source в одной локали + dual fallback на пустые UZ поля).
  - UZ-конвенция: QQS (НДС), EHF (ЭСФ), soʻm, tushum (выручка), foyda (прибыль), soliq (налог), kontragent. ОКВЭД сохранён кириллицей (banking convention), YoY оставлен EN (banking term).
  - **Hygiene**: `tax_penalties_current_year` вынесен `len(penalties)` в локальную `count` — line-length фикс после message_uz.

**Все B-следы закрыты ✅:**
- ~~B3 + B4 один коммит~~ ✅ `23fb311`.
- ~~B1 source_uz tabular~~ ✅ `6db0061`.
- ~~B2 RedFlag.message tabular~~ ✅ `10e91c2`.
- ~~CA-DS29-apostrophe bulk~~ ✅ `607d6ac` (355 ASCII `'` → U+02BB ʻ, 0 EN-contractions, JSON valid).

**Tier 0 follow-up complete.** Стек полностью UZ-локализован сквозь все слои (PDF, dossier UI, search UI, source/message rules, uz.json orthography). Tier 0 базовый scope тоже complete: T0.1 4-я фирма (ИНН 305738460, +5 файлов) на месте, formal acceptance 4×5=20 (по факту 28 включая q4 / monthly variations).

**T1.1 complete 2026-05-18.** Compromised B исполнен: `dossier_case_seq` Postgres sequence + `dossiers.case_id VARCHAR(20) UNIQUE NOT NULL` колонка + `CaseIdAllocator` с `pg_advisory_xact_lock(year)` + year-boundary RESTART. Backfill через `ROW_NUMBER() OVER (PARTITION BY year ORDER BY created_at, id)`. Drop'нули `_application_id` (dossier_mapper) + `_format_application_id` (pdf_renderer) — оба читают `view.case_id` напрямую. Frontend `formatCaseId` helper + test удалены; manual-input-view рендерит «—» pre-submit. Tests: 7 unit allocator + 4 integration (testcontainers) + 8 update'ов на новую `save(record, snapshot_id, case_id, ...)` сигнатуру. Lessons: (1) pre-impl grep на `DossierViewRecord(...)` callers поймал бы +4 не-в-плане файла раньше — план underestimate'нул scope ~10 → реально ~22 файла. (2) TDD-цикл поймал bug в allocator: `max_year=None` (пустая БД) не должен trigger'ить ALTER SEQUENCE RESTART — только реальный year shift. Без integration-теста с двумя последовательными allocate выпустил бы 0001/0001/0001.

**Lessons:**
- Перед мержем claim «X everywhere» обязательно `grep -rn` на hardcoded strings того класса, который локализуется. Я провалил это 3 раза (T0.4 base, LocaleSwitcher в BankTopbar, locale_full в Settings) — паттерн `feedback_nested_anchor_rtl_blind` extends: RTL/jsdom не ловит «забыл прокинуть» в shared-зоне consumers.
- Memory `feedback_dont_pause_between_commits.md` + `feedback_nbsp_write_loses_literal.md` добавлены 2026-05-18.
- Pre-impl scope-review B4 (2026-05-18): описание в CLAUDE.md ловило только namesake `formatBigUzs`, но live-browser в UZ-mode `/search` дал бы тот же gap через `formatRevenueShort`. Расширение scope **до** коммита спасло 4-й T0.4 hotfix. Lesson: «один namesake = один сценарий» — ложная конвенция; искать **все** формат-хелперы той же семантики.

</details>

### Tier 0 — Deal-breakers (closed)
- ~~**T0.1**~~ → **DONE 2026-05-18**: 4 фирмы (201308534, 305002665, 308747266, 305738460) × 5 типов = formal набор, 28 xltx по факту в `tests/fixtures/soliq_xltx/` (включая q4 + monthly). Gitignored. Анонимизированные версии — **CA-DS30** в backlog (только 1/28 anon на месте; bulk anonymize через openpyxl script — post-T1 priority).
- ~~**T0.2** CBU API real integration (CA-024b)~~ → **DONE 2026-05-17 (commit `b124af6`)**: cbu_client + usd_rate_service + usd_rate_repository (Postgres daily-cached) + endpoint switch. Fallback chain env → DB today → CBU live → DB latest → JSON. ADR-0014 «External API integration pattern». Live smoke ✓.
- ~~**T0.3** ГНК Phase A: manual upload справок (CA-003 Phase A)~~ → **DONE 2026-05-18**: backend `53ac8fe` (domain + migration + repo + service + 3 endpoints + snapshot round-trip), T0.3.1 `feabb3a` (wizard upload UI + 4 RTL), T0.3.2 `9cb20a6` (display в досье pill + PDF row + 3 RTL). ADR-0014 pattern переиспользован. Phase B (CA-DS28 public lookup) — после legal-clearance.
- ~~**T0.4** UZ-локализация PDF (CA-DS29-pdf)~~ → **DONE 2026-05-18**: 8 коммитов от `ce2c47a` (ADR-0015) до `a7de8a3` (endpoint `?lang=`). Backend single source of truth — `config/pdf-i18n/{ru,uz}.json` через `PdfMessages` DTO + `infrastructure/i18n/pdf_messages.py` loader с `lru_cache(maxsize=2)`. `Rule.name_uz` required в YAML schema; 19 правил переведены. `RenderDossierPdf.execute(dossier_id, lang)`, observations_builder f-strings → `messages.X.format(...)`, dossier.html / pdf_renderer.py / template_filters.py / chart_renderer.py wiring через DI. Endpoint `GET /api/dossier/{id}/pdf?lang=ru|uz` + `BrandConfig.default_lang` fallback + audit-log `payload={"lang": ...}`. ADR-0015 «PDF localization strategy».
- ~~**T0.5** VAT parser fix для real 10006_41/45/47 (промоут из CA-015)~~ → **DONE 2026-05-17 (commit `f5d7495`)**: NKM rows, trailing-empty stop, v1/v2 header dispatch. 19 real-xltx pass + 4 profit_tax xfail.

**Tier 0 closed.** См. roadmap для полного списка commits.

### Tier 1–4 status (snapshot 2026-05-18)
- ~~**T1** Prod-killers~~ ✅ done 2026-05-18 (T1.1 case_id seq · T1.2 refresh rotation · T1.3 PII encryption · T1.4 multi-tenant · T1.5 LDAP). ADR-0016/0017/0018/0019.
- ~~**T2** Data quality~~ ✅ done 2026-05-18 (T2.1 dynamic units FORM_2+FORM_1 · T2.2 поглощено T0.5 · T2.3 PROFIT_TAX · T2.4 faktura.uz honest stub). ADR-0020.
- **T3** Operational readiness — **Active.** Observability (CA-064), structured logging + correlation_id, Prometheus/Grafana, pg_dump backup, audit-log export, Ansible/systemd deploy. 6 items, приоритизация в начале новой сессии.
- **T4** Compliance pack (параллельно с T3): pentest от лицензированной узб-лаборатории, аттестат УзСтандарта на ПДн, резидентство в IT-юрисдикции РУз, Admin Guide + Security Architecture + DRP/BCP (RU + UZ).

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
