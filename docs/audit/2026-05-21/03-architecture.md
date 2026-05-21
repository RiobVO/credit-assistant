# Architecture & code quality audit — credit-assistant 2026-05-21

Auditor: Subagent #3 / 5 (senior backend reviewer simulation, ~60 min pass).
Scope: backend (`src/`), light pass on `web/`. Mandate — find architecture violations, pattern inconsistencies, quality smells, incomplete-but-claimed work; credit strong patterns honestly.

## Executive summary

Code health is **above the bar I'd set for a pre-pilot bank-internal tool** and well above average for projects of this age (~6 months of intense work). Clean Architecture boundary is genuinely respected — domain is import-pure (zero infra/ORM/framework leakage), every rule carries provenance annotations (`RULE_SOURCE` / `CONFIDENCE`), mappers are symmetric, migrations have non-trivial `downgrade()` blocks. The main reviewer concerns are (1) `application/use_cases/` reaching into concrete `infrastructure/*` instead of consuming `application/ports/*` (ports exist but are bypassed for a third of use-cases), (2) `application/services/case_id_allocator.py` mis-placed (it is an adapter, lives in `application/`), and (3) exception logging discipline relies on `logger.warning("...%r", exc)` rather than `logger.exception(...)` — stack traces aren't preserved on the error path. None of these are release-blockers, all are mechanical fixes.

## Architecture score: 8.5 / 10

Justification: Domain layer earns a solid 10 — it's textbook. Mappers earn 9 (symmetric, legacy-aware with explicit `.get()` defaults documented to CA-IDs). Migrations earn 9 (linear chain, every recent migration has working `downgrade`, PII migration is genuinely idempotent). Application layer drops to 7 because half the use_cases import concrete infrastructure classes by name instead of depending on ports — the ports infrastructure (`application/ports/*`) exists but isn't applied uniformly. Half-point off for `case_id_allocator` placement and the missing `logger.exception` discipline. No god-classes, no circular imports, no bare excepts, no `print()` in production code paths.

## Boundary violations

### Domain layer — clean

Greps for `from infrastructure`, `from sqlalchemy`, `from fastapi`, `from application`, `from interfaces` inside `src/domain/`: **zero matches**. The domain is genuinely framework-agnostic.

### Application layer — port discipline applied unevenly

Ports exist in `src/application/ports/` (11 ports: authn, repositories, allocator, encryptor, pdf, denylist, data source). Used correctly in some use-cases (e.g., `authenticate_analyst.py:13` consumes `AuthnPort`), bypassed in others.

Concrete-infrastructure imports inside `application/`:

- `src/application/use_cases/authenticate_analyst.py:14-17` — imports `JwtService`, `SqlAlchemyAuditLogRepository`, `mask_email` directly. `AuditLogPort` is not defined. JwtService is concrete (could plausibly live in domain).
- `src/application/use_cases/parse_manual_input_files.py:45-51` — imports 6 concrete classes from `infrastructure/adapters/soliq_xltx/*`. No `SoliqParserPort`. The use-case is welded to the xltx implementation; replacing parsing strategy requires editing the use-case.
- `src/application/use_cases/parse_manual_input_files.py:113` — function-local `from infrastructure.observability.metrics import …` (lazy import to avoid hard infra dep). Workaround for the absent port.
- `src/application/services/gnk_certificate_service.py:27` — imports `SqlAlchemyGnkCertificateRepository` concretely (no `GnkCertificateRepositoryPort`).
- `src/application/services/usd_rate_service.py:30-35` — concretely imports `load_usd_uzs_rate`, `fetch_usd_rate`, `SqlAlchemyUsdRateRepository`. The fallback chain (env → DB today → CBU live → DB latest → JSON) is fine logic, but the service can't be substituted for tests without monkey-patching modules.

