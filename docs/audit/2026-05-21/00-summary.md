# Production-readiness audit — credit-assistant 2026-05-21

> Aggregated from 5 independent parallel audit subagents. Each subagent
> worked in isolation; synthesis is mine, individual findings are theirs.
> Source reports: `01-honesty.md`, `02-security.md`, `03-architecture.md`,
> `04-demo-readiness.md`, `05-documentation.md`.

---

## Area scores

| Area | Score | Headline |
|---|---|---|
| Honesty (claims vs reality) | **7.5 / 10** | Architectural and persistence claims hold up; one material misrepresentation in customer-facing security narrative (`slowapi`) |
| Security (banker IT-audit) | **5.0 / 10** | Foundations right (encryption, secrets hygiene, JWT discipline) but tier-1 IT-officer would block on IDOR + no rate-limit + root container + JWT validation |
| Architecture & code quality | **8.5 / 10** | Domain genuinely pure, mappers symmetric, migrations disciplined; port adoption uneven, stack-traces lost on error path |
| Demo readiness | **5.0 / 10** | Works on this host but not reproducible at pilot bank (demo data in gitignored dump); `/history` polluted with test borrowers |
| Documentation accuracy | **7.5 / 10** | ADRs / session-log / active-contracts excellent; README frozen at Phase 1; **fabricated «№27-п» citation survives in compliance pack** |

### Overall production-readiness: **6.5 / 10**

Weighted by use-case impact (security and demo dominate any external
audience). Above average for a 4-week project that openly does
architecture-first; **below the bar a tier-1 Uzbek bank IT-office would
sign off** without a 3–5 day cleanup sprint.

---

## Top 10 issues — priority ranked (severity × impact)

| # | Issue | Source | Effort | Impact |
|---|---|---|---|---|
| 1 | **IDOR on `/api/dossier/{id}`, `/dossier/{id}/pdf`, `/dossier/{id}/readiness`** — any authenticated analyst reads any dossier UUID. `src/interfaces/api/shared/dossier.py:136-186`, `dossier_pdf.py:62-137`. No `created_by_analyst_id` / role check. | Sec/Crit | **4 h** | Banker IT will refuse sign-off — least-privilege is broken by default. |
| 2 | **No rate-limiting on `/login` / `/refresh` / `/mfa/challenge`** — TOTP brute-force ≈ 30 min over network. `src/interfaces/api/bank/auth.py:51-93,96-146`, `bank/mfa.py:112-176`. Compounded by: `PROJECT_BRIEF.md:326` + `security-architecture.md:39,50` **claim `slowapi` + lockout that don't exist**. | Sec/Crit + Honesty/Crit | **6 h** + 30 min doc rewrite | Single largest combined-severity issue: real exploit path **and** a customer-facing lie about the mitigation. Bank security review catches both on day one. |
| 3 | **Fabricated regulation cited in compliance pack** — `docs/compliance/security-architecture.md:244,341` still cites «Постановление ЦБ РУз №27-п» which ADR-0024 itself documented as non-existent and scrubbed from rule YAML (RU + UZ both leak). | Docs/Crit | **30 min** | If this lands in tender pack, it's the single phrase that ends pilot trust. Same lie ADR-0024 spent a week removing — missed one file. |
| 4 | **API container runs as root** — `Dockerfile` has no `USER`. `docker exec credit-api id → uid=0`. Web container does it right. | Sec/Crit | **1 h** | CIS Docker Benchmark §4.1 hard-fail. Bank deploy guidelines insist non-root. |
| 5 | **JWT secret length / strength never validated** — `src/config/settings.py:49` default `dev-only-insecure-secret-change-me`; `_validate_runtime_config` (`app.py:88-114`) only asserts PII keys. Misconfigured prod = forge any token. | Sec/Crit | **1 h** | Trivial fix, catastrophic miss. |
| 6 | **Demo dossiers not reproducible at pilot bank** — `BR-2026-0030/0040/0042/0046/0047` exist only in gitignored `backup-pre-t13.sql`. `scripts/seed_demo_borrowers.py:79-128` creates 3 different INNs; `case_id` comes from DB sequence so fresh DB → `BR-YYYY-0001/0002/0003`. `deploy/install.sh:167-170` seeds only the admin. | Demo/Block | **3–4 h** | Demo trip is unflyable as currently scripted. Either rewrite seed to produce the 5 scenarios deterministically, or PII-scrub the dump and check it in. |
| 7 | **uvicorn missing `--proxy-headers`** → audit-log IPs all equal Caddy container IP in prod. Forensics dead before pilot starts. `docker/entrypoint.sh:11-15`. | Sec/High | **30 min** | Bank requires "who tried 50 logins on Sunday" answerable. Currently: "unknown — same IP for every request". |
| 8 | **Backup encryption opt-in; current dumps plaintext** — `scripts/backup_postgres.sh:24,61-74`; `./backups/20260518T170143Z.dump` is a 243 KB Postgres custom dump (no `.age` suffix). Even with Fernet-encrypted PII columns, `analysts.email`, `borrowers.inn`, `borrowers.name`, `audit_log.payload` are all plaintext in the dump. | Sec/High | **2 h** | Backup-leak = full borrower roster + audit timeline exfiltrated. Standard pen-test finding. |
| 9 | **State-changing endpoints write no audit log** — GNK certificate upload (`shared/gnk_certificate.py:72-115`), soliq xltx upload (`shared/soliq_upload.py:70-113`), drafts CRUD (`shared/draft.py:31-57`). All zero `audit_log.record(...)` calls. | Sec/High | **3 h** | A malicious analyst can upload a forged GNK certificate; no trail of who or when. Regulator demands a complete trail. |
| 10 | **`/history` showcase polluted with test data** — borrowers `ЙЦУЙЦУЙЦУ` (×5), `TEST`, `OOO Test T1.1`; analysts `T0.4 Smoke`, `T1.1 Smoke Tester`, `Smoke Тестер`. Visible on every demo. Compounded by `BRAND_ID=default` rendering tagline "**Accountant Mode**" on bank UI (`config/brands/default.json:4` + `topbar.tsx:38` + `sidebar.tsx:97`). | Demo/High | **1 h** (delete) + 5 min (set `BRAND_ID=uzbekbank`) | First impression to banker. Currently looks like a sandbox, not a product. |

