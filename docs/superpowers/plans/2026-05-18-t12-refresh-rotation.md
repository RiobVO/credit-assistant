# T1.2 refresh-token rotation + Redis denylist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps размечены `- [ ]`.

**Goal:** Закрыть CA-019. На каждый `/api/bank/auth/refresh` старый refresh denylist'ится в Redis, выдаётся новая пара access+refresh. Logout аналогично denylist'ит активный refresh. JwtService остаётся stateless decode; denylist живёт отдельным сервисом за портом.

**Fallback policy (roadmap):**
- `REDIS_URL=None` → `NullRefreshTokenDenylist` (no-op). Stateless 7-day режим сохраняется для dev без compose.
- `REDIS_URL` задан, Redis недоступен → fail closed: refresh/logout возвращают 503/401, чтобы compromised tokens не проскочили.

**Race-safety:** атомарный `SET denylist:<jti> 1 NX EX <ttl_seconds>`. NX=false → второй параллельный refresh отвергается (`401 token_reused`).

**Out of scope (frozen):**
- MFA `/challenge` — первый issue, не rotation. Без правок.
- LDAP/OAuth (T1.5), PII encryption (T1.3).
- Замена JwtService stateless-семантики; denylist — отдельный сервис.

**Tech Stack:** redis-py 5.x asyncio API, fakeredis (unit), testcontainers-redis (integration), FastAPI Depends, pytest-asyncio.

**Commit policy:** Single atomic commit в конце (после Phase 8 verify). Within phases TDD без промежуточных коммитов.

---

## File Structure

**Backend — новые:**
- `src/application/ports/refresh_token_denylist_port.py` — `RefreshTokenDenylistPort` Protocol.
- `src/infrastructure/auth/redis_refresh_token_denylist.py` — Redis adapter.
- `src/infrastructure/auth/redis_refresh_token_denylist_test.py` — unit (fakeredis).
- `src/infrastructure/auth/null_refresh_token_denylist.py` — no-op adapter (fallback).
- `src/infrastructure/auth/null_refresh_token_denylist_test.py` — unit (smoke).
- `tests/integration/auth/redis_denylist_integration_test.py` — testcontainers Redis.

**Backend — modify:**
- `pyproject.toml` — `redis>=5.0` в deps, `fakeredis>=2.20`, `testcontainers[redis]` в dev.
- `src/config/settings.py` — `redis_url: str | None = None`.
- `.env.example` — обновить комментарий REDIS_URL (T1.2 active, не «ARQ»).
- `docker-compose.yml` — `REDIS_URL` env в `api`.
- `src/interfaces/api/bank/dependencies.py` — `get_refresh_token_denylist()` factory + `RefreshDenylistDep` annotation.
- `src/interfaces/api/bank/auth_schema.py` — `RefreshResponse.refresh_token: str`, `LogoutRequest` optional refresh_token.
- `src/interfaces/api/bank/auth.py` — `/refresh` rotation + `/logout` denylist refresh.
- `tests/integration/api/bank_auth_test.py` — переписать 3 refresh-теста + новые (rotation/double-use/logout-denylist).

**Frontend — modify:**
- `web/src/app/api/auth/refresh/route.ts` — принимать `refresh_token` обратно, обновлять `ca_refresh` cookie.
- `web/src/app/api/auth/logout/route.ts` — отправлять `refresh_token` upstream до удаления cookie.

**Docs:**
- `docs/adr/0016-refresh-token-rotation.md` — новый ADR.
- `CLAUDE.md` — Active task: T1.2 closed → T1.3 next. Stack-комменты.
- `docs/pre-demo-roadmap.md` — T1.2 → DONE с commit hash.

---

## Task 1: Dependencies + Settings + Compose

**Files:** `pyproject.toml`, `.env.example`, `docker-compose.yml`, `src/config/settings.py`

**Why:** Подготовить инфру до domain-кода. `redis>=5.0` даёт `redis.asyncio` API; `fakeredis>=2.20` поддерживает asyncio mode для unit'ов; `testcontainers[redis]` — для integration.

- [ ] **Step 1.1: pyproject.toml** — добавить `redis>=5.0` в `dependencies`, `fakeredis>=2.20`, `testcontainers[redis]` в `dependency-groups.dev`. (uv update lock — позже одним прогоном).