Severity assessment — Medium. These don't break correctness; they make swapping infra (e.g., a real ГНК lookup vs uploaded-only) require editing application code. For a single-deployment-per-bank topology this is tolerable; if a partner ever asks "we want our own xltx parser" you'll feel it.

### Service-in-application that's actually infrastructure

- `src/application/services/case_id_allocator.py:27-28` — imports `sqlalchemy.text` and `AsyncSession`. Class is named `SqlAlchemyCaseIdAllocator` — the prefix admits it's an adapter. It implements `CaseIdAllocatorPort`. **Belongs in `infrastructure/persistence/`**, not `application/services/`. Same applies to `gnk_certificate_service.py` (depends on a SqlAlchemy repository) and `usd_rate_service.py`.

This is a placement smell rather than a hard violation — the file is correctly named with `SqlAlchemy*` prefix, and an architecture diagram drawn from imports alone would still show layered direction. But "application/services/" stops meaning "domain-orchestrating use case helpers" and starts meaning "anything that wires more than one infrastructure component."

### Interfaces layer

Not deeply audited (frontend audit covers `interfaces/api/*` in pair with the API layer). Surface scan shows `interfaces/api/bank/dependencies.py` and `interfaces/api/middleware.py` are the wiring choke points — they construct concrete adapters and inject them into use-cases. That's the right place for it.

## Pattern inconsistencies

- **Port usage 50/50.** Of 11 ports defined, ~half the call-sites consume the port; the other half import the SqlAlchemy implementation by name. Decide one way: either "ports for everything that crosses the layer boundary" or "ports only for things we actually plan to swap." Pick before adding the next adapter (LDAP/OIDC came up in the open backlog).

- **Test file naming**: project uses `*_test.py` co-located with code (good — `src/domain/rules/financial/dscr_low_test.py`). `tests/` directory holds integration/fixtures only. Pytest `python_files = ["test_*.py", "*_test.py"]` accepts both — that's the right call. But pyproject `[tool.mypy.overrides] module = ["tests.*"]` only loosens the `tests/` tree; co-located `*_test.py` in `src/` still get strict-mode typing rules. That's good, just worth noting it's enforced.

- **JSONB legacy-payload `.get()` chain has grown deep.** `snapshot_mapper.py` reads ~25 optional fields via `d.get(...)` with CA-XXX comments pointing at the contract that introduced each. Symmetric and documented, but the next person adding a field will copy the pattern blindly. A schema-version field in JSONB (`{"_v": 4, ...}`) would let the loader branch explicitly instead of doing N `.get()` probes — that conversation isn't urgent but is becoming due.

## Quality smells

### High

- **Exception logging loses stack traces.** Only one `logger.exception` / `exc_info=True` call in the entire `src/` tree (`infrastructure/jobs/uptime_collector.py:1`). Sample of caught exceptions logs them as `_logger.warning("...%r", exc)` (`usd_rate_service.py:83`) — formats the repr but discards the traceback. When CBU fetcher fails in production with a chained `ConnectionResetError → SSLError → CbuFetchError`, the operator only sees `CbuFetchError("HTTP 503")` — no stack to follow. Replace `.warning("...%r", exc)` with `.warning("...", exc_info=exc)` (or `.exception(...)` on the actual error path).

### Medium

- **`case_id_allocator.py` placement** — see Boundary section. Move to `infrastructure/persistence/` and re-export from there.

- **`application/use_cases/parse_manual_input_files.py` is 563 lines, 5–6 importing concrete adapters.** Combined with the lazy `from infrastructure.observability.metrics import …` on line 113, this file has become the integration glue for the entire soliq-xltx pipeline. Splitting per-form (Form1 / Form2 / VAT / ProfitTax) use-cases would shrink it and make the missing `SoliqParserPort` more obvious.

