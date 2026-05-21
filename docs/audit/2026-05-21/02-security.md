# Security audit — credit-assistant 2026-05-21

Auditor profile: banker IT-security officer, 30-minute pre-pilot review. Scope: Python FastAPI backend (`src/`), Next.js frontend (`web/`), Postgres/Redis, Docker compose, deploy templates. Audit window: ~55 minutes static + live docker probes.

## Executive summary

Encryption-at-rest is solid (MultiFernet with key rotation, all sensitive PII columns covered) and there is **zero evidence of committed secrets in git history** — a real plus for a bank-pilot pack. But the system would not pass tier-1 IT-audit as-is: **no rate-limiting / brute-force protection on login or MFA**, **no row-level authorisation on dossier endpoints** (any authenticated analyst can fetch any dossier UUID), **JWT secret length never enforced**, **API container runs as root**, **uvicorn ignores X-Forwarded-For so audit IPs are useless in prod**, **backup encryption is opt-in**, and **state-changing endpoints (drafts, GNK upload, soliq upload) are not audited**. Pilot can proceed if Critical+High items are fixed before sign-off; otherwise an IT-officer will refuse approval.

## Banking IT-audit posture score: 5/10

Justification: foundation is right (encryption, audit table, secrets hygiene, parametrised SQL, JWT typ discrimination, refresh rotation + denylist, scrubbed Sentry, defence-in-depth in Caddy). But the missing pieces are the ones tier-1 IT officers look for first (brute-force limits, IDOR checks, defence-in-depth headers in the app, forensics-quality IP logging, root containers). A regional Uzbek bank in pilot phase might accept 5/10 with a clear fix-list; SberCIB or a state-owned bank would not.

## Critical (would block pilot deployment)

- **IDOR on dossier read/PDF/readiness** at `src/interfaces/api/shared/dossier.py:136-157`, `src/interfaces/api/shared/dossier.py:160-186`, `src/interfaces/api/shared/dossier_pdf.py:62-137`
  - Evidence: `get_dossier`, `get_dossier_readiness`, `download_dossier_pdf` accept any `dossier_id: UUID` and return full borrower PII + score + red-flags + 24-month chart + PDF; the only check is "dossier exists". No `created_by_analyst_id` / brand / role gate. Same for `get_draft` (`shared/draft.py:52-57`) by design (ADR-0005 capability-token model, but capability tokens leaking via logs/links is a banking-grade risk).
  - Impact: a junior analyst from one department can read a borrower file owned by another department / senior analyst if they obtain a UUID from a chat, a screenshot, an audit-log export. Banker IT will assume "least privilege" applies and refuse sign-off when any-analyst-sees-any-file is the default. Combined with the broken audit IP (below) — undetectable in forensics.
  - Fix recommendation: add a role-aware ownership check in `LoadDossierForView` or in the handler — at minimum `dossier.created_by_analyst_id == analyst.id OR analyst.role == 'senior_analyst'`. Drop the ADR-0005 "UUID = capability" model for bank mode.
  - Effort: 4 hours (handler + repository query + 3 tests).

- **No rate-limiting on /api/bank/auth/login, /refresh, /mfa/challenge** at `src/interfaces/api/bank/auth.py:51-93`, `src/interfaces/api/bank/auth.py:96-146`, `src/interfaces/api/bank/mfa.py:112-176`
  - Evidence: grep for `slowapi|ratelimit|throttle|limiter` across `src/` and `pyproject.toml` returns no hits. There is no FastAPI middleware, no Redis-backed counter, no IP-based rejection. 6-digit TOTP brute-force: with valid_window=1 (90 s validity per code) and unlimited attempts an attacker tries ~3×10⁴ codes/min → expected break ≈ 30 min over network, well within an analyst's lunch break. Password brute-force is rate-limited only by bcrypt (≈250 ms/attempt = 14 k/hour from one connection, more if parallel).
  - Impact: any leaked email + 30 min of unattended access ⇒ MFA bypass. Banks treat this as a blocker.
  - Fix recommendation: SlowAPI / fastapi-limiter on `/login`, `/refresh`, `/mfa/challenge` with Redis backend (Redis already wired). 5 attempts / 5 min / IP for login, 5 / 5 min / challenge-jti for MFA. Pair with audit event `auth_rate_limited`.
  - Effort: 6 hours (middleware + Redis schema + 4 tests).

