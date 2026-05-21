# Honesty audit — credit-assistant 2026-05-21

## Executive summary

Project documentation is, overall, **substantially honest** — the core
quantitative claims (rule count, KPI count, ADR numbering, Alembic head,
PII encryption columns, TOTP-based 2FA, bilingual PDF i18n,
multi-tenant model) are verifiable in code with file:line evidence.
ADR-0018 in particular openly documents what was NOT built and why,
which is a strong honesty signal. However, there is **one material
misrepresentation in the security narrative** — rate limiting via
`slowapi` is claimed in both `PROJECT_BRIEF.md` and the customer-facing
compliance pack but is **not present in dependencies, source, or
reverse-proxy config**. Several smaller numbers drifted (dossier count,
compliance pack TODO count). FRB SR 11-7 is invoked as
*conceptual rationale* for a coverage-floor mechanism rather than
implemented as a real model-risk-management framework — that distinction
should be sharper in customer-facing docs.

## Honesty score: 7.5/10

Architectural claims, persistence claims, and ADR provenance are
verifiable. Code-vs-config-vs-registry triangulation for rules passes
cleanly (24/24/24). PII encryption columns match docs to the byte
(6 columns, all wired). TOTP is real `pyotp` RFC 6238, not email-OTP
mock. Where the score gets dragged down:

- **`slowapi` / rate-limit claim is unsubstantiated** in PROJECT_BRIEF
  line 326 and `security-architecture.md` lines 39, 50. No code
  reference, no dependency, no nginx/Caddy `limit_req`. This is the
  single largest honesty gap because it appears in the **customer-facing
  security architecture document** that will go to the pilot bank.
- **"Account lockout after N failed attempts"** is asserted in the same
  paragraph; no implementation exists (`grep lockout|failed_attempt|
  locked_until` finds only mapper docstring).
- "49 dossiers" claim is stale — DB has **52**.
- SR 11-7 namedrop in `confidence_layer.py` is a rationalization, not
  an implementation. The actual mechanism (weighted coverage floor) is
  a sensible heuristic, but SR 11-7 is a *model risk management
  supervisory letter*, not a partial-data scoring framework. Acceptable
  internally; risky for bank-facing collateral.

Everything else holds up. Numbers, IDs, encrypted columns, audit log
trail, TOTP, ADR provenance, ML i18n bundles — verified.

## Verified claims (matches reality)

- **Rule count 24** — verified three ways:
  - `config/rules/v1_uz_msb.yaml` has 24 `id:` entries (lines listed
    earlier, from `DIRECTOR_CHANGED_6M` through `INSUFFICIENT_DATA`)
  - File-system count under `src/domain/rules/`: counterparty=5,
    financial=12, meta=1, payment_discipline=3, structural=3 → **24**
  - `src/infrastructure/rules/registry_factory.py:55-80` `CODE_RULES`
    dict has exactly 24 entries, and `load_registry` at line 83 raises
    `RuleConfigError` on YAML-vs-code asymmetry — invariant enforced.

- **KPI count 8 (new ADR-0024 set)** — verified in
  `src/application/services/kpi_calculator.py:66-75`: `ebitda`,
  `debt_to_ebitda`, `current_ratio`, `working_capital`,
  `interest_coverage`, `dscr`, `quick_ratio`, `fx_exposure_ratio`.
  Legacy `revenue_ltm`, `ebit`, `roe`, `debt_to_ebit` co-exist
  (CA-037 invariant). `fx_exposure_ratio` has no `level_tone` — matches
  doc "без level_tone v1, CA-070" claim (line 482-517 of kpi_calculator).

- **Alembic head `b04677374b85`** — `docker compose exec api uv run
  alembic heads` returned `b04677374b85 (head)`; DB
  `alembic_version` row equals the same string.

- **ADR count 0001..0024 contiguous** — `ls docs/adr/` returns exactly
  24 files, no gaps.