### Notable mentions that just missed the top 10

- **Mock «verified» badge on any 9-digit INN** in manual-input wizard
  (`step-1-borrower.tsx:354-359`, i18n `s1_inn_summary_mock` = «Юр. лицо ·
  действующий статус»). Banker reads as live ГНК lookup; flagged in
  memory `feedback_mock_ui_on_decision_screens.md`. Fix ~2 h.
- **Access-token revocation not implemented (TODO[CA-019])** — `/logout`
  / `/change-password` / `/admin/reset-mfa` don't invalidate active access
  tokens. ~8 h.
- **README.md frozen at Phase 1**: claims «17 red-flag правил», «Coverage
  ≈ 99%, 217 тестов» (`README.md:7,83`). Actual: 24 rules, 1310 tests. ~30 min.
- **Lost stack traces** — only one `logger.exception` in entire `src/`;
  caught-exception path uses `logger.warning("...%r", exc)` which drops
  the traceback. ~30 min batch rewrite.
- **mypy `--strict src/` is not actually clean** — 11 errors (10 missing-
  stub for `tests.fixtures.soliq_xltx._factories` + 1 unused `# type:
  ignore`). Pre-push checklist invokes `src tests` which masks the issue;
  documented invocation is red. ~15 min.
- **ADR-0005 unfulfilled promise** — promised `drafts.owner_user_id NOT
  NULL` in Phase 4; Phase 4 closed without it; ADR not marked Superseded.
- **CLAUDE.md "Dossiers: 49"** stale — DB has 52 (`BR-2026-0001..0052`).
  Same root cause as `pre-demo-smoke.md:57` "48 dossiers".
- **«FRB SR 11-7» namedrop** in `confidence_layer.py:11` — SR 11-7 is the
  US Fed model-risk-management supervisory letter (validation /
  governance), not a partial-data scoring framework. Risky in
  bank-facing collateral; downgrade to "loosely inspired by".
- **Stale TODO claiming `mfa_secret` plaintext** at `bank/mfa.py:19-20`
  — false, column is Fernet-encrypted (verified `gAAAAA` ciphertext in
  DB). Auditor reading the comment will note the documentation lying.
- **PDF filename `BR-{uuid.hex[:4]}.pdf`** instead of `BR-2026-0046.pdf`
  human-readable that banker sees in UI. ~15 min.