- [ ] **Step 1.2: src/config/settings.py** — добавить поле:
```python
# T1.2 (CA-019): URL Redis для refresh-token denylist. None → NullDenylist
# (stateless 7-day fallback для dev без compose). Задан, но Redis недоступен
# → fail closed на /refresh и /logout (см. ADR-0016).
redis_url: str | None = None
```

- [ ] **Step 1.3: .env.example** — заменить комментарий `# Redis (для ARQ background jobs, Phase 2+)` на:
```
# T1.2 (CA-019): Redis для refresh-token denylist. Без значения — stateless fallback.
REDIS_URL=redis://localhost:6379/0
```

- [ ] **Step 1.4: docker-compose.yml** — в `api.environment` добавить:
```yaml
REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
```
(внутри compose-сети redis резолвится по имени сервиса).

- [ ] **Step 1.5: uv sync** — `docker compose exec -T api bash -c "cd /app && uv sync"` для обновления `uv.lock`. Verify: `redis` и `fakeredis` появились.

**Verify:**
```
docker compose exec -T api bash -c "cd /app && uv run python -c 'import redis.asyncio; import fakeredis.aioredis; print(\"OK\")'"
```

---

## Task 2: RefreshTokenDenylistPort + NullDenylist

**Files:**
- Create: `src/application/ports/refresh_token_denylist_port.py`
- Create: `src/infrastructure/auth/null_refresh_token_denylist.py`
- Create: `src/infrastructure/auth/null_refresh_token_denylist_test.py`

**Why:** Port — стабильный контракт между use-case и adapter'ом. Null-impl — fallback при `REDIS_URL=None`, гарантирует backward-compat stateless режим.

- [ ] **Step 2.1 (Red): null_refresh_token_denylist_test.py** — unit:
```python
import pytest
from datetime import UTC, datetime, timedelta
from infrastructure.auth.null_refresh_token_denylist import NullRefreshTokenDenylist


@pytest.mark.asyncio
async def test_null_denylist_never_denies():
    denylist = NullRefreshTokenDenylist()
    expires = datetime.now(tz=UTC) + timedelta(days=7)
    # add — no-op, не должен бросать
    await denylist.deny("any-jti", expires_at=expires)
    # is_denied — всегда False
    assert await denylist.is_denied("any-jti") is False
```

- [ ] **Step 2.2 (Green): refresh_token_denylist_port.py**
```python
"""Protocol для refresh-token denylist (T1.2 / CA-019).

Используется при rotation на /refresh и при /logout — старый jti помечается
denied до его натурального exp. Decode проверяет denylist, отвергает 401.
"""
from __future__ import annotations
from datetime import datetime
from typing import Protocol


class RefreshTokenDenylistPort(Protocol):
    async def deny(self, jti: str, *, expires_at: datetime) -> bool:
        """Атомарно добавить jti в denylist с TTL = expires_at - now.

        Returns:
            True — jti успешно denied (первый раз).
            False — jti уже был в denylist (race: параллельный refresh использовал
            тот же токен; вызывающий должен трактовать как reuse-attack).
        """
        ...

    async def is_denied(self, jti: str) -> bool:
        """Проверить наличие jti в denylist. False — токен не denied."""
        ...
```

- [ ] **Step 2.3 (Green): null_refresh_token_denylist.py**
```python
"""No-op denylist для dev без Redis. Stateless 7-day режим сохраняется."""
from __future__ import annotations
from datetime import datetime


class NullRefreshTokenDenylist:
    async def deny(self, jti: str, *, expires_at: datetime) -> bool:
        return True  # «успешно» — отсутствие denylist не блокирует ничего

    async def is_denied(self, jti: str) -> bool:
        return False
```

- [ ] **Step 2.4 (Verify):** `docker compose exec -T api bash -c "cd /app && uv run pytest src/infrastructure/auth/null_refresh_token_denylist_test.py -v"` → green.

---

## Task 3: RedisRefreshTokenDenylist (unit + fakeredis)

**Files:**
- Create: `src/infrastructure/auth/redis_refresh_token_denylist.py`
- Create: `src/infrastructure/auth/redis_refresh_token_denylist_test.py`

