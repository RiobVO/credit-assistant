# LDAP setup playbook (T1.5 / ADR-0019)

> Production deployment с `AUTHN_MODE=ldap`. Pilot-bank LDAP-параметры
> заполняются на инсталляции; ниже generic Active Directory defaults.

---

## Activation

В `.env` (или `docker-compose.yml` environment):

```bash
AUTHN_MODE=ldap
LDAP_URI=ldaps://ldap.bank.uz:636
LDAP_BASE_DN=DC=bank,DC=uz
LDAP_BIND_DN=CN=svc-credit-assistant,CN=Users,DC=bank,DC=uz
LDAP_BIND_PASSWORD=<service-account-password>
LDAP_USER_SEARCH_FILTER=(&(objectClass=user)(mail={email}))
LDAP_ROLE_ANALYST_GROUP=CN=Analysts,CN=Groups,DC=bank,DC=uz
LDAP_ROLE_SENIOR_ANALYST_GROUP=CN=SeniorAnalysts,CN=Groups,DC=bank,DC=uz
ADMIN_BREAK_GLASS_EMAILS=admin@bank.uz,emergency@bank.uz
```

Startup-assert в `interfaces/api/app.py` упадёт с `RuntimeError`,
если хоть одно из обязательных полей пустое.

---

## Active Directory mapping (generic defaults)

| Параметр | Значение по умолчанию | Notes |
|---|---|---|
| Search filter | `(&(objectClass=user)(mail={email}))` | `{email}` — placeholder, экранируется per RFC 4515 |
| Email attribute | `mail` (резолвится фильтром) | Для нестандартных схем заменить на `userPrincipalName` или `sAMAccountName` |
| Display name | `displayName` → `cn` (fallback) | Используется как `analysts.full_name` |
| Group membership | `memberOf` | Multi-valued attribute |
| Encryption | LDAPS (port 636) **обязательно** | `ldap://` без TLS — anti-pattern для bank-internal |

Open-LDAP / FreeIPA: заменить `objectClass=user` на `objectClass=inetOrgPerson` или `posixAccount`.

---

## Group → role mapping

Сейчас 2 роли:

- `senior_analyst` — admin endpoints (`bank/admin.py`, reset MFA, аудит-export когда добавим).
- `analyst` — обычный bank-mode user.

Если user в обеих группах — **senior precedence**. Без членства ни в одной — login fail (LDAP-bind пройдёт, role resolution вернёт `None`).

Добавление третьей роли (например `admin`) — изменение в `LdapAuthnAdapter._resolve_role` + новая env `LDAP_ROLE_ADMIN_GROUP`. Open до запроса от пилот-банка.

---

## Break-glass admin emails

`ADMIN_BREAK_GLASS_EMAILS` — comma-separated email'ы, для которых **в LDAP-mode** используется local SeededAuthnAdapter (bcrypt против `analysts` table). Use-cases:

- LDAP-инфра упала, нужен emergency access.
- Operator случайно потерял LDAP-доступ (например, AD-account locked).
- Initial bootstrap: пока LDAP не настроен, admin создаёт первого user'а через seeded.

**Provisioning**:
```bash
docker compose exec api bash -c "cd /app/src && uv run --no-sync python -m interfaces.cli.seed_analysts \
  --email admin@bank.uz \
  --password '<strong-password>' \
  --full-name 'Operations Admin' \
  --role senior_analyst"
```

Этот user пройдёт seeded flow даже когда `AUTHN_MODE=ldap`. Audit-log пишет `authn_source='break_glass'` для compliance подсветки.

**Безопасность**:
- Break-glass user'ы хранят bcrypt password_hash в `analysts.password_hash` (encrypted at rest через T1.3 ADR-0017 NOT относится к password_hash — только к full_name/mfa_secret).
- TOTP MFA обязательна для break-glass (как и для LDAP-users) — `mfa_enrolled_at` отдельно.
- Список email'ов хранится также в bank-ops runbook (out-of-band), на случай если `.env` потерян.

