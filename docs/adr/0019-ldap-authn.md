# ADR-0019 — LDAP AuthnPort integration + break-glass whitelist

**Status:** Accepted · **Date:** 2026-05-18 · **Context:** T1.5 (Pre-Demo Roadmap, closes CA-020 LDAP-part)

## Context

PROJECT_BRIEF Section 3 / 8 фиксирует требование: «Authorization: банковский SSO (mock в POC, real LDAP/OAuth в production)». Pre-T1.5 единственный AuthnPort реализован как `SeededAuthnAdapter` (`analysts` table + bcrypt). Это не работает для bank-пилота: банки УЗ почти все на Active Directory / OpenLDAP и не позволяют параллельный user-store рядом с корпоративным каталогом.

Pre-T1.5 состояние:
- `AuthnPort` (Protocol) — единственная точка расширения, контракт уже extension-ready.
- `SeededAuthnAdapter` — единственный implementation, читает `analysts` table.
- 3 callsite через `AuthnDep`: login (`bank/auth.py`), MFA re-auth (`bank/mfa.py`), password change (`bank/auth.py`).
- `analysts` table: `email PK`, `password_hash NOT NULL`, `full_name`, `role`, `is_active`, `mfa_secret`, `mfa_enrolled_at`.

Требования к LDAP-интеграции:
1. **Mandatory** — bank-пилот без LDAP не запустится.
2. **Не убирать `SeededAuthnAdapter`** — dev/staging работают без LDAP, и break-glass admin'ы нужны на случай если LDAP-инфра упала.
3. **Compliance audit** — каждый login event пишет в audit-log источник аутентификации (`seeded`/`ldap`/`break_glass`).
4. **TOTP MFA остаётся** (ADR-0012) — LDAP заменяет только password verification, не отменяет 2-й factor.

OAuth2/OIDC и SAML — отдельная история, defer'ятся в backlog (T1.5b — для банков на Okta/Azure AD).

## Decision

**Approach: `AUTHN_MODE` env switch + break-glass email whitelist + lazy user provisioning.**

### Settings (env-level config)

```
AUTHN_MODE=seeded|ldap                                 # default seeded
LDAP_URI=ldaps://ldap.bank.uz:636
LDAP_BASE_DN=DC=bank,DC=uz
LDAP_BIND_DN=CN=svc-credit-assistant,CN=Users,DC=bank,DC=uz
LDAP_BIND_PASSWORD=<service-account-pass>
LDAP_USER_SEARCH_FILTER=(&(objectClass=user)(mail={email}))
LDAP_ROLE_ANALYST_GROUP=CN=Analysts,CN=Groups,DC=bank,DC=uz
LDAP_ROLE_SENIOR_ANALYST_GROUP=CN=SeniorAnalysts,CN=Groups,DC=bank,DC=uz
ADMIN_BREAK_GLASS_EMAILS=admin@bank.uz,emergency@bank.uz
```

### Adapter chain

В `authn_mode=seeded` (default):
```
get_authn_adapter() → SeededAuthnAdapter(analyst_repo, hasher)
```

В `authn_mode=ldap`:
```
get_authn_adapter() → BreakGlassAuthnAdapter(
    seeded=SeededAuthnAdapter(analyst_repo, hasher),
    ldap=LdapAuthnAdapter(client, settings, analyst_repo),
    break_glass_emails=parse(ADMIN_BREAK_GLASS_EMAILS),
)
```

`BreakGlassAuthnAdapter` — explicit branch по email:
- email в whitelist → `SeededAuthnAdapter` (local bcrypt).
- email вне whitelist → `LdapAuthnAdapter` (LDAP bind+search).

Это **не fallback** — switch. Operator не сможет случайно создать local account и обойти LDAP: для всех email'ов кроме whitelist единственный путь — LDAP.

### LDAP flow

1. **Service-bind** через `LDAP_BIND_DN`/`LDAP_BIND_PASSWORD` — service account read-only для search.
2. **Search** по `LDAP_USER_SEARCH_FILTER` с подстановкой email (escaped per RFC 4515) → получаем user DN + `memberOf`.
3. **Role resolution** по `memberOf`: senior-group → `senior_analyst`, analyst-group → `analyst`, нет роли → fail.
4. **User-bind** — отдельный bind с user DN + password → verify.
5. **Lazy upsert** в `analysts` table: `email`, `full_name` (`displayName`/`cn`), `role`. `password_hash=NULL`, `authn_source='ldap'` (T1.5.2 миграция).

### Library: `ldap3` (pure Python)

- Нет system deps (libldap-dev не нужен) → Dockerfile без изменений.
- Blocking API → оборачиваем в `asyncio.to_thread` в `LdapAuthnAdapter`.
- Per-call connection (no pool): bank-scale операции (десятки логинов/час) делают overhead несущественным, short-lived connections избегают stale-session проблем.

### Identity provisioning: lazy upsert