**Why:** Адаптер поверх `redis.asyncio.Redis`. Atomic `SET NX EX` для race-safety. TTL вычисляется как `(expires_at - now).total_seconds()` — после exp jti уже инвалиден, ключ можно удалить.

- [ ] **Step 3.1 (Red): redis_refresh_token_denylist_test.py** — unit с `fakeredis.aioredis`:
```python
"""Unit для RedisRefreshTokenDenylist через fakeredis.

Покрытие:
- deny() первый вызов → True, ключ присутствует с правильным TTL.
- deny() повторный вызов того же jti → False (race-detection).
- is_denied(): True для denied, False для unknown.
- TTL = expires_at - now (с допуском ±2s).
- Прошедший expires_at → deny() возвращает True но ключ моментально expire'ится
  (Redis принимает EX>=0, EX=0 отвергает; добавить min(1, ttl) guard).
- ConnectionError из Redis всплывает наверх (fail closed; trap в caller'е).
"""
import pytest
import fakeredis.aioredis
from datetime import UTC, datetime, timedelta
from infrastructure.auth.redis_refresh_token_denylist import RedisRefreshTokenDenylist


@pytest.fixture
async def denylist():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return RedisRefreshTokenDenylist(client, key_prefix="refresh_denylist:")


async def test_deny_first_call_returns_true(denylist):
    expires = datetime.now(tz=UTC) + timedelta(seconds=60)
    assert await denylist.deny("jti-1", expires_at=expires) is True
    assert await denylist.is_denied("jti-1") is True


async def test_deny_second_call_returns_false_race_detection(denylist):
    expires = datetime.now(tz=UTC) + timedelta(seconds=60)
    await denylist.deny("jti-1", expires_at=expires)
    assert await denylist.deny("jti-1", expires_at=expires) is False


async def test_is_denied_unknown_jti(denylist):
    assert await denylist.is_denied("ghost") is False


async def test_ttl_matches_expires_at_minus_now(denylist):
    expires = datetime.now(tz=UTC) + timedelta(seconds=120)
    await denylist.deny("jti-ttl", expires_at=expires)
    ttl = await denylist._client.ttl("refresh_denylist:jti-ttl")
    assert 118 <= ttl <= 120


async def test_past_expires_clamps_to_min_ttl(denylist):
    """Если expires уже прошёл (clock skew, expired token) — Redis не примет EX=0/negative.
    Adapter должен clamp до 1s, чтобы не ронять flow."""
    expires = datetime.now(tz=UTC) - timedelta(seconds=10)
    assert await denylist.deny("jti-past", expires_at=expires) is True
    ttl = await denylist._client.ttl("refresh_denylist:jti-past")
    assert ttl in (1, 0, -2)  # 1s clamp, или уже expired
```

- [ ] **Step 3.2 (Green): redis_refresh_token_denylist.py**
```python
"""Redis-adapter для refresh-token denylist (T1.2 / CA-019).

Ключ: `<prefix><jti>` → "1". TTL = max(1, expires_at - now). Atomic SET NX EX:
NX=False → второй параллельный refresh обнаружил уже denied jti — reuse-attack.

Fail-mode: ConnectionError/TimeoutError от redis-py всплывают вверх. Caller
(auth.py /refresh) ловит и возвращает 503/401 — fail closed.
"""
from __future__ import annotations
from datetime import UTC, datetime
from typing import cast

from redis.asyncio import Redis


class RedisRefreshTokenDenylist:
    def __init__(self, client: Redis, *, key_prefix: str = "refresh_denylist:") -> None:
        self._client = client
        self._prefix = key_prefix

    async def deny(self, jti: str, *, expires_at: datetime) -> bool:
        ttl_seconds = max(1, int((expires_at - datetime.now(tz=UTC)).total_seconds()))
        result = await self._client.set(
            self._key(jti), "1", nx=True, ex=ttl_seconds
        )
        # redis-py возвращает True (set), None (NX hit existing), либо bool.
        return result is True

    async def is_denied(self, jti: str) -> bool:
        return await self._client.exists(self._key(jti)) > 0

    def _key(self, jti: str) -> str:
        return f"{self._prefix}{jti}"
```

- [ ] **Step 3.3 (Verify):** `pytest src/infrastructure/auth/redis_refresh_token_denylist_test.py -v` → 5 green.