- **JWT secret length / strength never validated** at `src/config/settings.py:49`, `src/interfaces/api/app.py:88-114`
  - Evidence: `jwt_secret: str = "dev-only-insecure-secret-change-me"` (32 chars but predictable). `_validate_runtime_config` only checks `PII_ENC_KEYS` in staging/prod — there is **no startup-assert for JWT_SECRET length, entropy, or default value**. A misconfigured prod deploy with the default secret signs valid tokens. `.env.example:25` says `change_me_in_real_env`; the actual `.env` (gitignored) has `dev-compose-insecure-change-me-32bytes-minimum` — still trivially guessable.
  - Impact: forge any analyst's access token if the default secret reaches prod.
  - Fix recommendation: in `_validate_runtime_config`, when `app_env in {staging, prod}` assert `len(jwt_secret) >= 32 AND jwt_secret not in {default values}`. Reject startup on fail.
  - Effort: 1 hour.

- **API container runs as root** at `Dockerfile:8-60`
  - Evidence: no `USER` directive; `docker exec credit-api id` → `uid=0(root) gid=0(root)`. Web container correctly uses `USER nextjs` (`web/Dockerfile`).
  - Impact: container breakout via a Python/native CVE (Pillow 12, WeasyPrint, ldap3) escalates to host root if Docker socket / volume mounts aren't strictly locked. Banking deploy guidelines (CIS Docker Benchmark §4.1) explicitly require non-root containers.
  - Fix recommendation: add `useradd --uid 1001 --system app && chown -R app:app /app && USER app` before ENTRYPOINT.
  - Effort: 1 hour (including verifying alembic + uvicorn permissions on /app/.venv).

## High (would require fix before sign-off)

- **uvicorn ignores X-Forwarded-For — audit IPs are wrong in prod** at `docker/entrypoint.sh:11-15`, `src/interfaces/api/bank/auth.py:42-48`
  - Evidence: entrypoint launches `uvicorn ... --host 0.0.0.0` with no `--proxy-headers` flag and no `FORWARDED_ALLOW_IPS`. Uvicorn default `forwarded_allow_ips=127.0.0.1` ignores headers from Caddy (different container IP in compose network). `_client_ip(request)` returns `request.client.host` = Caddy's container IP for every request. Audit log `login_failed.payload.ip` will be identical for every attempt regardless of origin.
  - Impact: forensics ("who tried 50 logins on Sunday?") is broken before pilot starts. IT-officer will reject sign-off because incident response can't isolate threat actor.
  - Fix recommendation: add `--proxy-headers --forwarded-allow-ips="*"` (or the specific Caddy container IP/subnet) to entrypoint; or set `FORWARDED_ALLOW_IPS=*` env in `docker-compose.prod.yml`.
  - Effort: 30 minutes + redeploy.

- **No defence-in-depth security headers from FastAPI** at `src/interfaces/api/app.py:155-176`
  - Evidence: `docker exec credit-api curl -i http://localhost:8000/health` returns no `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`, `Referrer-Policy`. Only Caddy edge sets them (`deploy/Caddyfile.template:40-46`), but Caddy doesn't set CSP either. Header `server: uvicorn` leaks framework. If Caddy is bypassed (internal port forward, smoke test, future internal API consumer) the API is naked.
  - Impact: Failed OWASP ASVS V14.4. Bank pen-test report will list this even if Caddy is present.
  - Fix recommendation: add `SecurityHeadersMiddleware` (or `starlette-secure`) in `create_app` that sets the five headers above. Remove `server: uvicorn` via `--header server:hidden` or middleware.
  - Effort: 2 hours including a smoke test.

- **No brute-force counter on backup-code consumption** at `src/infrastructure/auth/totp_service.py:97-111`, `src/interfaces/api/bank/mfa.py:138-148`
  - Evidence: `consume_backup_code` walks all hashed codes with bcrypt.verify per submitted attempt. No attempt limit. With 10 codes of 8 chars from A-Z0-9 (36^8 ≈ 3×10¹² space, but attacker can submit anything), bcrypt-rate-limits to ~4 attempts/sec per code → ~40/sec total. The actual risk is lower than TOTP brute-force (much larger keyspace) but the architecture says "no limit anywhere".
  - Impact: backup-code enumeration is theoretical but unbounded; same MFA-rate-limit fix solves it.
  - Fix recommendation: same as MFA rate-limit above.
  - Effort: included in MFA rate-limit task.

