# ADR-0016 — Refresh-token rotation + Redis denylist

**Status:** Accepted · **Date:** 2026-05-18 · **Context:** T1.2 (Pre-Demo Roadmap), closes CA-019

## Context

После закрытия Tier 0 (UZ-локализация, GNK, CBU, real fixtures, VAT-парсер) refresh-token flow остался stateless: один refresh `jti` валиден 7 дней без возможности отзыва. JwtService подписывает HS256, decode проверяет только signature + `typ` + `exp` (см. `src/infrastructure/auth/jwt_service.py`). Audit-log на `/logout` пишется, но сам токен продолжает работать до натурального expiration.

Failure modes:
- **Stolen cookie**: XSS / device theft / supply-chain attack → 7 дней неотзываемого доступа от лица аналитика. Bank-grade compliance такой gap не выдерживает.
- **Replay**: тот же refresh повторно используется параллельно (концертный поток на 401 от access-токена) — оба возвращают валидные access-токены.
- **Logout без revocation**: «выйти» из системы — это удалить cookie на BFF, но злоумышленник со stolen cookie продолжает refresh'ить access.

Pre-demo roadmap T1.2 фиксирует: rotation per-request + denylist старых tokens, dev-fallback на stateless 7-day режим.

## Decision

**Rotation:** каждый успешный `/api/bank/auth/refresh` (1) денилист'ит входящий `jti` и (2) выдаёт **новую пару** access + refresh. Старый refresh инвалиден сразу.

**Denylist storage:** Redis с ключом `refresh_denylist:<jti>` → `"1"`. TTL = `max(1, expires_at − now)` секунд — после натурального exp denylist-запись больше не нужна, Redis удалит её автоматически. Atomic `SET NX EX`: если ключ уже существует, NX возвращает `nil`, adapter возвращает `False` → caller трактует как `token_reused`.

**Logout denylist:** BFF читает `ca_refresh` cookie, прокидывает в backend body `{refresh_token: ...}`. Backend decode + denylist (best-effort: невалидный/чужой refresh silently ignore — access-токен уже подтвердил identity). Закрывает stolen-cookie hole: явный logout инвалидирует токен на оставшийся TTL.

**Fallback при `REDIS_URL=None`:** `NullRefreshTokenDenylist` — no-op (`is_denied` всегда `False`, `deny` всегда `True`). Сохраняет существующий stateless 7-day режим для dev без compose. Singleton выбора фабрикой `get_refresh_token_denylist()` по `settings.redis_url`.

**Fallback при Redis недоступен, REDIS_URL задан:** fail closed. `redis.exceptions.ConnectionError` / `TimeoutError` всплывают наверх из `RedisRefreshTokenDenylist.deny/.is_denied` — FastAPI отдаёт 500. Refresh не выполняется → compromised tokens не проскочат. Если REDIS_URL объявлен в env, Redis считается essential.

**Race-safety:** атомарный `SET NX EX`. Конкурирующие refresh с одним и тем же jti — один выигрывает SET (получает новую пару), остальные получают 401 `token_reused`. БД-сторонний `is_denied` check — fast-path для типичных reuse-attempts; финальный gate — NX в `deny`.

**Cross-account защита (logout):** backend decode'нув переданный refresh, сверяет `claims.analyst_id == current_analyst.id`. Чужой refresh в body — silently skip, не denylist'им. Access-токен подтверждает identity первого user'а; manipulating logout body не должен влиять на сессии других user'ов.

**JwtService остаётся pure stateless decode.** Denylist живёт отдельным сервисом `RefreshTokenDenylistPort` (`src/application/ports/refresh_token_denylist_port.py`). Это позволяет (a) тестировать decode без Redis, (b) подменить хранилище позже (PostgreSQL / Vault / cloud KMS).

## Alternatives considered

- **Allowlist** (валидные jti в Redis): write на каждый issue (login + refresh + mfa/challenge), не только на rotation. Лишний overhead для типовых flow login → много refresh; rotation проще как denylist write-on-rotate.
- **PostgreSQL denylist table**: транзакционно с auditom, persistent across restart. Но Redis уже в compose, latency `SET NX EX` < 1ms vs ~5-10ms на pg-insert. Для denylist persistence не критична — после `expires_at` запись бессмысленна, Redis TTL даёт автоматическое expiration. Если Redis вышел из строя и потерял ключи — refresh'ы со старыми jti снова валидны до их exp, что эквивалентно текущему stateless режиму.
- **JWT identifier rotation без denylist**: новый refresh с новым jti, старый jti остаётся валидным до своего exp. Не решает stolen-cookie сценарий — украденный токен живёт 7 дней.
- **JTI-blacklist в JWT claim**: невозможно (claims подписаны при issue, не модифицируются).
- **Stateful sessions через session cookie**: пересборка auth-флоу. Откладываем до T1.5 (LDAP/OAuth), где session-based authentication уже частично потребуется.