---

## Task 4: Integration test — Redis testcontainers

**Files:**
- Create: `tests/integration/auth/redis_denylist_integration_test.py`

**Why:** Зеркало unit-test, но против реального Redis-контейнера. Защита от семантических расхождений fakeredis vs redis-py 5.x (NX-возврат, TTL precision).

- [ ] **Step 4.1: redis_denylist_integration_test.py**
```python
"""Integration: RedisRefreshTokenDenylist против testcontainers redis."""
import pytest
import pytest_asyncio
from datetime import UTC, datetime, timedelta
from testcontainers.redis import RedisContainer
from redis.asyncio import Redis
from infrastructure.auth.redis_refresh_token_denylist import RedisRefreshTokenDenylist

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def redis_client():
    with RedisContainer("redis:7-alpine") as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)
        client = Redis(host=host, port=int(port), decode_responses=True)
        try:
            yield client
        finally:
            await client.aclose()


async def test_deny_then_is_denied(redis_client):
    denylist = RedisRefreshTokenDenylist(redis_client, key_prefix="test:")
    expires = datetime.now(tz=UTC) + timedelta(seconds=60)
    assert await denylist.deny("jti-int", expires_at=expires) is True
    assert await denylist.is_denied("jti-int") is True


async def test_concurrent_deny_nx_winner(redis_client):
    denylist = RedisRefreshTokenDenylist(redis_client, key_prefix="test2:")
    expires = datetime.now(tz=UTC) + timedelta(seconds=60)
    first = await denylist.deny("race-jti", expires_at=expires)
    second = await denylist.deny("race-jti", expires_at=expires)
    assert first is True
    assert second is False
```

- [ ] **Step 4.2 (Verify):** `pytest tests/integration/auth/redis_denylist_integration_test.py -v -m integration` → 2 green.

---

## Task 5: DI wiring

**Files:**
- Modify: `src/interfaces/api/bank/dependencies.py`

**Why:** Singleton factory. Если `settings.redis_url is None` → NullDenylist. Иначе создаём один `Redis.from_url(...)` client на процесс (lru_cache).

- [ ] **Step 5.1: dependencies.py — добавить factory и DI annotation**
```python
from application.ports.refresh_token_denylist_port import RefreshTokenDenylistPort
from infrastructure.auth.null_refresh_token_denylist import NullRefreshTokenDenylist
from infrastructure.auth.redis_refresh_token_denylist import RedisRefreshTokenDenylist


@lru_cache(maxsize=1)
def get_refresh_token_denylist() -> RefreshTokenDenylistPort:
    """T1.2: NullDenylist при REDIS_URL=None (stateless fallback), иначе
    Redis adapter. Singleton — Redis client живёт на весь процесс."""
    settings = get_settings()
    if settings.redis_url is None:
        return NullRefreshTokenDenylist()
    from redis.asyncio import Redis
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    return RedisRefreshTokenDenylist(client)


RefreshDenylistDep = Annotated[
    RefreshTokenDenylistPort, Depends(get_refresh_token_denylist)
]
```

- [ ] **Step 5.2 (Verify):** `docker compose exec api bash -c "cd /app && uv run python -c 'from interfaces.api.bank.dependencies import get_refresh_token_denylist; print(type(get_refresh_token_denylist()).__name__)'"` → `RedisRefreshTokenDenylist` (т.к. compose `REDIS_URL` задан).

---

## Task 6: Backend `/refresh` rotation

**Files:**
- Modify: `src/interfaces/api/bank/auth_schema.py`
- Modify: `src/interfaces/api/bank/auth.py`
- Modify: `tests/integration/api/bank_auth_test.py`

**Why:** /refresh теперь:
1. Decode incoming refresh → claims (jti, analyst_id, expires_at).
2. `is_denied(jti)` → True → 401 `token_reused`.
3. `is_active` check (existing).
4. `deny(old_jti, expires_at=old_exp)` — NX=False → 401 `token_reused` (race).
5. Выдаём новые access + refresh, возвращаем оба.

Logout сразу не трогаем — отдельный task для clean diff.

- [ ] **Step 6.1 (Red): integration test — переписать существующие 3 refresh-теста + добавить 3 новых.**

В `tests/integration/api/bank_auth_test.py`:

Расширить `api_client` fixture: переопределить `get_refresh_token_denylist` на `NullRefreshTokenDenylist()` для всех тестов **кроме** rotation/double-use — там in-memory fake.

Альтернатива: `app.dependency_overrides[get_refresh_token_denylist] = lambda: _InMemoryDenylist()` per-test через factory.

Test cases:
- `test_refresh_returns_new_access_AND_refresh` — body содержит и `access_token`, и `refresh_token`.
- `test_refresh_rotation_invalidates_old_refresh` — после refresh, повторный POST со старым refresh → 401 `token_reused`.
- `test_refresh_double_use_rejected` — параллельный second refresh с тем же токеном → 401.
- `test_refresh_rejects_access_token` (existing — оставить).
- `test_refresh_rejects_inactive_analyst` (existing — оставить).

In-memory denylist для тестов:
```python
class _InMemoryRefreshDenylist:
    def __init__(self):
        self._set: set[str] = set()
    async def deny(self, jti, *, expires_at):
        if jti in self._set:
            return False
        self._set.add(jti)
        return True
    async def is_denied(self, jti):
        return jti in self._set
```

Вынести в `tests/integration/api/conftest.py` или прямо в файл.

- [ ] **Step 6.2 (Green): auth_schema.py**
```python
class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str  # T1.2: rotation — возвращаем новый refresh
    token_type: str = "bearer"
```

- [ ] **Step 6.3 (Green): auth.py /refresh**
```python
@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest,
    jwt_service: JwtServiceDep,
    analyst_repo: AnalystRepoDep,
    denylist: RefreshDenylistDep,
) -> RefreshResponse:
    try:
        claims = jwt_service.decode(payload.refresh_token, expected_type="refresh")
    except InvalidTokenError as exc:
        raise HTTPException(401, detail="invalid_token") from exc

    if await denylist.is_denied(claims.jti):
        raise HTTPException(401, detail="token_reused")

    identity = await analyst_repo.get_by_id(claims.analyst_id)
    if identity is None or not identity.is_active:
        raise HTTPException(401, detail="invalid_token")

    # Atomic denylist старого jti. NX=False — параллельный refresh уже отыграл,
    # это reuse-attack либо race; в любом случае отвергаем второй refresh.
    denied = await denylist.deny(claims.jti, expires_at=claims.expires_at)
    if not denied:
        raise HTTPException(401, detail="token_reused")

    access = jwt_service.issue_access(identity.id)
    new_refresh = jwt_service.issue_refresh(identity.id)
    return RefreshResponse(access_token=access, refresh_token=new_refresh)
```

- [ ] **Step 6.4 (Verify):** `pytest tests/integration/api/bank_auth_test.py -k refresh -v` → 5 green.

---

## Task 7: Backend `/logout` denylist refresh

**Files:**
- Modify: `src/interfaces/api/bank/auth_schema.py`
- Modify: `src/interfaces/api/bank/auth.py`
- Modify: `tests/integration/api/bank_auth_test.py`

**Why:** BFF logout посылает refresh_token (если присутствует в cookie). Backend decode + denylist. Без access-токена /logout оставить нельзя — `CurrentAnalyst` гард требует access; это OK, потому что logout всегда идёт из авторизованной сессии.

- [ ] **Step 7.1 (Red): integration test**
```python
async def test_logout_denylists_refresh_token(api_client, pg_session):
    # ... seed + login
    login_body = (await api_client.post("/api/bank/auth/login", json={...})).json()
    access = login_body["access_token"]
    refresh = login_body["refresh_token"]

    resp = await api_client.post(
        "/api/bank/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
        json={"refresh_token": refresh},
    )
    assert resp.status_code == 204

    # /refresh со старым refresh → 401 token_reused
    retry = await api_client.post("/api/bank/auth/refresh", json={"refresh_token": refresh})
    assert retry.status_code == 401
    assert retry.json()["detail"] == "token_reused"


async def test_logout_without_refresh_token_still_succeeds(api_client, pg_session):
    """Backward-compat: старый клиент без refresh_token в body должен работать.
    Logout audit-only path; денилист silently skip."""
    # ... seed + login
    resp = await api_client.post(
        "/api/bank/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 204
```

