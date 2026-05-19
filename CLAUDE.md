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
- **ADR-0024 research closure** (2026-05-19): 3-way reconcile Claude / ChatGPT / Qwen — 9 правил с подложными источниками заменены (ЦБ РУз №2696, НК РУз ст.47+257+489, FATF/EAG/ЗРУ-660); confidence layer заменил `INSUFFICIENT_DATA` (BR-2026-0050 TEST bug); OKED-UZ benchmark catalog; 3 новых правил (FX_MISMATCH_HIGH / DSCR_LOW / WC_INSUFFICIENT) + supporting data structures (BalanceSnapshot +current_assets/current_liabilities, FinancialReport +D&A/OCF); 7 правил с threshold-only adjustments per Q0.B. Research outputs: `docs/research/2026-05-19-3way-reconcile/`. Архитектурно тяжёлые правки (OKVED→ОКЭД rename, dual-severity, новые Counterparty/LoanRequest fields, stat.uz industry medians) — backlog в ADR-0024. **Session 1 (2026-05-19) closed**: 6 KPI (`ebitda` / `debt_to_ebitda` / `current_ratio` / `working_capital` / `interest_coverage` / `dscr`) end-to-end в calculator + PDF + UI. **Session 2 (2026-05-19) closed** (PR #10 + hotfixes `b986c4a` / `4878258`): `quick_ratio` KPI (acid-test ratio, IFC SME ch.4); 2 новых правила — `OFF_BALANCE_COMMITMENTS` high (BCBS d424 §50) и `CASH_FLOW_QUALITY` medium (IFC SME ch.4 + Beneish M-score 1999 + Healy & Wahlen JIFM 1999), rule count **22 → 24**; `BalanceSnapshot.inventory` + `FinancialReport.{guarantees,leases,letters_of_credit}_outstanding` (4 nullable JSONB-поля, без Alembic — Session 1 convention); UI/PDF align — пустые KPI cards скрыты в обоих рендерингах (banker-clean). Flaky `custom-dropdown.test.tsx` побеждён (macrotask race в test, не DOM-leak; fix через `await waitFor()` wrap). **Session 3 (2026-05-20) closed** (PR #11 → main `42b116b`): infrastructure `FiringEvidence.severity` override + `Rule.run_all` fallback (одна точка для conditional-severity без `severity_fn`); 5 rule narrows — `TAX_PENALTIES_CURRENT_YEAR` material filter (ст.223 НК vs ст.219 КоАО), `SHELL_COMPANY_PARTNERS` IE exclusion, `SINGLE_SUPPLIER_CONCENTRATION` foreign-escalation (>0.50 + foreign = HIGH через override), `OKVED_CHANGED_12M` owner-gate (`oked_changed_by_owner` flag), `LOAN_TO_REVENUE_RATIO` secured-variant (0.40 unsecured / 0.70 secured); 5 entity полей — `TaxEvent.material` / `Counterparty.opf` / `Counterparty.is_foreign` / `Borrower.oked_changed_by_owner` / `LoanRequest.collateral_type`; 1 Alembic migration `c5e9d2a7b1f4` (только Borrower SQL-persisted, остальные 4 — JSONB через `.get(..., default)`); UI Step 1 conditional toggle (parser-driven `okvedMainChangedAt`) + Step 3 collateral pills (counter 5/5→6/6); rule count **24** (без изменений), KPI count **7** (без изменений). Regression invariant подтверждён через `scripts/verify_adr0024_baseline.py` cross-branch replay diff — Session 3 narrows silent на default-False/None полях. **Session 3 lesson**: pre-impl grep на `rule_id` + entity field names обязателен — CI hotfix `bb484c4` поймал 5 hardcoded fixtures в `tests/fixtures/synthetic_borrowers.py` + `src/interfaces/api/shared/dossier_test.py`. **Day 4 closed (2026-05-20)** (PR #14 → `c2c6f4e` + PR #13 → `7f88656` + PR #12 → `2be6ea2`, параллельные ветки A/B/C через worktrees): **A (PR #14, atomic 81 файл)** — OKVED → ОКЭД rename per ПКМ РУз №275 от 24.08.2016: `Borrower.okved_main` → `oked_main`, `okvedMain` → `okedMain` в Pydantic/Zod/UI/i18n/PDF, Alembic `b04677374b85` (head, single `ALTER COLUMN`, round-trip DOWN/UP smoke ✓ на 49 dossiers). Mixed-prefix Session 3 (`oked_changed_by_owner` + `okved_main_changed_at`) удалён — теперь сквозной `oked_*`. **B (PR #13, 7 коммитов)** — `fx_exposure_ratio` 8-й KPI: `BalanceSnapshot.liabilities_fx: Money | None` (Option D — поле в существующем snapshot, не новая entity Liability с currency breakdown), формула `liabilities_fx / liabilities × 100`. Banker вводит вручную в wizard Шаг 2; парсер FORM_1 не извлекает на v1. **БЕЗ level_tone в v1** — пороги отложены до verified § ЦБ РУз для FX-mismatch (см. CA-070). End-to-end: kpi_calculator + KpiBundle + Pydantic + UI (Шаг 2 + dossier kpi-row) + PDF slot. JSONB round-trip покрыт через `_balance_snapshot_to_dict`/`_from_dict` `.get()` backward-compat. **C (PR #12, 2 коммита)** — `CIRCULAR_INVOICING` graph cycle detection через `networkx>=3.4`: `_build_graph(snapshot) → DiGraph` (SELLER edge borrower→CP, BUYER edge CP→borrower), `networkx.simple_cycles()` для full 3+ node detection, материальный порог 100 млн UZS на сумму invoices в цикле + 90-day window. `FiringEvidence.severity` override CRITICAL для cycle.length≥3 (Session 3 pattern), 2-cycle сохраняет default high из YAML. Backward-compat: `BorrowerSnapshot.invoices` хранит только наши ЭСФ → max cycle = 2 на текущих данных (3+ cycle activate'ся когда появится cross-CP ESF source — backlog CA-002b). 7 existing test'ов зелёные без правок + 2 новых (3-node через monkeypatch, 2-cycle severity fallback). Rule count **24** (без изменений), KPI count **7 → 8**, regression baseline (5 demo dossiers BR-2026-0030/0040/0042/0046/0047) — empty diff. **Day 4 merge protocol**: parallel worktrees A/B/C → A merged первой (largest scope, low cross-conflict risk) → B+C rebase'нуты на свежий main → оба CI зелёные после rebase → merged sequentially. Concurrency-cancel quirk на main CI run `26124961854` (#13 merge cancelled 18s после #12 push — by-design `concurrency.cancel-in-progress`, финальный state верифицирован run `26124978000` ✓ success на `2be6ea2`).

### Stack state (2026-05-20)

- Docker compose поднят: `credit-api` (8000), `credit-postgres` (5433), `credit-redis` (6379) — все healthy. Сегодня smoke'нул `credit-db-backup` sidecar (backup + restore_drill PASS exit=0).
- Backend env: `APP_MODE=bank`, `BRAND_ID=default`, `PII_ENC_KEYS` задан тестовым Fernet-ключом (`/tmp/pii_key.txt`, prefix `iEuuP5WADM_...`). БД зашифрована — без ключа restore из `backup-pre-t13.sql` (gitignored).
- Frontend Next dev (Turbopack) `npm run dev` в `web/` — порт 3000. После T3.6.1 production-image тоже билдится.
- Seeded analyst для smoke: **email `t04@bank.uz`** / **password `T04Smoke!`**, без MFA.
- Dossiers в БД: 49 (47 backfilled `BR-2026-0001..0047` + smoke `BR-2026-0048..0049`). Snapshot.payload + drafts.payload зашифрованы. Demo scenarios используют `BR-2026-0030/0040/0042/0046/0047` (см. `docs/demo/scenarios.md`).
- Backups: `./backups/` (gitignored) — 2 dump'а после T3.4 smoke.
- ADR-0024 Session 1 (2026-05-19): 6 новых KPI в `src/application/services/kpi_calculator.py` (`ebitda`, `debt_to_ebitda`, `current_ratio`, `working_capital`, `interest_coverage`, `dscr`) — end-to-end через PDF (`config/pdf-i18n/{ru,uz}.json` + `dossier.html`) и UI (`web/src/features/dossier/kpi-row.tsx`). T4 compliance skeleton доставлен (`docs/compliance/{admin-guide,security-architecture,drp-bcp}.md`, 1007 строк bilingual, UZ-блоки помечены `TODO[CA-T4-UZ]`). CA-DS30 закрыт — 27 anonymized xltx fixtures + `scripts/anonymize_xltx.py` + 6 unit-тестов. Pre-demo smoke playbook расширен (8×3 matrix + 4 пути 2FA + 8 edge UX + sign-off table); журнал прогонов — `docs/operations/pre-demo-smoke-history.md`.
- ADR-0024 Session 2 (2026-05-19, PR #10 → main `4878258`): 7-й KPI `quick_ratio` end-to-end (calculator + `KpiBundle` DTO + Pydantic `KpiBundleOutput` + UI `kpi-row.tsx` + PDF `_build_kpi_slots`). Rule count **24** (`config/rules/v1_uz_msb.yaml`) — `OFF_BALANCE_COMMITMENTS` high и `CASH_FLOW_QUALITY` medium. 4 новых persisted поля по JSONB-pattern (Session 1 convention, без Alembic): `BalanceSnapshot.inventory` имеет UI input в Step 2 «Запасы (TMZ)» + Pydantic + dossier_mapper; `FinancialReport.{guarantees_outstanding, leases_outstanding, letters_of_credit_outstanding}` — JSONB-only (без UI / Pydantic, заполняются через test fixtures или future FORM_1 parser). UI/PDF align: пустые KPI cards (`value=None`) фильтруются перед render в обоих местах. `tests/fixtures/regression/adr0024_baseline.json` неизменён — новые правила silent на existing 49 dossiers (нет off-balance / OCF полей в payloads до Session 2).
- ADR-0024 Session 3 (2026-05-20, PR #11 → main `42b116b`): rule infrastructure расширена — `FiringEvidence.severity: FlagSeverity | None = None` опциональный override, `RuleRegistry.run_all` fallback на `rule.severity` если override = None. 5 rule narrows + 5 новых entity полей: `TaxEvent.material` (Pydantic + dossier_mapper, JSONB), `Counterparty.{opf, is_foreign}` (Pydantic + dossier_mapper, JSONB), `Borrower.oked_changed_by_owner` (**1 Alembic migration `c5e9d2a7b1f4`** — Borrower единственный SQL-persisted, + Pydantic + dossier_mapper + ORM mapper + UI Step 1 conditional toggle), `LoanRequest.collateral_type` (Pydantic + dossier_mapper, JSONB + UI Step 3 collateral pills, counter 5/5→6/6). UI prefill через `rememberStep1Prefill` расширен `okved_main_changed_at` + `oked_changed_by_owner` для conditional rendering. `scripts/verify_adr0024_baseline.py` — cross-branch regression verify (pre vs post replay JSON diff). Rule count **24** (без изменений), KPI count **7** (без изменений), regression baseline неизменён (Session 3 narrows silent на default-False/None полях).
- ADR-0024 Day 4 (2026-05-20, PR #14 + #13 + #12 → main `2be6ea2`): три параллельные ветки через worktrees. **A**: OKVED → ОКЭД atomic rename 81 файл — `Borrower.oked_main` (был `okved_main`), Pydantic/Zod/UI поля `okedMain`, PDF `oked_label`, i18n keys, **Alembic head `b04677374b85`** (single `ALTER COLUMN borrowers.okved_main RENAME TO oked_main`, round-trip DOWN/UP smoke ✓). Session 3 mixed-prefix gotcha (`oked_changed_by_owner` + `okved_main_changed_at`) удалён → сквозной `oked_*`. **B**: 8-й KPI `fx_exposure_ratio = liabilities_fx / liabilities × 100` (PCT). `BalanceSnapshot.liabilities_fx: Money | None` (Option D — поле в существующем snapshot, не новая Liability entity с FK currency). Banker вводит вручную в wizard Шаг 2 «Валютные обязательства»; парсер FORM_1 не извлекает. **КPI без level_tone в v1** (CA-070) — пороги отложены до verified § ЦБ РУз для FX-mismatch у МСБ. JSONB round-trip backward-compat. **C**: `CIRCULAR_INVOICING` graph cycle detection — replace 2-node defaultdict-heuristic на `networkx.simple_cycles()` (3+ node ready). Новая deps **`networkx>=3.4`** в `pyproject.toml` + mypy override. `FiringEvidence.severity` override CRITICAL для cycle.length≥3 (Session 3 pattern); 2-cycle сохраняет default high из YAML. Backward-compat: текущие данные (только наши ЭСФ) → max cycle = 2; 3+ activate'ся когда появится cross-CP ESF source (CA-002b). Rule count **24** (без изменений), KPI count **7 → 8**. Regression baseline (5 demo dossiers) empty diff ✓.

### Active focus — выбор следующего шага

Pre-demo MVP ready. **ADR-0024 Day 4 closed (2026-05-20, PR #14 + #13 + #12 → main `2be6ea2`)** —
OKVED→ОКЭД atomic rename (Alembic `b04677374b85`), 8-й KPI `fx_exposure_ratio`
(без level_tone v1), `CIRCULAR_INVOICING` via networkx (3+ node ready, дёргается
когда придёт cross-CP ESF source). KPI count 7 → 8, rule count 24 (без изменений).
Готов к Day 5 — Pre-demo smoke walkthrough перед pilot trip.

**ADR-0024 research closure history**: 3-way reconcile (Claude / ChatGPT /
Qwen) → 6 атомарных коммитов foundational sources + confidence layer +
OKED-UZ catalog + FX/DSCR/WC rules + Q0.B thresholds. Session 1 — 6 KPI
end-to-end. Session 2 — `quick_ratio` + 2 правила + 4 JSONB поля.
Session 3 — 5 rule narrows + 5 entity полей + severity_override
infrastructure. Day 4 — OKVED→ОКЭД rename (Tier 3 closed) + fx_exposure_ratio
8-й KPI + CIRCULAR networkx (CA-002 closed). Подробности
`docs/adr/0024-foundational-source-verification.md` + research outputs
`docs/research/2026-05-19-3way-reconcile/`.

Открытые направления (НЕ блокеры, dispatch по сигналу):

1. **T4 compliance pack**: skeleton доставлен (`docs/compliance/{admin-guide,security-architecture,drp-bcp}.md`, 1007 строк bilingual RU+UZ). Открыто: UZ-перевод (грепай `TODO[CA-T4-UZ]`) — нужен носитель / compliance-эксперт; pentest узб-лаборатории; аттестат УзСтандарта на ПДн (Закон РУз №547); IT-Park / Uzinfocom резидентство. Старт за 2 мес до bank tender.
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
5. **ADR-0024 backlog** (требуют расширения domain entities / новых каталогов / pilot-bank signal — см. ADR-0024 «Research debt remaining»):
   - **`fx_exposure_ratio` thresholds (CA-070)**: KPI рендерится value-only (level_tone=None) в v1 — без light-up. Pre-condition: verified § ЦБ РУз для FX-mismatch у МСБ. Candidates по research outputs (`docs/research/2026-05-19-3way-reconcile/`): conservative 0.25 medium / 0.50 high или lenient 0.40 / 0.70 — финальный выбор требует уточнения у пилот-банка / official ЦБ doc. Threshold добавляется через separate commit (см. CA-070 convention).
   - **CA-002b CIRCULAR external_invoices**: текущий граф строится только из наших ЭСФ (`BorrowerSnapshot.invoices`), все edges проходят через borrower → max cycle = 2. Detection 3+ node активируется только когда появится cross-CP ESF source (Soliq ESF group API или pilot-bank cross-borrower invoice feed). Hook готов в `_build_graph` — добавить external invoices в DiGraph поверх borrower-anchored edges. ~50 LOC + 5 интегр-тестов на реальных 3-node циклах.
   - **OKVED → ОКЭД Tier 4 catalog rename**: `config/catalog/okved.json` → `oked.json`, `config/benchmarks/oked-uz.json` keys, frontend OkvedAutocomplete component naming, `GET /api/system/okved` endpoint → `/oked`. ~12-15 файлов. Pre-condition: pilot-bank приоритет (UX не блокер для аналитика — labels всё ещё «ОКЭД» в i18n).
   - **OFF_BALANCE manual-input UI wiring**: 3 поля (`guarantees/leases/letters_of_credit_outstanding`) есть в `FinancialReport`, JSONB round-trip покрыт. Не в Pydantic `FinancialReportInput`, `dossier_mapper`, wizard Step 2. Pre-condition: пилот-банк подтверждает значимость 3 off-balance компонентов.
   - **OKVED_CHANGED_12M brand-new dossier flow**: Session 3 закрыла owner-gate, но UI toggle reachable только во flow «Пересобрать с дополнениями» (требует parser-given `oked_main_changed_at`). Brand-new dossier flow покроет Госкомстат ОКЭД-API integration.
   - **OKVED_CHANGED_12M dual-severity** (опционально): через `severity_override` pattern (Session 3 infrastructure) можно дать `low` для Госкомстат auto-overwrite и `medium` для owner-initiated. Сейчас binary gate — Госкомстат silent.
   - **SINGLE_BUYER_CONCENTRATION dual-severity** (0.50 medium / 0.70 high) — теперь применим `FiringEvidence.severity` override (Session 3 infrastructure), без split в 2 правила или `severity_fn`. ~30 LOC изменение.
   - **LOW_MARGIN_HIGH_TURNOVER vs industry_median**: stat.uz net-margin catalog по ОКЭД. Текущий `config/benchmarks/oked-uz.json` все 7 buckets с null.
6. **Active code-level TODOs** (`grep TODO\\[CA- src/ web/src/`):
   - **CA-001** ИНН checksum по ГНК-алгоритму (`src/domain/value_objects/inn.py`).
   - **CA-002b** CIRCULAR external_invoices — graph детекция 3+ node циклов через cross-CP ESF feed. CA-002 закрыт Day 4 (networkx-based detection развёрнут, но текущие данные только наши ЭСФ → max cycle = 2 на практике; 3+ activate'ся когда придёт external invoice source).
   - **CA-003** Real ГНК lookup — pre-condition: legal review (см. также CA-DS28).
   - **CA-019** Access-token denylist для force-logout (formally T1.2 закрыта только refresh-rotation; access ttl 15м истекает сам).
   - **CA-031** Source-trail invasive refactor — `applyToForm` все ячейки формы (UX nice-to-have).
   - **CA-DS19** Pulse-dot motion cleanup в DSCR-summary (UI polish, frozen pre-demo).
   - **CA-DS25** KPI sparkline — pre-condition: monthly_turnover≥12 источник (VAT_DECL monthly chain или ESF). Не PROFIT_TAX (annual).
   - **CA-DS28** ГНК public lookup на soliq.uz/services/search/ — pre-condition: legal review.

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
- **ADR-0024 data structures**: `BalanceSnapshot` расширен полями `current_assets` / `current_liabilities` (Money | None) — компоненты Current Ratio для WC_INSUFFICIENT. `FinancialReport` расширен полями `depreciation_amortization` / `operating_cash_flow` (Money | None) — D&A для EBITDA-числителя DSCR_LOW (CA-037 анонс выполнен), OCF для proper DSCR per Murodov 2025. Snapshot_mapper round-trip покрывает оба расширения; legacy payloads (до ADR-0024) грузятся через `.get()` без миграции. Парсеры FORM_1 пока не извлекают новые поля — заполняются вручную через manual-input.
- **ADR-0024 Session 2 data structures**: `BalanceSnapshot.inventory: Money | None` — компонент Quick Ratio = (CA − inventory) / CL (IFC SME ch.4). `FinancialReport.{guarantees_outstanding, leases_outstanding, letters_of_credit_outstanding}: Money | None` — off-balance commitments для правила `OFF_BALANCE_COMMITMENTS` (BCBS d424 §50). Все 4 nullable, JSONB round-trip через `.get()` backward-compat. **`inventory` — единственное из 4 в Pydantic + UI** (Step 2 Balance group, форм-поле `inventoryEnd25`); три off-balance поля JSONB-only (test fixtures / future FORM_1 parser extension, в Pydantic / dossier_mapper / wizard не пробрасываются).
- **ADR-0024 Session 3 data structures**: `TaxEvent.material: bool = False` (ст.223 НК vs ст.219 КоАО — фильтр для TAX_PENALTIES_CURRENT_YEAR). `Counterparty.opf: LegalForm | None = None` (ИП исключаются из SHELL_COMPANY_PARTNERS). `Counterparty.is_foreign: bool = False` (foreign supplier escalation для SINGLE_SUPPLIER до HIGH). `Borrower.oked_changed_by_owner: bool = False` (gate для OKVED_CHANGED_12M — единственное SQL-persisted поле Session 3, Alembic `c5e9d2a7b1f4`, остальные 4 JSONB). `LoanRequest.collateral_type: CollateralType | None = None` (secured-variant порог 0.70 для LOAN_TO_REVENUE). Все 5 default-False/None → backward-compat: 49 existing dossiers и legacy payloads загружаются с пустыми значениями, narrows silent.
- **ADR-0024 Day 4 data structures**: `BalanceSnapshot.liabilities_fx: Money | None = None` (Session 4 поле, CA-037 JSONB pattern) — FX-компонент total liabilities для KPI `fx_exposure_ratio`. Banker вводит вручную в wizard Шаг 2 «Валютные обязательства»; парсер FORM_1 не извлекает на v1. Currency invariant snapshot'а (все Money в одной валюте) сохранён — `liabilities_fx ≤ liabilities`, banker отвечает за корректность. Round-trip через `_balance_snapshot_to_dict`/`_from_dict` `.get()` — legacy 49 dossiers загружаются с `liabilities_fx=None`, KPI silent (см. silent contract в `kpi_calculator.fx_exposure_ratio`). **OKVED → ОКЭД atomic rename**: Day 4 ветка A сделала сквозной `oked_*` префикс по всему стеку (`Borrower.oked_main`, Pydantic `okedMain`, UI `okedMain`, i18n keys, PDF `oked_label`). Alembic `b04677374b85` — single `ALTER COLUMN borrowers.okved_main RENAME TO oked_main` (round-trip DOWN/UP smoke ✓). Session 3 mixed-prefix gotcha закрыт.
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
- **CA-067** KPI hide-empty (ADR-0024 Session 2): пустые KPI cards (`value=None`) скрываются и в UI (`kpi-row.tsx` — slot returns null), и в PDF (`_build_kpi_slots` filter `s["value"] is not None`). Banker-clean default. **Exception**: `NoDebtCard` (Decimal(0)) и `DebtToEbitSlot` Case 3 «убыток скрывает оценку» — это самостоятельные финансовые сигналы, не пустота — остаются видимыми. Аналитик видит «нет данных» в manual-input wizard, не в готовом досье.
- **CA-068** Partial-data rules (ADR-0024 Session 2): правило `OFF_BALANCE_COMMITMENTS` суммирует 3 поля как «None → 0», если хотя бы одно не None. Silent только если все 3 None. Banker видит сигнал даже при неполной off-balance выгрузке (worst-case-known оценка). `CASH_FLOW_QUALITY` silent если OCF None или net_profit ≤ 0 (последнее ловит `NEGATIVE_PROFIT_3Q`).
- **CA-069** Dual-severity через `FiringEvidence.severity` override (ADR-0024 Session 3): когда правило fires с conditional severity (зависит от runtime-данных, не от YAML), возвращай `FiringEvidence(..., severity=FlagSeverity.HIGH)` поверх default `severity` из YAML — `RuleRegistry.run_all` fallback'ит на `rule.severity` если override = None. **Не плодить дубль-правила** (например, SUPPLIER_CONC_FOREIGN_HIGH + SUPPLIER_CONC_GENERIC_MEDIUM) и не вводить `severity_fn` в RuleSpec — достаточно `severity_override` на per-evidence уровне. Применено в `SINGLE_SUPPLIER_CONCENTRATION` (foreign + >0.50 = HIGH; >0.60 = MEDIUM из YAML), `CIRCULAR_INVOICING` (cycle.length≥3 → CRITICAL поверх YAML high). Backlog candidates: `SINGLE_BUYER_CONCENTRATION` (0.50 medium / 0.70 high), `OKVED_CHANGED_12M` (Госкомстат low / owner medium).
- **CA-070** KPI без `level_tone` v1 pattern (ADR-0024 Day 4): когда threshold не имеет verified источника (officially-cited § ЦБ РУз / IFC / Basel / Murodov 2025 и т.д.), KPI рендерится как value-only — `level_tone=None` в `KpiBundle` field, UI показывает число без light-up (нейтральный), PDF — без цветовой подсветки. Banker reads число, applies professional judgment. **Threshold добавляется через separate commit когда найден verified §** — не повторяем урок Qwen industry medians с фабрикованными цифрами (research closure 2026-05-19). Применено в `fx_exposure_ratio` (Day 4, B) — пороги отложены до verified § ЦБ РУз для FX-mismatch у МСБ. Принцип: «честный value лучше выдуманного threshold».

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
2. **`ruff check` + `mypy --strict` + `pytest`** обязательны перед push. **`pytest src/ tests/` — оба обязательны** (`src/` co-located unit-тесты + `tests/` integration / e2e). Минимум: `docker compose exec -T api bash -c "cd /app && uv run python -m ruff check . && uv run python -m mypy --strict src tests && uv run python -m pytest"`. Memory `feedback_pytest_tests_dir_in_prepush.md` — пропуск `tests/` ловит на CI red push.
3. **Меняешь computed-from-X invariant — `grep -r` все тесты на эту semantic.** Локальный mapper-test может пропустить интеграционный тест.
4. **Меняешь rule registry / rule count** — `grep -rn "== <old_count>\|== <new_count>" tests/ src/` обязателен (Session 2 lesson: 4 hardcoded assertions проворонились, CI 3× красный до hotfix).
5. **CI коммита перед твоим зелёный?** `gh run list --branch main -L 3` перед началом работы.

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
- **Pre-demo smoke history журнал** — `docs/operations/pre-demo-smoke-history.md` (вести запись каждого прогона перед demo trip).
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
- `docs/adr/` — Architecture Decision Records (0001..0024)
- `docs/compliance/` — T4 артефакты (Admin Guide, Security Architecture, DRP/BCP) для bank tender pack
- `docs/research/2026-05-19-3way-reconcile/` — Claude / ChatGPT / Qwen research outputs за ADR-0024
