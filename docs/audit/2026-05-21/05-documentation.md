# Documentation accuracy audit — credit-assistant 2026-05-21

## Executive summary

Project-level docs (`CLAUDE.md`, ADRs, `active-contracts.md`, operations
playbooks, `session-log.md`) are in **strong sync with code** — sampled
4 ADRs and 5 CA-XXX contracts and code matches description in every case;
all sampled commit hashes and PR numbers resolve cleanly. **Three drift
sites** found: root `README.md` is frozen at Phase 1 (still claims "17
red-flag правил"; реально 24), `CLAUDE.md` "Dossiers: 49 (BR-2026-0001..0049)"
counter is stale (DB now holds 52, BR-2026-0001..0052), and `web/README.md`
is unmodified create-next-app boilerplate. **One serious fabricated
citation** survives in `docs/compliance/security-architecture.md` (line 244
+ 341): refers to «Постановление №27-п» which ADR-0024 explicitly proved
non-existent — same citation was stripped from rule YAML but missed in
compliance pack.

## Documentation score: 7.5/10

Justification: high-quality internal docs (session-log, ADRs, active-contracts,
operations playbooks) — all checked items resolve. Stack metadata in
CLAUDE.md mostly accurate (Alembic head exact, rule count exact, KPI list
exact, PR references all merged). Public-facing README and compliance pack
are the weak surface: README hasn't been touched since Phase 1, and the
compliance pack still cites the fabricated regulation that ADR-0024 dedicated
itself to removing. Without the README and the №27-п drift in compliance,
this would be 9/10.

## Major drift (docs lie about code)

- `README.md:7` — claims "Phase 1 — Domain Core: complete. **17 red-flag
  правил**, ... Coverage `src/domain/rules` ≈ 99%, 217 unit + integration
  тестов." Actual rule count: **24** (verified `config/rules/v1_uz_msb.yaml`
  via `grep -cE "^\s+- id:" → 24`). README has not been updated since
  ADR-0024 (S1/S2/S3 added 5 rules; total 19→24).

- `README.md:83` — Documentation section: "`config/rules/v1_uz_msb.yaml` —
  все **17** red-flag правил с metadata". Same drift.

- `README.md:9` — "Phase 0 — Foundation: complete." Doc is frozen at end
  of Phase 1 — no mention of Phase 2 / Bank Mode (Phase 4) / Tier 0-3 /
  Pre-Demo MVP / ADR-0024. CLAUDE.md says current status is "Pre-demo MVP
  ready (closed 2026-05-18, Tiers 0/1/2/3 complete)".

- `docs/compliance/security-architecture.md:244` —
  "Постановление №27-п (методики кредитного риск-анализа) — реализовано
  через rules engine v1". This regulation **does not exist** —
  `docs/adr/0024-foundational-source-verification.md:29` documents
  "«ЦБ РУз №27-п» — НЕ СУЩЕСТВУЕТ" and lists it as a fabricated source
  that was scrubbed from all 3 rules (`REVENUE_DROP_MOM_30`,
  `REVENUE_DROP_YOY_50`, `NEGATIVE_PROFIT_3Q`). Compliance pack still
  cites the fictional regulation as proof of CBU compliance — exactly
  the «подложная цитата на demo подорвёт trust банкира» risk that
  ADR-0024 sought to remove.

- `docs/compliance/security-architecture.md:341` (UZ block) —
  same drift: "MB RUz №27-p va №2696 nizomlari." Two-language
  drift, scrub it in both.

## Minor drift (likely staleness)