- [ ] **Step 7.2 (Green): auth_schema.py**
```python
class LogoutRequest(BaseModel):
    """T1.2: optional refresh_token для denylist при logout. Backward-compat
    с старыми клиентами — поле опциональное."""
    refresh_token: str | None = None
```

- [ ] **Step 7.3 (Green): auth.py /logout**
```python
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    analyst: CurrentAnalyst,
    audit_log: AuditLogRepoDep,
    jwt_service: JwtServiceDep,
    denylist: RefreshDenylistDep,
    payload: LogoutRequest | None = Body(default=None),
) -> Response:
    # Refresh denylist — best-effort. Невалидный/чужой refresh — игнорируем,
    # logout сам по себе уже подтверждён access-токеном.
    if payload is not None and payload.refresh_token:
        try:
            claims = jwt_service.decode(payload.refresh_token, expected_type="refresh")
            if claims.analyst_id == analyst.id:
                await denylist.deny(claims.jti, expires_at=claims.expires_at)
        except InvalidTokenError:
            pass  # broken refresh — пусть истечёт натурально

    await audit_log.record(event="logout", analyst_id=analyst.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 7.4 (Verify):** `pytest tests/integration/api/bank_auth_test.py -k logout -v` → 4 green (3 existing + 2 new).

---

## Task 8: Frontend BFF — refresh rotation cookie + logout passthrough

**Files:**
- Modify: `web/src/app/api/auth/refresh/route.ts`
- Modify: `web/src/app/api/auth/logout/route.ts`

**Why:** Refresh должен обновлять `ca_refresh` cookie с новым токеном (иначе следующий /refresh снова пошлёт старый → 401). Logout должен прокидывать refresh upstream до удаления cookie.

- [ ] **Step 8.1: web/src/app/api/auth/refresh/route.ts** — типизировать data как `{access_token: string; refresh_token: string}`, после успешного upstream-ответа поставить **обе** cookies (access path=/, refresh path=/api/auth).

```typescript
const data = (await upstream.json()) as { access_token: string; refresh_token: string };
const response = new NextResponse(null, { status: 204 });
const isProd = process.env.NODE_ENV === "production";
response.cookies.set(ACCESS_COOKIE, data.access_token, {
  httpOnly: true,
  secure: isProd,
  sameSite: "lax",
  path: "/",
  maxAge: 15 * 60,
});
response.cookies.set(REFRESH_COOKIE, data.refresh_token, {
  httpOnly: true,
  secure: isProd,
  sameSite: "lax",
  path: "/api/auth",
  maxAge: 7 * 24 * 60 * 60,
});
return response;
```

- [ ] **Step 8.2: web/src/app/api/auth/logout/route.ts** — прочитать `ca_refresh` cookie, передать в body upstream:

```typescript
const store = await cookies();
const access = store.get(ACCESS_COOKIE)?.value;
const refresh = store.get(REFRESH_COOKIE)?.value;

const upstream = await fetch(`${API_URL}/api/bank/auth/logout`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    ...(access ? { Authorization: `Bearer ${access}` } : {}),
  },
  body: JSON.stringify(refresh ? { refresh_token: refresh } : {}),
});
// далее как раньше — удаляем cookies
```

(Прочитать текущий контент logout/route.ts перед изменением — структура может отличаться от ожидания.)

- [ ] **Step 8.3 (Verify):** `cd web && npm run typecheck` → pass. RTL для BFF route не существует (не было раньше), не добавляем.

---

## Task 9: ADR-0016 + docs

**Files:**
- Create: `docs/adr/0016-refresh-token-rotation.md`
- Modify: `CLAUDE.md`
- Modify: `docs/pre-demo-roadmap.md`

**Why:** Зафиксировать decisions: Denylist vs allowlist, NullDenylist fallback, fail-closed Redis-down policy, atomic SET NX EX. ADR следует структуре существующих (0014 — внешние API, 0015 — i18n).

- [ ] **Step 9.1: docs/adr/0016-refresh-token-rotation.md** — Context (CA-019 stolen-cookie hole 7 дней), Decision (rotation + Redis denylist + NullDenylist fallback + fail closed), Rationale (denylist vs allowlist — почему write только на rotate), Trade-offs (Redis SPOF в prod без HA, dev без Redis = stateless), Implementation (jti-based, NX-race, BFF cookie sync).

- [ ] **Step 9.2: CLAUDE.md** — обновить Current Status:
  - T1.2 done с commit hash.
  - Active task → T1.3 PII encryption (или следующий в roadmap).
  - Stack state: `credit-redis` теперь активный consumer.
  - Раздел «Persistence / infra»: добавить bullet `Redis: refresh-token denylist (T1.2) — REDIS_URL env, NullDenylist fallback, fail closed при недоступности`.

- [ ] **Step 9.3: docs/pre-demo-roadmap.md** — T1.2 → DONE с commit hash. Если есть «Resolved decisions» секция — внести 7 принятых решений.

---

## Task 10: Verify full pipeline

- [ ] **Step 10.1: Backend full verify**
```
docker compose exec -T api bash -c "cd /app && PYTHONPATH=/app/src uv run python -m ruff check . && uv run python -m mypy --strict src/ tests/ && uv run python -m pytest"
```

- [ ] **Step 10.2: Frontend verify**
```
cd web && npm run lint && npm run typecheck && npm test -- --run
```

- [ ] **Step 10.3: E2E smoke (manual)**
```
curl -X POST http://localhost:8000/api/bank/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"t04@bank.uz","password":"T04Smoke!"}'
# получить refresh_1