---

## Use-case verdicts

### Portfolio piece — **READY**
Architecture genuinely exceeds the bar for a 4-week solo project: domain
purity, provenance metadata on every rule, symmetric mappers,
non-trivial migration downgrades, real PII encryption, real TOTP, real
i18n with proper Uzbek modifier apostrophes, honest ADRs (ADR-0018
openly documents what wasn't built). The fix-list above is itself a
demo of capability — "I built it, then I audited it, then I prioritized
the fixes" is a hireable narrative. **Show it as-is, with this audit
folder visible.**

### Demo MVP (on our host) — **NEEDS CLEANUP, ~1 day**
The 5 demo scenarios work end-to-end (PDF in 0.75 s, list in 10 ms, all
red-flag patterns match `scenarios.md` narrative). What blocks a polished
demo: (a) test borrowers `ЙЦУЙЦУЙЦУ` / `TEST` / `OOO Test T1.1` and
analysts `Smoke Тестер` in `/history`, (b) `BRAND_ID=default` rendering
"Accountant Mode" tagline in bank mode, (c) mock ГНК verified badge on
INN. Fix items #10, #11, and the mock badge → demo is presentable.

### Production deployment for tier-1 bank — **NOT READY, 3–5 day sprint**
Critical security items (#1, #2, #4, #5) plus High items (#6, #7, #8, #9)
each individually block sign-off. None are hard. Sequenced cleanup is
~60–80 hours of focused work for one engineer.

---

## Recommended fix priority

### Must-fix before demo trip (~12 hours, 1.5 days)
1. #6 demo-data reproducibility — without this no pilot install works
2. #3 fabricated regulation in compliance pack — banker will see this
3. #10 test data + Accountant Mode tagline cleanup
4. Mock ГНК verified badge — relabel or remove
5. README frozen at Phase 1 — 5-minute number refresh
6. CLAUDE.md "49 dossiers" + `pre-demo-smoke.md` "48 dossiers" → "52"

### Should-fix before pilot sign-off (~30 hours, ~4 days)
1. #1 IDOR on dossier endpoints (+ tests)
2. #2 rate-limiting on login/refresh/MFA (+ honest compliance-doc rewrite)
3. #4 non-root API container
4. #5 JWT secret length assert
5. #7 `--proxy-headers` on uvicorn
6. #8 mandatory backup encryption
7. #9 audit-log entries for state-changing endpoints

### Can defer indefinitely (post-pilot hardening backlog, ~20+ hours)
- Access-token denylist (TODO[CA-019])
- Encrypt `borrowers.inn`, `borrowers.name`, `analysts.email`
- Move `case_id_allocator.py` etc. to `infrastructure/persistence/`
- Replace `logger.warning("...%r", exc)` with `logger.exception(...)`
- `pyjwt` migration off `python-jose`
- ADR-0005 either implement `drafts.owner_user_id` or mark Superseded
- Per-form split of `parse_manual_input_files.py` (563 lines)
- Threshold YAML wiring (currently Python constants)
- TrustedHostMiddleware + `/docs` gating in staging/prod
- Disable Swagger in prod
- Separate MFA encryption key from PII key

### Total fix effort
- **Demo-ready**: ~12 h
- **Pilot-ready**: ~42 h on top of demo-ready (~54 h total)
- **Production-hardened**: ~80 h total

---

## Honest assessment

Four weeks of orchestrated work produced a system whose **architecture
deserves the praise it gives itself** — domain is genuinely pure, the
mapper / migration / rules discipline is the real thing, the ADRs are
load-bearing, the docs/code consistency is above average for this
project age. Where reality bites: the **security surface was inherited
from "make it work" velocity and never re-hardened** (no rate-limit,
no IDOR check, root container, JWT not validated, plaintext backups,
silent state-changing endpoints) — the compliance pack then **wrote
checks the code can't cash** (`slowapi` claimed, never installed). The
**demo is unflyable as currently scripted** because the 5 showcase
dossiers live only in a gitignored SQL dump. None of this is hard to
fix; all of it is hard to discover under a "Pre-demo MVP ready" label.
**Verdict: portfolio piece — yes, today. Demo — yes, after a 1.5-day
cleanup. Bank pilot — no, not until the 4-day security sprint lands.**