- **Access-token revocation not implemented (TODO[CA-019])** at `src/interfaces/api/bank/auth.py:149-178`, `src/interfaces/api/bank/auth.py:189-230`
  - Evidence: `/logout` denylists only the refresh token (best-effort), not the access token; comments explicitly admit this (`stateless v1; access токен остаётся валидным до TTL`). `/change-password` does not revoke any tokens. `/admin/analysts/reset-mfa` does not force-logout the target user — admin file even documents this (`admin.py:7-12`).
  - Impact: stolen access token remains valid 15 min after every recovery action. Compromise scenario: attacker steals JWT, victim sees alert and changes password → attacker still has 14 min of access. Banker IT considers `change_password` and `reset_mfa` to be high-trust events; failing to invalidate sessions there is an open finding.
  - Fix recommendation: short-term — drop access TTL to 5 min and require refresh more often; medium-term — JTI-denylist on `/logout`, `/change-password`, `/admin/reset-mfa`, `/mfa/disable` with Redis-backed access-jti table, expires at access exp.
  - Effort: 8 hours (implementation + tests + handler updates).

- **Backup encryption is opt-in; current dumps are unencrypted plaintext** at `scripts/backup_postgres.sh:24,61-74`, `backups/`
  - Evidence: `BACKUP_AGE_RECIPIENT` env optional; absent → `pg_dump --format=custom` written plain. Current `./backups/20260518T170143Z.dump` is a 243 KB PostgreSQL custom dump (`file` confirms `PostgreSQL custom database dump - v1.15-0`), no `.age` suffix. Even though PII columns themselves are Fernet-ciphertext in the dump, the dump still exposes: every `analysts.email` (plaintext), every `borrowers.inn` (TIN — PII under Uzbek Law 547 on personal data), every `borrowers.name`, every `audit_log.payload` (which includes masked-INN but also IP, request_id, event timestamps — forensic-sensitive).
  - Impact: a backup file landing on engineer's laptop or in an S3 bucket leaks the full borrower roster + audit timeline. Failed pen-test finding. Failed §3.6 PCI-DSS-analogue and ISO 27001 A.8.13.
  - Fix recommendation: make `BACKUP_AGE_RECIPIENT` mandatory; entrypoint of `backup_postgres.sh` should `exit 1` if unset. Document key custody in `docs/operations/`. Re-encrypt the two existing dumps or delete them.
  - Effort: 2 hours.

- **GNK certificate upload + soliq xltx upload + drafts: no audit log entries** at `src/interfaces/api/shared/gnk_certificate.py:72-115`, `src/interfaces/api/shared/soliq_upload.py:70-113`, `src/interfaces/api/shared/draft.py:31-57`
  - Evidence: grep for `audit_log\|record(event` in those files shows zero hits (only `gnk_certificate.py` imports nothing audit-related; `gnk_certificate_service.py` has no audit either — `grep "audit\|record" src/application/services/gnk_certificate_service.py` empty). These are state-changing endpoints handling PII (TIN, borrower name, financial periods, GNK PDF) — the audit trail has a gap.
  - Impact: a malicious / careless analyst can upload fake GNK certificates or VAT data, and there is no record of who did it when. Bank regulator will demand a complete trail.
  - Fix recommendation: add `audit_log.record(event=…)` for each: `gnk_certificate_uploaded`, `soliq_xltx_uploaded`, `draft_created/updated/deleted`. Payload with masked-INN, file size, MIME.
  - Effort: 3 hours including tests.

- **No virus scan, no magic-byte validation on file uploads** at `src/interfaces/api/shared/gnk_certificate.py:89-102`, `src/interfaces/api/shared/soliq_upload.py:148-163`
  - Evidence: GNK upload trusts `file.content_type` (client-supplied MIME) — attacker sends `application/pdf` MIME with `.exe` payload, server stores it in `gnk_certificates.file_bytes` (Fernet-encrypted, but still served back via `GET /api/gnk-certificates/{id}/file` with that MIME). Soliq endpoint parses xltx via openpyxl — zip-bomb / xltx-bomb (deeply nested formulas) → DoS. Size cap 5 MB but no zip-ratio guard.
  - Impact: stored XSS via PDF content (some PDF viewers); DoS via xltx bomb; banker pen-test will trial this in week one.
  - Fix recommendation: magic-byte check (e.g., `python-magic` to confirm actual MIME); openpyxl in `read_only=True` mode for soliq parsers (verify in code) + cap on cell count post-parse; document virus-scan integration point (ClamAV sidecar) for prod.
  - Effort: 4 hours.