При первом успешном LDAP login создаём `analysts` row с `password_hash=NULL`, `authn_source='ldap'`. Subsequent logins обновляют `full_name` и `role` (LDAP-attrs могут меняться).

Миграция (T1.5.2):
- `ALTER COLUMN analysts.password_hash DROP NOT NULL`
- `ADD COLUMN analysts.authn_source VARCHAR(20) NOT NULL DEFAULT 'seeded'` + `CHECK (authn_source IN ('seeded','ldap'))`

`mfa_secret` остаётся NULL для нового LDAP-user'а до его enrollment в TOTP — separate flow через `/api/bank/mfa/enroll` (не меняется).

## Rationale

| Decision | Alternative | Why this |
|---|---|---|
| AUTHN_MODE env switch | Hybrid chain (LDAP→seeded auto-fallback) | Hybrid маскирует mistypes: typo email тихо проваливается к seeded. Switch — explicit, безопаснее |
| Break-glass через email whitelist | CLI-only break-glass tool | Email whitelist работает через стандартный login flow, не требует console доступа к API контейнеру; whitelist аудитится в коде/env |
| `ldap3` (pure Python) | `python-ldap` (C-binding) | Нет system deps в Docker, проще CI. Performance overhead vs C-binding несущественный на bank-scale |
| Per-call connection | Connection pool | Short-lived bind избегает stale-session, bank-scale не требует pool optimization. Если станет узким горлышком — добавим, не базовая абстракция |
| Lazy upsert | Pre-provision CLI | UX: новый сотрудник банка получает доступ автоматически после добавления в AD group, без admin-вмешательства в CA |
| Mock-only unit tests | testcontainers-openldap | Production использует реальный LDAP, mock покрывает adapter logic; openldap testcontainer defer'ится в T1.5c backlog для отдельного hardening pass |
| Role resolution до verify_password | После | Экономит один LDAP user-bind для users которые не в нужной группе. Side-effect: timing-разница может leak'ить group membership — но это публичная инфа в AD |
| LDAP-only в T1.5 | LDAP+OAuth | OAuth — отдельный protocol (redirect flow), отдельный adapter, отдельный ADR. Defer в T1.5b до запроса от bank на Okta/Azure AD |

## Trade-offs

- **Break-glass email whitelist в env** — если operator потеряет доступ к env-config (например `.env` файл удалён), recovery невозможна. Mitigation: list email'ов хранится также в banking ops runbook (out-of-band), env restore через team-shared secrets manager.
- **`asyncio.to_thread` для blocking LDAP calls** — каждый login делает `to_thread` × 2 (search + verify), spawning OS thread. На bank-scale (~10-100 logins/час) acceptable, не bottleneck.
- **LDAP role change visible на следующий login**, не realtime — пока user не разлогинится, role в JWT не обновится (15-min access TTL). Acceptable для bank-internal: critical role-changes требуют forced re-login через ops.
- **`password_hash=NULL` для LDAP-users** — security plus: атакующий с DB dump не получит password material для LDAP-users (LDAP-server владеет паролями). Trade-off: SeededAdapter для break-glass всё ещё хранит bcrypt-hash в БД (только для admin-emails).
- **Production fail-closed на LDAP unavailability** — service-bind error поднимает `LdapBindError`, caller (use case) возвращает 401. Не fallback на seeded для не-whitelist email'ов. Acceptable: если LDAP упал, банк не работает в целом, не только CA.

## Implementation phases

T1.5 разбит на 3 атомарных коммита:

- **T1.5.1** (этот коммит): Settings + adapter classes (LdapAuthnAdapter, Ldap3Client, BreakGlassAuthnAdapter) + unit tests (mock-based). DI wiring отложен.
- **T1.5.2**: Migration (`analysts.password_hash` NULLABLE + `authn_source` column) + `analyst_repo.upsert_from_ldap()` + DI factory switch. После этого `AUTHN_MODE=ldap` функционирует end-to-end.
- **T1.5.3**: Audit-log payload `authn_source` + `docs/operations/ldap-setup.md` + roadmap/CLAUDE.md sync.

## Future work

- **T1.5b** OAuth2/OIDC: `OAuthAuthnAdapter` поверх того же `AuthnPort`. Pre-condition: pilot bank на Okta/Azure AD.
- **T1.5c** openldap testcontainer для full integration tests. Закроется при первом hardening pass.
- **LDAP cache** — если bank-scale вырастет до тысяч логинов/час и `to_thread` overhead станет заметен. На bank-internal scale не нужен.
- **Per-OU role mapping** — сейчас 2 группы (analyst/senior_analyst). Когда добавится admin role (T3+ admin-management) — расширится через `LDAP_ROLE_ADMIN_GROUP`.
- **Direct-bind authentication** (bind by user DN без service-bind+search) — для LDAP'ов с consistent DN-pattern. Сейчас not used, can be added как parametric mode.