- `CLAUDE.md:46` — "Dossiers: 49 (47 backfilled `BR-2026-0001..0047` +
  smoke `BR-2026-0048..0049`)". Actual DB state (verified via `SELECT
  COUNT(*), MIN, MAX FROM dossiers`): **52 rows, BR-2026-0001..0052**.
  Three new dossiers (0050..0052) since the doc was last refreshed.

- `docs/operations/pre-demo-smoke.md:57` — Acceptance matrix expects
  "48 dossiers" on `/history`. Actual is 52. Smoke playbook tester will
  see 52 and either over-correct or treat the discrepancy as noise.

- `docs/conventions/active-contracts.md:38` — "JWT (Phase 4.B): native
  bcrypt, HS256, access 15м + refresh 7д **без ротации в v1**". Refresh
  rotation was actually implemented as T1.2 per ADR-0016 (and is
  correctly described in line 40 right below it). Line 38 still says
  "без ротации в v1" — stale half-sentence.

- `web/README.md` (entire file, 37 lines) — unmodified create-next-app
  boilerplate. Mentions "Vercel Platform" deployment for an on-prem
  banking app. References `app/page.tsx` (no longer the entry point —
  App Router with `(bank)` / `(accountant)` route groups now). Zero
  project-specific content.

- `docs/adr/0005-drafts-auth-by-uuid.md:51-58` — "Phase 4 plan" promises
  to add `drafts.owner_user_id UUID NOT NULL` when Bank Mode arrives.
  Bank Mode is live (Phase 4 closed 2026-05-11 per session-log), but
  `drafts` table still has no owner column (verified `\d drafts` →
  only `id/payload/created_at/updated_at/expires_at`). ADR is not
  marked Superseded or Updated — reader of the ADR will expect the
  schema change that never happened.

## Stale references (file/symbol mentioned no longer exists or never did)

- `README.md` references "Phase 1" status, "Phase 0 complete", "Phase 2.5"
  era language — Phase nomenclature shifted to Tier 0/1/2/3 in Pre-Demo
  roadmap.

- `docs/compliance/security-architecture.md` (line 244, 341) — Постановление
  №27-п is the only place left in the repo where this fabricated source
  appears in a current document (ADR-0024 mentions it only to *retract*
  it; research/ files mention it in their original audit context). All
  rule YAML occurrences were correctly removed.

## Fabricated content (suspected)

- `docs/compliance/security-architecture.md:244,341` — fabricated cite of
  «ЦБ РУз №27-п» (see Major drift above). This is **proven** fabrication,
  not suspected, because ADR-0024 explicitly documented the regulation as
  non-existent.

- Other compliance source URLs verified live:
  - `https://lex.uz/ru/docs/2703056` (ЦБ РУз №2696) — WebFetch confirms
    real document, title and registration number match ADR-0024's claim.
  - `https://lex.uz/ru/docs/4674893` (НК РУз) — WebFetch confirms genuine
    Tax Code of Uzbekistan.

  No other fabrication observed in the limited 2-URL sample. The wider
  compliance pack URL inventory was not exhaustively crawled (time budget).

## Accurate sections (kudos)