curl -X POST http://localhost:8000/api/bank/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<refresh_1>"}'
# получить refresh_2, access_2

curl -X POST http://localhost:8000/api/bank/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<refresh_1>"}'
# ожидать 401 token_reused

curl -X POST http://localhost:8000/api/bank/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<refresh_2>"}'
# OK — refresh_3
```

- [ ] **Step 10.4: Redis state check**
```
docker compose exec redis redis-cli KEYS 'refresh_denylist:*'
# должны быть два jti (refresh_1, refresh_2)
docker compose exec redis redis-cli TTL refresh_denylist:<jti>
# < 7d worth seconds, > 0
```

- [ ] **Step 10.5: CI status** — `gh run list --branch main -L 3` перед push. Если baseline красный — не push до выяснения.

---

## Commit

После всех ✓ — одним атомарным commit:

```
feat(auth): T1.2 refresh-token rotation + Redis denylist (CA-019)

- RefreshTokenDenylistPort + Redis adapter (atomic SET NX EX) + Null fallback.
- /refresh: rotation. Old jti → denylist, выдаём новые access + refresh.
- /logout: denylist активного refresh из body (best-effort).
- BFF: refresh route обновляет ca_refresh cookie; logout проксирует refresh upstream.
- ADR-0016. CLAUDE.md + roadmap T1.2 → DONE.

Closes CA-019.
```

---

## Rollback plan

Если в проде CI красный после merge:
- `REDIS_URL=` (пустая строка → settings parse как None → NullDenylist activate).
- Refresh возвращается в stateless 7-day режим. Старые refresh всё ещё работают как раньше.
- Hotfix зелёным следующим коммитом — debug в спокойной обстановке.

---

## Risks / heads-up

1. **fakeredis 2.20+ asyncio mode**: API через `fakeredis.aioredis.FakeRedis`. Если в pyproject lock'е поедет 2.x старый — миграция на 3.x async может потребовать `FakeAsyncRedis`. Проверю на Step 1.5 install.
2. **redis-py 5.x ConnectionError**: при fail closed на /refresh — пользователь видит 500/503 без объяснения. Endpoint должен ловить `redis.ConnectionError`/`TimeoutError` отдельно и отдавать 503 с `Retry-After`. Sub-decision внутри Task 6.
3. **JTI collision**: `uuid4().hex` — 128-bit, collision-probability negligible. Не валидируем.
4. **Race в Task 6 между `is_denied` и `deny`**: `is_denied` отсекает уже-known reuse, `deny` NX-check ловит параллельный refresh. Между ними окно есть, но `deny` всегда атомарно — окончательный gate. `is_denied` — fast-path для типичных reuse-attempts (старый stolen token).
5. **MFA challenge** не trogal — issue_refresh там просто выдаёт. После rotation первый refresh уже сразу же отработает как rotation. Backward-compat сохраняется.
6. **BFF logout без refresh cookie** (race с expired cookie) — backend logout silently skip denylist, audit пишется. OK.