- **mypy --strict has 11 errors**, all of the form `Cannot find implementation or library stub for module named "tests.fixtures.soliq_xltx._factories"` plus one `Unused "type: ignore" comment` in `interfaces/api/shared/soliq_upload_test.py:35`. Co-located `*_test.py` files in `src/` import `tests.fixtures.…` (a directory not on `mypy_path` when running `mypy --strict src/`). Fix is either move the factories under `src/` or extend `mypy_path` to include `.` so the `tests/` package resolves. **The project claim "strict-clean" in `CLAUDE.md` is not currently true — strict run errors out on every commit unless tests/ is added to mypy invocation.**

- **47 `# type: ignore` instances across 23 files** — moderate. Not red, but the trend matters. About a third are in test files (acceptable for tighter mock typing); the rest sit on `pdf_renderer.py`, encrypted-column TypeDecorators, and pyyaml usages. Worth a sweep at next quiet patch.

### Low

- **`kpi_calculator.py` is 667 lines / 29 functions.** Not a god-class (no shared mutable state, all functions are pure helpers operating on `BorrowerSnapshot` or its sub-records), but at the upper end of "single-file readability." Splitting per KPI family (margin / coverage / liquidity / FX) would make CA-070 fx_exposure_ratio additions easier without scrolling.

- **Three exception swallows in `infrastructure/reports/pdf/pdf_renderer.py:498-513`** — all `(InvalidOperation, TypeError, ValueError) → pass`. They're a formatting fallback chain (try ratio formatter → try UZS formatter → return raw). Justifiable, but adding a single `logger.debug("pdf format fallback for key=%s value=%r", key, value)` before each `pass` would make a future "why is this field rendered raw in the PDF?" debug 60 seconds instead of an hour.