- **PII encryption (6 columns)** — verified the exact set claimed in
  `docs/compliance/admin-guide.md` line 96-98:
  - `analysts.full_name` — `models/analyst.py:36` `EncryptedString(500)`
  - `analysts.mfa_secret` — `models/analyst.py:66`
  - `borrowers.director_name` — `models/borrower.py:33`
  - `borrower_snapshots.payload` — `models/borrower_snapshot.py:39`
    `EncryptedJsonb`
  - `drafts.payload` — `models/draft.py:33` `EncryptedJsonb`
  - `gnk_certificates.file_bytes` — `models/gnk_certificate.py:42`
    `EncryptedBytea`

- **2FA is real TOTP, not email-OTP** —
  `src/infrastructure/auth/totp_service.py:18` imports `pyotp`, generates
  RFC 6238 secrets, has provisioning URI for QR, 10 one-time
  backup-codes hashed with bcrypt (lines 83-110). Enrollment flow
  exists in `src/interfaces/api/bank/mfa.py`.

- **Bilingual PDF i18n** — `config/pdf-i18n/{ru,uz}.json` both 186 lines,
  same key-space. UZ uses proper modifier apostrophe U+02BB
  (`soʻm`, `oʻrtacha`, `oʻzbek`), uses correct Soliq terminology
  (`QQS`, `EHF`). Loader at `src/infrastructure/i18n/pdf_messages.py`
  raises `IncompletePdfMessagesError` on missing keys.

- **Compliance pack 1007 lines** — `wc -l docs/compliance/*.md` returns
  267+391+349 = **1007** exactly as claimed.

- **TODO[CA-T4-UZ] markers** — `grep -c TODO\[CA-T4-UZ\]` per file:
  admin-guide=11, security-architecture=11, drp-bcp=9, total **31**.
  Doc explicitly says "грепай `TODO[CA-T4-UZ]`" — claim is honest.
  UZ sections are clearly labelled `O'zbek` with header note "mashinaviy
  tarjima asosida tayyorlangan skelet". No false bilingual claim.

- **Multi-tenant model — single-tenant per deployment** — ADR-0018 is
  explicit, lines 33-37: "borrowers/dossiers/snapshots/drafts/analysts —
  Approach A полагается на DB-level isolation through separate Postgres
  containers ... колонка не несёт security value". Only `audit_log` has
  `brand_id` for forensic cross-contamination detection
  (`audit_log_repository.py:22-31`). Doctrine and code agree.