---

## Audit-log trail

Каждый успешный login event пишется с `authn_source` в payload:

```sql
SELECT event, payload->>'authn_source' AS source, created_at
FROM audit_log
WHERE event = 'login' AND created_at > now() - interval '7 days'
ORDER BY created_at DESC;
```

Ожидаемое распределение в `AUTHN_MODE=ldap` deployment'е:
- `ldap` — 99%+ events (обычные сотрудники банка).
- `break_glass` — единичные events (emergency access). Алерт при N > 0/day.
- `seeded` — 0 events (если есть — конфигурационная ошибка).

В `AUTHN_MODE=seeded` (dev/staging) — все events `seeded`.

---

## Operations runbook

### LDAP-сервер недоступен

Симптом: 401 `invalid_credentials` для всех non-break-glass logins.

Backend logs:
```
LdapBindError: LDAP service-bind failed: <reason>
```

Workaround:
1. Operator с email из `ADMIN_BREAK_GLASS_EMAILS` входит через seeded flow.
2. Через bank-admin endpoints решает urgent дела.
3. Восстанавливает LDAP-инфра.

Если LDAP — partial outage (server отвечает, но возвращает stale данные): не падаем, но user-role-promotion не отразится до восстановления.

### Role changed в AD

Симптом: user был `analyst`, добавлен в senior-group; в bank-mode остался `analyst`.

Cause: access JWT (15-min TTL) кэширует identity. После expiration refresh подгрузит новый role.

Resolution: попросить user'а logout/login или подождать 15 минут. Forced re-login через admin-endpoint — будущий enhancement.

### User не может войти, хотя в AD есть

Возможные причины (в порядке частоты):
1. **Не в analyst/senior-group** — добавить в `LDAP_ROLE_ANALYST_GROUP` через AD admin.
2. **Email не совпадает с LDAP `mail`** — проверить через `ldapsearch -x -b "$LDAP_BASE_DN" "mail=<email>"`.
3. **Search filter не подходит** — для нестандартных схем заменить `LDAP_USER_SEARCH_FILTER`.
4. **`LDAP_BIND_PASSWORD` устарел** — rotate service-account password через AD, обновить env.

Диагностика через test bind:
```bash
docker exec credit-api bash -c "ldapsearch -x \
  -H \$LDAP_URI \
  -D \"\$LDAP_BIND_DN\" \
  -w \"\$LDAP_BIND_PASSWORD\" \
  -b \"\$LDAP_BASE_DN\" \
  \"(mail=ivanov@bank.uz)\""
```

---

## Migration: dev → ldap-prod

Перед переключением на `AUTHN_MODE=ldap`:

1. ☐ LDAP-инфра доступна (test bind проходит).
2. ☐ `LDAP_ROLE_*_GROUP` группы существуют в AD, в них есть нужные users.
3. ☐ `ADMIN_BREAK_GLASS_EMAILS` заполнен (минимум 1 break-glass admin).
4. ☐ Break-glass user(ы) seeded в БД (через `seed_analysts` CLI).
5. ☐ Break-glass MFA enroll'ена (TOTP setup).
6. ☐ `_validate_runtime_config` startup-check проходит на staging.
7. ☐ Smoke: один LDAP-login + один break-glass-login, оба создают audit-log с правильным `authn_source`.
8. ☐ Production deploy. `LDAP_BIND_PASSWORD` — отдельный secret в Vault/SOPS, не в plain `.env`.

---

## Out of scope (см. backlog)

- **T1.5b OAuth2/OIDC** — pilot-bank на Okta/Azure AD. Pre-condition: запрос от банка.
- **T1.5c openldap testcontainer** — integration tests против реального LDAP в CI.
- **LDAP cache** — bank-scale делает overhead `to_thread` несущественным.
- **Direct-bind authentication** (skip service-bind+search) — для LDAP-серверов с deterministic DN pattern.
- **Per-OU role mapping** beyond 2 groups — потребуется при добавлении `admin` role.