- **YAML `config/rules/v1_uz_msb.yaml` carries metadata + formula text, not numeric thresholds.** Thresholds are module-level constants in Python (`DSCR_MIN_THRESHOLD = Decimal("1.3")` at `dscr_low.py:16`, `THRESHOLD_UNSECURED = Decimal("0.4")` at `loan_to_revenue_ratio.py:25`, etc.). This is a valid design choice — keeps thresholds in version-controlled code with type safety — but it contradicts the project description "rules-engine with YAML config." If a bank ever wants to re-calibrate DSCR_MIN to 1.25 without a code deploy, they can't via YAML. Either rename the YAML's role (it's a "rule catalog with source/rationale", not a "config") or wire thresholds through the YAML.

## Strong patterns (credit where due)

- **Domain purity is the real thing, not a shibboleth.** `src/domain/**.py` has zero imports of SQLAlchemy, FastAPI, or `infrastructure.*`. A junior touching domain physically cannot reach for an ORM call. This is the most important architectural invariant in the project and it holds.

- **Every rule file carries provenance metadata.** `RULE_SOURCE:`, `CONFIDENCE:`, `VALIDATED_BY:` comments on `domain/rules/**/*.py` (verified on `dscr_low.py:3-9`). Tied to the YAML's `source:` field. For a bank-internal credit-scoring tool, this is exactly the audit-trail discipline I want to see.

- **Co-located tests with consistent naming.** Every rule has a `*_test.py` sibling. Mappers, KPI calculators, value objects, entities — all co-located. 877 tests collected from `src/` alone. Sampled test (`dscr_low_test.py`) is a real behavioral test with named scenarios, not `assert True` smoke.

- **Migration discipline.** 15 migrations, linear chain (no merges), no branches. Every one I sampled has a `downgrade()` with non-trivial inverse logic — PII encryption migration (`20260518_2000_pii_encryption.py`) does a full decrypt pass on rollback, with idempotency guards (`_is_encrypted_string` / `_is_encrypted_jsonb` prefix checks). The ОКЭД rename (`b04677374b85`) is a Postgres `ALTER COLUMN RENAME` — atomic, metadata-only, downgrade reverses cleanly. No FK constraint complications since `oked_main` isn't an FK.

- **Mapper symmetry.** `snapshot_mapper.py` — every `_X_to_dict` has a matching `_X_from_dict`. Legacy-payload contract (CA-037, CA-044, CA-047, CA-070 etc.) documented inline with the `.get()` default. Round-trip is by construction lossless on serialization (Decimal→str, Money→{amount,currency}, date→ISO).

- **No bare excepts. Zero.** `grep -rn "except:" src/` returns nothing. Every catch names an exception type. Re-raises preserve cause with `raise NewError(...) from exc` (verified `usd_rate_service.py:75`, `ldap3_client.py:62`).

- **No f-string PII logging.** `grep -rn 'logger\.info\(f|logger\.debug\(f' src/` returns nothing. All log statements use `%`-format (`_logger.warning("usd_rate.cbu_unavailable error=%r", exc)`) — safer for structured logging pipelines and harder to accidentally leak by string interpolation.

- **No `print()` in `domain/` / `application/` / `infrastructure/`.** Only hit is `src/interfaces/cli/seed_analysts.py:101` — a CLI script, appropriate place.

- **TypeScript strict: true and zero `@ts-ignore`** in `web/src/`. Frontend type-safety discipline is good (full audit deferred to frontend subagent).

- **Ruff clean** — `uv run ruff check src/` returns "All checks passed!"

- **Dependency hygiene in `pyproject.toml`.** Sensibly chosen libs (FastAPI / Pydantic / SQLAlchemy 2 async / WeasyPrint / networkx). No 14 date libraries, no abandoned packages. Pinning is `>=` (loose minimum) — fine for an actively maintained internal tool, would tighten to `~=` for vendored bank-deployable. mypy overrides per-package are documented inline with the reason ("WeasyPrint doesn't publish stubs", "ldap3 has no py.typed") — that's discipline.

- **Brand multi-tenancy is honest single-tenant-per-deploy**, not row-level masquerade. Only `audit_log` has `brand_id` column (forensics requirement, ADR-0018), the rest of the schema is owned by one bank's deployment. The CLAUDE.md status calls this out (`Multi-tenant deploy — separate compose-project per bank`). No fake "we filter by brand_id everywhere" claim — they didn't try to build it the wrong way.

## mypy / lint state

```
ruff check src/        → All checks passed!
mypy --strict src/     → Found 11 errors in 10 files (checked 346 source files)
```

The 11 mypy errors are all "Cannot find implementation or library stub for module named `tests.fixtures.soliq_xltx._factories`" — co-located test files in `src/` reaching into `tests/`, which isn't on `mypy_path` when mypy runs against `src/` alone. Plus one unused `type: ignore` at `interfaces/api/shared/soliq_upload_test.py:35`.

The fix is one of: (a) move `_factories.py` into `src/`, (b) run mypy against `src/ tests/` not just `src/`, (c) add `tests` to `mypy_path` in pyproject. The project's pre-push checklist (`CLAUDE.md`) already prescribes running both — but invoking `mypy --strict src/` alone (as documented in many places) reports red. **This contradicts the implicit claim of strict-clean and should either be fixed or noted.**

47 `# type: ignore` across 23 files (mostly tests and PDF renderer / encrypted columns). Acceptable count for a 27k-LOC backend, trending stable.

## Test posture

- **877 tests collected** from `src/` alone (co-located unit tests). Not counting `tests/` integration suite — couldn't collect from container (`/app` doesn't mount `tests/`, only `src/`). On host filesystem `tests/{application,domain,fixtures,infrastructure,integration,interfaces,parsers,scripts}/` exists.
- Sample quality: `src/domain/rules/financial/dscr_low_test.py` — real behavioral tests with factory helpers (`_annual()`, `_loan()`, `_snapshot()`) and named scenarios. Test count vs source LOC ratio is healthy (~3:1 in domain).
- **Test collection has 10 errors** — all the same `_factories` import problem. Tests are runnable when invoked correctly (per `CLAUDE.md`: `pytest src/ tests/`), but `pytest --collect-only src/` alone reports red.
- Critical paths covered: rule engine has per-rule tests; mappers have round-trip tests (`snapshot_mapper_test.py` — 542 lines); KPI calculator has 1040-line test file; auth use-case has tests; render-pdf has tests.