- **CI green claim** — `gh run list --branch main -L 5`: last 4 pushes
  to main are `completed/success`; one cancelled (manual cancel of
  merged PR #13 immediately superseded by #14). Genuinely green.

- **Audit log table populated** — 735 rows in `audit_log`. Writes are
  scattered explicit `audit_log.record(...)` calls
  (`auth.py:177,229`, `mfa.py:108`, `admin.py:81,131`, etc.), not
  middleware. Doc never claims middleware — honest.

- **PDF rendering bilingual & real** — WeasyPrint via
  `src/infrastructure/reports/pdf/pdf_renderer.py`, per-render locale
  through `bundle.messages: PdfMessages` (line 11-15 docstring). Not a
  template stub — full HTML+CSS+JSON message bundle. Confidence: high.

- **External framework citations (FATF, Basel, ЦБ РУз, Закон №547)** —
  citations in `config/rules/v1_uz_msb.yaml` (FATF R.10, R.21, R.24,
  Basel III, BCBS d424, КМ РУз №275, ЗРУ-660, НК РУз гл.17, Постановление
  №27-п, Положение №2696) all reference real documents. WebFetch on
  `bis.org/bcbs/publ/d424.pdf` returned the 2.9MB binary PDF
  (URL exists, document real). FATF site returned 403 (anti-bot, not
  fabrication). Закон РУз №547 «О персональных данных» is a real RUz
  law. No fabricated citations detected.

- **Docker stack live** — `docker compose ps`: credit-api, postgres,
  redis, db-backup all `Up ... (healthy)`. Status doc accurate.

## Discrepancies (claims don't match)

### Critical (intentional misrepresentation)

- **`slowapi` rate limiting claimed but not implemented.**
  - `PROJECT_BRIEF.md:326`: "Rate limiting (slowapi) на all endpoints"
  - `docs/compliance/security-architecture.md:39`:
    "A07:2021 Identification/Authn Failures | bcrypt + MFA (TOTP/WebAuthn),
    refresh-token rotation, **rate limiting**"
  - `docs/compliance/security-architecture.md:50`: "Credential stuffing:
    rate limiting через **`slowapi`** на `/login`, account lockout
    после N failed attempts"
  - Reality: `slowapi` appears **only in `uv.lock`** (likely transitive,
    not a real dependency in `pyproject.toml:10-36`). `grep slowapi`
    against `src/` returns zero matches. `grep rate.?limit|429|
    TooManyRequest` against `src/` returns zero. Caddyfile template
    has no `limit_req`/`rate_limit` directive. **No rate limiting
    exists anywhere in the stack.**
  - **Severity:** Critical because this is a customer-facing bank
    compliance artifact making a specific OWASP A07 claim. A pilot
    bank security review will catch this on the first read. The fix is
    1-2 hours (add `slowapi` to pyproject, wire `/login` `/refresh`
    `/mfa/verify` with `@limiter.limit("5/minute")`); the misstatement
    is the issue.

- **"Account lockout after N failed attempts" claimed but not
  implemented.**
  - `docs/compliance/security-architecture.md:50-51` — same paragraph
    as above
  - Reality: `grep lockout|failed_attempt|fail.?count|locked_until|
    failed_login` returns only 2 hits, both in `analyst_mapper.py:18`
    docstring explaining why `mfa_enrolled_at` is the source of truth
    to avoid a *different* "lockout bug" (half-enrolled MFA). No
    actual lockout column on `analysts`, no failed-attempt counter
    in code. Bank tender pack lists this as A07 mitigation — false.

### High (significant drift)

- **Dossier count: 49 claimed → 52 actual.**
  - `CLAUDE.md` line 50 ("47 backfilled `BR-2026-0001..0047` + smoke
    `BR-2026-0048..0049`") and `active-contracts.md:23` ("49 existing
    dossiers"). Real DB:
    `SELECT COUNT(*), MIN(case_id), MAX(case_id) FROM dossiers` returns
    52 rows, `BR-2026-0001..BR-2026-0052`.
  - Likely cause: smoke runs added 3 dossiers post-Day-4 close. Not
    deliberate. Low security impact, but breaks the contract
    "49 existing dossiers загружаются с пустыми значениями" in the
    backward-compat test in active-contracts.md.

- **FRB SR 11-7 namedrop overstates what's implemented.**
  - `src/domain/services/confidence_layer.py:11` module docstring:
    "Решение (per FRB SR 11-7 / Basel III IRB partial-data
    conservatism)". This is a coverage-weighted floor — fine as a
    heuristic. SR 11-7 itself is the US Federal Reserve "Guidance on
    Model Risk Management" (2011), covering model **validation,
    governance, documentation, ongoing monitoring** — not partial-data
    scoring.
  - If this language ends up in customer materials (it currently only
    lives in the docstring, but the rationale is paraphrased in
    PROJECT_BRIEF risk-management narratives — worth a sweep), a bank
    model-risk reviewer will challenge it. Either implement the
    governance/validation aspects of SR 11-7 (model inventory,
    documentation requirements, validation cycle) or downgrade the
    citation to "loosely inspired by SR 11-7 model conservatism
    principle".

### Medium (minor drift, likely staleness)

- **Test count not explicitly claimed**, but `pytest --collect-only`
  from host returns **1310 tests**, from inside the container only
  877 (10 errors because `tests/` directory is not mounted into
  `/app`). The container `/app` has only `src/`. CI on Ubuntu does
  see both, hence green. **Pre-push checklist in CLAUDE.md** prescribes
  `pytest src/ tests/` from inside the docker exec — that command will
  *currently fail* in the container because `tests/` doesn't exist
  there. Either mount `tests/` in `docker-compose.yml`, or update the
  checklist to run pytest on host or via a separate volume mount.

- **Encrypted-bytea column listed as `gnk_certificates.file_bytes`.**
  Verified, matches doc. No drift — listing as caveat only because the
  field is `nullable=True` (`models/gnk_certificate.py:42`), so PII
  protection only kicks in when rows actually have file bytes. Worth
  confirming whether any real rows currently store certificates.

## Red flags

- **`slowapi` and lockout claims** are the strongest single signal
  that the security-architecture.md was written aspirationally rather
  than from inventory. Recommend a full top-to-bottom audit of that
  file against actual implementation — there may be other A0X claims
  with similar drift (e.g., A04 "Threat modeling до implementation,
  regular review" — is there a threat model document anywhere?
  `find docs -iname '*threat*'` returns nothing).

- **`pytest --collect-only` exits with 10 collection errors inside the
  running api container.** Not a regression of tests themselves (CI on
  host with mounted `tests/` is green). But it means the CLAUDE.md
  pre-push command (`docker compose exec -T api bash -c "cd /app && uv
  run python -m pytest"`) currently produces 10 ERRORs and exits
  non-zero. Anyone following the checklist literally will think the
  tree is broken.

- **EAG ("Eurasian Group on combating money laundering") cited in
  rule sources.** Real organization, but I couldn't quickly find a
  specific cited document/typology report. Worth checking whether
  any URL appears in source-trail JSON.

- **The `audit_log_repository.py` write API has no enforcement that
  `event` is from a closed enum.** Risk of typos drifting event names
  in the table (`login` vs `login_failed` vs `loginFailed`). Out of
  scope for honesty audit, but flag.

- **"Backups: `./backups/` (gitignored) — 2 dump'а после T3.4 smoke"**
  in CLAUDE.md — I did not verify, but easy to spot-check on the host.
  Backups sidecar is running per `docker compose ps`.

## Areas you couldn't verify

- **Sample bilingual PDF rendered output.** I did not run the WeasyPrint
  PDF generator end-to-end. The HTML template, message bundles, and
  loader chain look real; if it were a stub I'd expect placeholder
  fixtures, which are absent. But "render works" is unverified beyond
  unit-test presence (`pdf_renderer_test.py`,
  `pdf_renderer_kpi_slot_test.py`, etc., 4 test files).

- **Background `audit_log.brand_id` distinct check** — query the table
  for `SELECT DISTINCT brand_id FROM audit_log` to confirm rows are
  actually tagged with current `default` and not `NULL`. Not done.

- **TOTP enrollment flow end-to-end.** Code exists; I did not simulate
  enrollment → verify → backup-code consume. Logic looks correct
  (especially the MFA half-enrolled-state guard in `analyst_mapper.py
  :12-30`).

- **LDAP integration.** ADR-0019, `LdapAuthnAdapter`, `Ldap3Client`,
  `BreakGlassAuthnAdapter` all present. T1.5b/T1.5c noted as
  pre-conditions in CLAUDE.md. Not exercised.

- **EAG typology reports as cited source** — couldn't quickly verify a
  specific URL.

- **Sentry/GlitchTip sourcemaps upload** — listed as post-demo
  hardening backlog, not claimed delivered. No issue.

- **Prometheus / Grafana dashboard correctness** — `deploy/metrics/`
  contains the dashboard JSON and provisioning. Not verified that
  panels resolve real metrics.

- **WebFetch on FATF site** returned 403 (anti-bot). Citations look
  legitimate by name and pattern. Did not deep-verify individual
  Recommendation 10/21/24 numbering.