## Medium (would be in pen-test report)

- **`/docs` and `/openapi.json` exposed without auth** at `src/interfaces/api/app.py:155-160`
  - Evidence: `curl -i http://localhost:8000/docs` returns 200 with Swagger UI HTML; `/openapi.json` returns full schema including all bank endpoints. Compose dev exposes 8000 to host. Prod Caddy proxies `/api/*` and `/health` to backend but not `/docs` — so prod via Caddy is OK by accident, not by design. Anyone with direct backend access in dev/staging sees the full API surface.
  - Impact: information disclosure for attacker mapping the system.
  - Fix recommendation: disable `docs_url`/`openapi_url` in `FastAPI()` when `app_env in {staging, prod}`. Or stake explicit allow-list in Caddy.
  - Effort: 30 min.

- **Stale TODO claim that mfa_secret is plaintext** at `src/interfaces/api/bank/mfa.py:19-20`
  - Evidence: comment "TODO[CA-DS12]: ``mfa_secret`` сейчас plain в БД. Production должна шифровать через банковский KMS/vault." But `src/infrastructure/persistence/models/analyst.py:66` declares `mfa_secret: Mapped[str | None] = mapped_column(EncryptedString(200), nullable=True)`; live DB query confirms ciphertext starting with Fernet `gAAAAA` prefix.
  - Impact: documentation lies; an honest review pass should catch this. Compliance auditor checks code comments for known gaps and will note the falsified TODO badly.
  - Fix recommendation: remove the stale TODO; replace with "mfa_secret is Fernet-encrypted via EncryptedString TypeDecorator (T1.3 / ADR-0017). Compromised PII_ENC_KEYS = MFA bypass — same blast radius as PII decryption."
  - Effort: 5 min.

- **Audit trail uses the same Fernet key as PII (no separation of duties)** at `src/infrastructure/persistence/types/encrypted_string.py`, `src/config/settings.py:64`
  - Evidence: single `PII_ENC_KEYS` env for PII payload, director name, full name, MFA secret. Compromise of one key → full PII + MFA bypass + ability to forge JWTs (separately, but key-management implies same vault).
  - Impact: blast radius of any key compromise is the entire dataset including MFA.
  - Fix recommendation: separate `MFA_ENC_KEYS` for `analysts.mfa_secret` and `analysts.mfa_backup_codes_hash`; document key custody so MFA key lives in HSM while PII key lives in Vault.
  - Effort: 4 hours.

- **`borrowers.inn`, `borrowers.name`, `analysts.email` stored as plaintext** at `src/infrastructure/persistence/models/borrower.py:27-28`, `src/infrastructure/persistence/models/analyst.py:29`
  - Evidence: `SELECT inn, name FROM borrowers LIMIT 3` returns `305738460 | GOF-KAR-UP MCHJ` (plaintext); `SELECT email FROM analysts` returns `ivanov@bank.uz` plaintext.
  - Impact: A unique TIN + business name is sufficient to identify a borrower. Uzbek Law 547 article 4 classifies TIN as personal data; same as analyst email. A DB-dump leak therefore leaks identifiable PII directly.
  - Fix recommendation: encrypt `borrowers.inn` (use separate searchable index via deterministic-encryption or HMAC for ILIKE search), encrypt `borrowers.name` (lose ILIKE search → switch to encrypted column + search column), encrypt `analysts.email` (login lookup via deterministic encryption or HMAC). Big migration.
  - Effort: 2-3 days (schema migration + repository changes + search rewrite).