## Migration health

- **Chain linearity**: 15 migrations from `<base> -> 1e51c05eab8c` to `c5e9d2a7b1f4 -> b04677374b85 (head)`. Linear chain, no merges, no branches.
- **Sampled three recent migrations for `downgrade()`:**
  - `20260520_1300_rename_okved_to_oked.py` (`b04677374b85`): both upgrade() and downgrade() are 1-2 `op.alter_column(...)` calls. Atomic at the column level. ОКЭД rename touches only `borrowers.okved_main` and `borrowers.okved_main_changed_at` — neither is FK, no downstream constraint. Downgrade reverses cleanly. **Comment notes JSONB payload doesn't store borrower fields** (`snapshot_mapper.py:10`) — that's verified, so no backward-compat for JSONB is needed.
  - `20260518_2000_pii_encryption.py` (`c5d2f3a7e1b4`): non-trivial migration — schema length expansions + data encryption pass + idempotency guards. Downgrade does the full inverse: decrypt → restore VARCHAR length. Idempotency via `_is_encrypted_*` prefix checks (`gAAAAA` for Fernet) means re-running upgrade after partial failure is safe. Env-fallback (`PII_ENC_KEYS` absent → schema-only) is explicit and logged.
  - `20260518_1500_dossier_case_id_sequence.py`: didn't read in full, but file exists with both functions and is referenced in `case_id_allocator.py` docstring.
- **No idempotency on the ОКЭД rename** — re-running upgrade after a partial failure where `okved_main` was renamed but `okved_main_changed_at` wasn't would fail on the missing source column. For a one-shot atomic migration on a 49-row table this is fine, but a `try: op.alter_column(...) except (ProgrammingError): pass` guard would let production re-runs be safe. Low priority.

## Areas not verified

- **Repository pattern uniformity** — sampled `dossier_repository.py` and `audit_log_repository.py` paths but didn't audit every method of every repository for consistent transaction handling, query style (text vs ORM), or pagination patterns. Open question: do all repositories wrap their async with the same session-management contract?
- **Use-case test coverage of port substitution** — verified some use-cases construct with port arguments; didn't check that tests actually pass fake-port implementations vs real adapters.
- **API layer (`interfaces/api/`) input validation** — left to API/security subagent.
- **Frontend** — only checked tsconfig strict, package.json deps, `@ts-ignore` count, large component sizes. Detailed React-pattern review is for the frontend subagent.
- **Performance / N+1 query analysis** — out of scope for this pass.
- **Concurrency / race-condition audit** — only verified `case_id_allocator.py` uses `pg_advisory_xact_lock` correctly; didn't audit other concurrent paths.
- **Container-only `pytest src/ tests/`** — `tests/` isn't mounted in the api container; couldn't run the full integration suite from container to confirm "all green." Verification of green-CI claim deferred to a separate run.

---

## TL;DR for the team

1. **Boundary**: domain is genuinely clean; application/ has port-discipline drift (medium, mechanical fix).
2. **Migrations / mappers / rules / tests**: excellent, above bar.
3. **Three concrete asks**, in order of return-on-time:
   - Replace `logger.warning("...%r", exc)` with `logger.exception(...)` or `exc_info=exc` on caught-exception paths. ~30 minutes, big debuggability win.
   - Fix the `mypy --strict src/` invocation contradiction — either add `tests` to `mypy_path` or move `_factories.py` under `src/`. ~15 minutes, makes the prepush check honest.
   - Move `case_id_allocator.py` (and consider `gnk_certificate_service.py`, `usd_rate_service.py`) to `infrastructure/persistence/`. ~1 hour with test re-runs.
4. **Not a release blocker**: any of the above. Ship the pilot, fix in the post-demo hardening backlog already documented in CLAUDE.md.