- `docs/session-log.md` — full 86-row timeline, every sampled commit hash
  (`2be6ea2`, `c2c6f4e`, `7f88656`, `d2fb869`, `c116908`, `40c770d`,
  `94229e8`, `bcde558`, `a8f2b66`, `b124af6`, `5f634eb`, `9fa3d91`,
  `9972435`, `fd005a1`, `42b116b`, `4878258`) resolves via
  `git rev-parse`. PR refs (#12/#13/#14) all merged. Excellent
  archaeology.

- `docs/conventions/active-contracts.md` — sampled CA-044 (taxes_paid
  Money|None), CA-042 (FORM_2 tier priority), CA-049 (NEGATIVE_EQUITY
  rule), CA-067 (KPI hide-empty), CA-070 (level_tone=None v1) — every
  one matches code 1:1. This file is doing its job as live contract.

- `docs/adr/0017-pii-encryption-at-rest.md` — every file listed under
  Implementation exists at the path claimed (Encrypted{String,Bytea,Jsonb}
  TypeDecorators, Null/FernetPiiEncryptor adapters, pii migration
  20260518_2000, `pii_encryptor_port.py`).

- `docs/adr/0018-multi-tenant-runtime-isolation.md` — `Settings.brand_id`
  default "default" at `src/config/settings.py:71`; `_validate_runtime_config`
  at `src/interfaces/api/app.py:88`; `audit_log.brand_id VARCHAR(50)
  NOT NULL DEFAULT 'default'` confirmed via `\d audit_log`; both brand
  files `config/brands/{default,uzbekbank}.json` exist.

- `docs/adr/0019-ldap-authn.md` — `BreakGlassAuthnAdapter`,
  `LdapAuthnAdapter`, `Ldap3Client` all present in `src/infrastructure/auth/`;
  `analysts.authn_source VARCHAR(20) NOT NULL DEFAULT 'seeded'` confirmed
  in DB; `analysts.password_hash` correctly NULLABLE.

- `docs/adr/0024-foundational-source-verification.md` — all 9 source-
  attribution replacements match `config/rules/v1_uz_msb.yaml` content;
  `BalanceSnapshot.liabilities_fx` + KPI `fx_exposure_ratio` present
  in `src/application/dto/kpi_bundle.py:111` and
  `src/application/services/kpi_calculator.py:505-517` with explicit
  `level_tone=None` comment (CA-070 invariant honored); Alembic head
  `b04677374b85` confirmed via `alembic heads`.

- `deploy/README.md` — references real files: `deploy/install.sh`,
  `docker-compose.yml`, `docker-compose.prod.yml`, `scripts/build_release_tarball.sh`,
  every operations playbook in cross-refs exists.

- `docs/operations/2fa-smoke.md` — TOTP flow + Microsoft Authenticator
  iCloud-quirk note matches `RFC 5233 subaddress` workaround from session
  log entry 2026-05-14 Phase 5.B; `seed_analysts` CLI command path
  (`/app/src && uv run --no-sync python -m interfaces.cli.seed_analysts`)
  matches frontend wiring.

- `docs/operations/pii-key-rotation.md`, `multi-tenant-deploy.md`,
  `ldap-setup.md` — env var names, command structures, file paths all
  resolve.

## Verification table — CLAUDE.md numbers

| Claim | Actual | Match? |
|---|---|---|
| Rule count = 24 | 24 (grep `^\s+- id:` v1_uz_msb.yaml) | OK |
| KPI count = 8 (ADR-0024 set) | 8 ADR-0024 KPI fields confirmed in `kpi_bundle.py:97-111` (plus 4 legacy = 12 total in dataclass — but CLAUDE.md scopes "8" to ADR-0024 list) | OK |
| Dossiers = 49 (BR-2026-0001..0049) | 52 rows, BR-2026-0001..**0052** | STALE |
| Alembic head = b04677374b85 | b04677374b85 (head) | OK |
| ADR count = 0001..0024 | 24 files in `docs/adr/` | OK |
| Ports 8000/5433/6379 | docker-compose.yml: 8000:8000, 5433:5432, 6379:6379 | OK |
| Seeded analyst `t04@bank.uz` | row present in `analysts` table | OK |
| PRs #12/#13/#14 merged | all MERGED per `gh pr view` (2026-05-19 20:54-20:59 UTC) | OK |
| Latest commit `2be6ea2` | `git rev-parse 2be6ea2` resolves | OK |
| Rule registry 24 + KPI 8 in CLAUDE.md:28 | matches yaml + bundle | OK |
| `networkx>=3.4` Day 4 dep | confirmed in pyproject.toml deps for CIRCULAR via `_build_graph` | OK |

## ADR-vs-code drift table

| ADR | Decision claim | Code state | Drift? |
|---|---|---|---|
| 0005 drafts auth | "Phase 4 will add `drafts.owner_user_id NOT NULL`" | drafts table has NO owner column; Phase 4 closed without this migration | YES — promise not fulfilled, ADR not marked Superseded |
| 0017 PII | 6 PII columns via TypeDecorators; Alembic `c5d2f3a7e1b4` for `20260518_2000_pii_encryption.py`; MultiFernet rotation | All files present, migration file exists; `analysts.full_name VARCHAR(500)` post-expansion; ports/encryption infra match | NO |
| 0018 multi-tenant | `Settings.brand_id`, `_validate_runtime_config`, `audit_log.brand_id` indexed | All 3 verified: settings.py:71, app.py:88, audit_log schema confirms `ix_audit_log_brand_id_created_at` | NO |
| 0019 LDAP | `AUTHN_MODE` env switch, `BreakGlassAuthnAdapter`, `LdapAuthnAdapter` + `ldap3`, lazy upsert with `password_hash=NULL`, `authn_source` enum | All 4 file artifacts present; `analysts.password_hash` NULLABLE; `authn_source` VARCHAR(20) NOT NULL with seeded default | NO |
| 0024 FX/OKED | OKED atomic rename + fx_exposure_ratio (no level_tone) + CIRCULAR via networkx; Alembic `b04677374b85` | OKED rename confirmed (all `oked_*` paths exist), `fx_exposure_ratio` KPI in `kpi_calculator.py:505-517` returns `level_tone=None`, networkx imported in CIRCULAR rule, Alembic head matches | NO |

ADR-0005 is the only meaningful drift — promised Phase 4 migration never
happened. UUID-only auth is still the live model for drafts (Bank Mode
inherited UUID-only despite ADR's stated plan).

## TODO tracking

TODOs found in code (`src/` + `web/src/`):

- `CA-001` — `src/domain/value_objects/inn.py:3` (ИНН checksum). **In CLAUDE.md.**
- `CA-019` — `src/interfaces/api/bank/auth.py:201`, `src/interfaces/api/bank/admin.py:8` (access-token denylist). **In CLAUDE.md.**
- `CA-DS12` — `src/interfaces/api/bank/mfa.py:19` (mfa_secret encryption). **NOT in CLAUDE.md** — but closed by ADR-0017 (mfa_secret IS encrypted now); stale code comment, not stale plan.
- `CA-DS13` — `src/interfaces/api/bank/mfa.py:21` (admin-reset MFA). **NOT in CLAUDE.md** — but per session-log entry 2026-05-14 Phase 5 holes, CA-DS13 was *closed* (commit `f9dc928`). Stale code comment.
- `CA-DS10` — `src/infrastructure/persistence/migrations/versions/20260514_1000_phase5_settings_uptime.py:14`, `20260514_1500_phase5_real_mfa.py:15` (TOTP/SMS enrollment-flow). **NOT in CLAUDE.md.** Plausibly closed by Phase 5.B 2FA work (commit `d9387c0`).
- `CA-XXX` — `src/application/services/kpi_calculator_test.py:346` (NEGATIVE_EQUITY rule placeholder). Closed by CA-049 — but the test comment still has placeholder `CA-XXX`.
- `CA-DS19` — `web/src/features/manual-input/components/dscr-summary.tsx:8`. **In CLAUDE.md.**
- `CA-DS25` — `web/src/features/dossier/kpi-card.tsx:24` (KPI sparkline). **In CLAUDE.md.**
- `CA-003` — `web/src/features/manual-input/components/step-1-borrower.tsx:356` (ГНК lookup). **In CLAUDE.md.**
- `CA-031` — `web/src/features/manual-input/components/parsed-files-dropzone.tsx:9` (source-trail). **In CLAUDE.md.**

CLAUDE.md "Active code-level TODOs" lists: CA-001, CA-002b, CA-003, CA-019,
CA-031, CA-DS19, CA-DS25, CA-DS28.

- TODOs in code: 10 distinct IDs (counting closed-but-comment-stuck).
- TODOs in CLAUDE.md "active": 8.
- **Hidden TODOs in code (not in CLAUDE.md)**: `CA-DS12`, `CA-DS13`,
  `CA-DS10`, `CA-XXX` placeholder. Most likely *stale code comments*
  from work already closed (CA-DS12 closed by ADR-0017, CA-DS13 closed
  per session-log entry 2026-05-14), not hidden work — but the markers
  should be removed from the code so future greppers don't think
  the work is outstanding.
- **Stale TODOs in CLAUDE.md (not in code)**: `CA-002b` (CIRCULAR external
  invoices) — exists in YAML / docstrings via `circular_invoicing.py`
  but no `TODO[CA-002b]` literal in code. `CA-DS28` (ГНК public lookup)
  — referenced in active-contracts but no `TODO[CA-DS28]` literal.
  These are tracked entries in CLAUDE.md without corresponding code
  marker — could be intentional (backlog, no code yet written) or
  forgotten. Verify-by-name: both items have legitimate domain artifacts
  (`gnk_certificate.py`, `circular_invoicing.py`) so they're not
  fabricated; just not annotated as TODO.

## Areas not verified

- Full compliance pack URL crawl — only 2 of ~20 citations WebFetched
  (lex.uz/2703056 and lex.uz/4674893). FATF Recommendations,
  BIS d424, federalreserve.gov SR 26-02, group-ib.com URLs not pulled.
- Compliance pack statute numbers (Закон №547, ЗРУ-660, ст.47/257/223
  НК РУз, ПКМ №275/489) verified only at the ADR-0024 attribution layer
  — not against actual lex.uz documents. ADR-0024 itself was rigorous
  (3-way reconcile Claude/ChatGPT/Qwen) so risk is low.
- `db-backup.md`, `metrics.md`, `observability.md` playbooks — not
  sampled (time budget).
- `PROJECT_BRIEF.md` — not audited against current state (large file,
  scope was secondary to CLAUDE.md).
- Frontend i18n key audit (`ru.json` / `uz.json` keys vs `useTranslations`
  callsites) — out of scope, would be its own audit.
- Test coverage claim "Coverage `src/domain/rules` ≈ 99%, 217 unit +
  integration тестов" in README — neither verified (almost certainly
  stale: test count grew significantly through Tier 0-3).
- Verification of every `docs/operations/*.md` env var name against
  `Settings` class — only `LDAP_*`, `PII_ENC_KEYS`, `BRAND_ID`, `AUTHN_MODE`
  sampled.