- **`audit_log.payload` is plaintext JSONB and may grow PII** at `src/infrastructure/persistence/models/audit_log.py`, `src/interfaces/api/bank/mfa.py:151-154`
  - Evidence: payload dicts contain `masked_inn`, `target_email` (already masked via `mask_email`), `ip`, `authn_source`. All fine TODAY. But payload is unencrypted JSONB — any future audit caller adding `email` or `inn` or `passport` directly leaks instantly. There is no review-gate.
  - Impact: regression risk; backup-leak amplifier.
  - Fix recommendation: switch column to `EncryptedJsonb`. Cost: harder to query by payload (currently no callsite does that — confirmed via grep). Or, lint-rule: reject payloads with `'email'`, `'inn'`, `'passport'`, `'name'` as raw keys.
  - Effort: 3 hours.

- **No TrustedHost middleware** at `src/interfaces/api/app.py:155-176`
  - Evidence: grep `TrustedHost|allowed_hosts` returns nothing.
  - Impact: HTTP Host-header injection (e.g., `Host: attacker.com`) can poison cache, mis-route password-reset links (no password-reset email yet, but planned). Lower severity than missing rate-limit but a standard ASVS V14.5.1.
  - Fix recommendation: add `app.add_middleware(TrustedHostMiddleware, allowed_hosts=[brand_domain, "localhost"])`.
  - Effort: 1 hour.

- **CORS `allow_credentials=True` paired with `allow_headers=["*"]`** at `src/interfaces/api/app.py:162-168`
  - Evidence: `allow_credentials=True` + wildcard headers. CORS spec allows wildcard headers with credentials only because browsers reject `*` when credentials=true and substitute the explicit Origin — but documentation-readers tend to flag this. CORS origin IS pinned (`CORS_ALLOWED_ORIGINS`), so the actual risk is low.
  - Impact: easy pen-test "finding" even though exploitability is minimal.
  - Fix recommendation: enumerate the headers used (`Authorization, Content-Type, X-Request-ID`) instead of `*`.
  - Effort: 30 min.

- **`seed_analysts` CLI takes password as argv** at `src/interfaces/cli/seed_analysts.py:74-101`
  - Evidence: `parser.add_argument("--password", required=True)` — appears in shell history, ps -ef, journalctl.
  - Impact: dev / install-time password leak. Used for the smoke analyst seed; ops will inevitably copy commands into chat.
  - Fix recommendation: read password via `getpass.getpass()` if `--password` is not given; document that for prod.
  - Effort: 30 min.

## Low / Informational

- **CSRF protection relies on SameSite=Lax + JWT-in-Authorization-header** at `web/src/app/api/auth/login/route.ts:69-79` and pattern.
  - Cookies are httpOnly + Secure (prod) + SameSite=Lax. Backend never reads cookies (auth via Bearer header set by BFF). For strict banking, SameSite=Strict would be better. Acceptable but not best-in-class.

- **Logout audit doesn't include the action's source IP** at `src/interfaces/api/bank/auth.py:177`
  - `await audit_log.record(event="logout", analyst_id=analyst.id)` — no payload. Combined with the broken X-Forwarded-For story, logout events are forensically blind.

- **`forwarded_allow_ips` default leak in dev/local** — `request.client.host = "127.0.0.1"` for all containerised requests in dev compose. Won't matter for pilot.

- **`pip` 25.0.1 inside container has 4 known CVEs** (`CVE-2025-8869`, `CVE-2026-1703`, `CVE-2026-3219`, `CVE-2026-6357`) — these are pip-runtime CVEs, not exploitable in our runtime path (we never `pip install` at runtime; `uv sync --frozen` is used). Informational.

- **`python-jose` 3.5.0** is the latest published, but the library is community-maintained and slowly. Long-term: switch to `pyjwt`.

- **`ldap3` 2.9.1** — unchanged since 2021, no newer release. Pure-python LDAP client. No known CVEs at time of audit but the project being effectively abandoned is a supply-chain risk.

- **`secrets.token_hex(3)` in TOTP enrollment** (`totp_service.py:61`) — 6 hex chars = 16M variants. Fine for the deduplication purpose stated in the comment.

## What's solid (banker would credit)