## Trade-offs

- **Redis SPOF в prod:** без HA Redis недоступность ставит refresh-flow на стоп. В compose dev — приемлемо (один pod). В prod банка ожидается Redis sentinel/cluster (часть infra deliverables в T3).
- **Cache-miss restart:** перезапуск Redis = потеря denylist. Все живые refresh снова валидны до их exp. Acceptable: атакёр без активной сессии не может воспроизвести stolen-cookie attack в этот короткий window; rotation продолжает работать сразу после restart.
- **Single-process counter race в Null mode:** при `REDIS_URL=None` rotation работает (новый refresh выдаётся), но старый остаётся валиден. Это и есть «stateless 7-day fallback» — явно зафиксирован для dev/POC, не для prod.
- **MFA `/challenge` не trogal:** первый issue refresh после MFA-success — не rotation. Token wear-pattern идентичен post-login: первый refresh запускает rotation, дальше цепочка.
- **BFF logout без refresh cookie** (race с expired cookie): backend silently skip denylist, audit пишется. Не страшно — refresh уже expired или никогда не был выдан.
- **`jti` collision:** `uuid4().hex` (128-bit), collision-probability negligible (~2.7×10⁻¹⁹). Не валидируем.

## Implementation sketch

**Файлы:**
- `src/application/ports/refresh_token_denylist_port.py` — `RefreshTokenDenylistPort` Protocol (`deny`, `is_denied`).
- `src/infrastructure/auth/null_refresh_token_denylist.py` — no-op fallback.
- `src/infrastructure/auth/redis_refresh_token_denylist.py` — Redis adapter, `SET NX EX`, TTL clamp до 1s.
- `src/interfaces/api/bank/dependencies.py` — `get_refresh_token_denylist()` factory с `@lru_cache(maxsize=1)`, switch по `settings.redis_url`.
- `src/interfaces/api/bank/auth.py` — `/refresh` + `/logout` с denylist.
- `src/interfaces/api/bank/auth_schema.py` — `RefreshResponse.refresh_token`, `LogoutRequest`.

**Settings:**
```python
# src/config/settings.py
redis_url: str | None = None  # T1.2: None → NullDenylist fallback
```

**Compose:**
```yaml
api:
  depends_on:
    redis:
      condition: service_healthy
  environment:
    REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
```

**Frontend BFF:**
- `web/src/app/api/auth/refresh/route.ts` — обновляет **обе** cookies (access + ca_refresh) из upstream-response.
- `web/src/app/api/auth/logout/route.ts` — прокидывает `refresh_token` в backend body до удаления cookies.

## Security checklist

- [x] Stolen-cookie window — closed: refresh инвалидируется при первой rotation owner'а ИЛИ logout'е.
- [x] Replay/race — closed: atomic SET NX EX, второй параллельный refresh → 401 token_reused.
- [x] Cross-account abuse в logout — closed: `claims.analyst_id == analyst.id` check.
- [x] Fail closed при Redis down — refresh не выполняется (compromised tokens не проскочат).
- [x] BFF httpOnly cookies — secure, sameSite=lax, path=/api/auth для refresh.
- [x] Frontend никогда не видит JWT — только наличие сессии (`/api/auth/me`).
- [ ] Redis HA / sentinel — deferred в T3 (operational readiness).
- [ ] PII encryption refresh_token-payload — N/A: JWT не содержит PII (только `sub` UUID + meta).

## Acceptance

- `POST /api/bank/auth/refresh` с валидным refresh → 200 с **обоими** токенами в body.
- Повторный `POST /api/bank/auth/refresh` с тем же refresh → 401 `token_reused`.
- `POST /api/bank/auth/logout` с `{refresh_token: X}` в body + access в Authorization → 204; следующий refresh с X → 401 `token_reused`.
- При `REDIS_URL=None` — все запросы как раньше, без denylist.
- При запущенном Redis: ключ `refresh_denylist:<jti>` живёт ровно до натурального exp.