- **No secrets ever committed.** `git log --all -S "BEGIN PRIVATE KEY"` → empty. `git log --all -- .env` → empty. `git log --all -S "iEuuP5WADM"` (actual Fernet key from `.env`) → empty. `.env`, `web/.env.local`, `backups/`, `backup-pre-t13.sql`, `backup-age-identity.txt` all in `.gitignore`. `.env.example` only contains placeholders.
- **PII at rest properly encrypted** via MultiFernet with explicit key rotation (`src/infrastructure/encryption/fernet_pii_encryptor.py`). Coverage:
  - `analysts.full_name`, `analysts.mfa_secret` → EncryptedString
  - `borrowers.director_name` → EncryptedString
  - `borrower_snapshots.payload` (financial details) → EncryptedJsonb with `{_encrypted: true, ciphertext: gAAAAA...}` wrap
  - `drafts.payload` → EncryptedJsonb
  - `gnk_certificates.file_bytes` → EncryptedBytea
  Live DB query confirms Fernet `gAAAAA` prefix.
- **bcrypt cost=12** (`password_hasher.py:20`) — banking standard.
- **JWT algorithm pinned on decode** — `algorithms=[self._algorithm]` (`jwt_service.py:61`), no algorithm-confusion (none, RS256-as-HS256) attack. Typ claim discriminates access/refresh/mfa_challenge so a refresh can't be used as access.
- **Refresh-token rotation + Redis denylist** (`auth.py:96-146`, `redis_refresh_token_denylist.py`). Detects token reuse, fails closed.
- **Sentry/GlitchTip PII scrubber** (`infrastructure/observability/sentry.py`) — two layers (`send_default_pii=False` + custom `before_send` regex). Drops request body, cookies, headers. Masks emails in breadcrumbs/extra/contexts.
- **SQL is parameterised everywhere.** No f-string SQL in repositories. The two `f"UPDATE … SET {set_clause}"` instances in migration `20260518_2000_pii_encryption.py:112,195` use controlled column-name lists with parametrised values — safe.
- **No `print()` or `console.log` leakage of PII.** Grep for `logger.*(tin|inn|passport|payload|email|password|secret|token)` empty.
- **Startup assertions** (`app.py:88-139`) crash-on-boot on missing PII_ENC_KEYS in staging/prod, missing BRAND_ID config, incomplete LDAP env. Good operator-error guard.
- **Caddy edge headers** (`deploy/Caddyfile.template:40-46`) set HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, hide Server. So the prod HTTP surface is OK; the gap is only defence-in-depth at app layer.
- **Audit log table is append-only by design** (`audit_log_repository.py:4`: "Mutations (update/delete) not provided — this is a security invariant"). request_id binding for trace correlation. brand_id forensic column (ADR-0018) for cross-tenant misconfig detection.
- **MFA enrollment requires TOTP + password to disable** (`mfa.py:179-209`) — proper two-secret confirmation.
- **Login + MFA-challenge audit-log with masked email** for both success and failure (`authenticate_analyst.py:50-72`, `mfa.py:151-154`).
- **Web container runs as non-root user `nextjs` uid 1001** (`web/Dockerfile`) — done right.
- **`.gitignore` is thorough** for `.env`, `backups/`, `backup-*.sql`, age keys, smoke artifacts.

## Areas not verified

- **`uv pip-audit` against runtime venv failed** (no internet inside container; running pip-audit from host venv would need a separate setup). Only listed installed versions and known-CVE crosscheck by memory. Recommend a CI step that runs `pip-audit` and `npm audit` periodically against a snapshot.
- **`npm audit`** — did not run inside web container; `package-lock.json` versions not cross-checked against advisory DB.
- **Actual penetration testing** — every "rate-limit" or "IDOR" finding above is from code-read, not from running an attack. Recommend a half-day live pen-test against staging before pilot.
- **Caddy actual config in pilot** — only the `Caddyfile.template` was reviewed. Real banks often add custom TLS / mTLS / IP allow-list that the template doesn't show.
- **LDAP path** — `authn_mode=ldap` code-reviewed but not exercised; default deploy is `seeded`.
- **Frontend XSS** — checked Jinja autoescape (PDF) only. React JSX/Next is generally XSS-safe but `dangerouslySetInnerHTML` callers not enumerated.
- **PII-key rotation procedure live-test** — `docs/operations/pii-key-rotation.md` exists per CLAUDE.md but was not exercised against the current data.
- **2FA "/disable" rate-limit** — same gap as MFA challenge; not separately tested.
- **Time-of-check / time-of-use on refresh-token denylist** — code reasons about it (`auth.py:130-142`) but not race-tested.
- **Restore drill** — `restore_drill.sh` exists, not executed within this audit window.
- **Headers under Caddy** — only the template was read; live response from a deployed instance behind Caddy was not measured.
