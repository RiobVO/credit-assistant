# ADR 0009: Bank Mode auth + APP_MODE-driven router gating

- **Status**: Accepted
- **Date**: 2026-05-11
- **Phase**: 4 (Bank Mode UI, 4.A–4.H)

## Context

PROJECT_BRIEF Section 2 определяет два режима продукта: **Bank Mode** (банковский аналитик
с auth, история заёмщиков) и **Accountant Mode** (бухгалтер локально, без auth, валидация).
Section 9 Phase 4 требует login screen, поиск по ИНН, генерацию досье, историю и PDF.

Нужно:
- одна кодовая база, два режима — переключение без изменений кода;
- bank install: shared endpoints закрыты auth-стеной + audit-trail;
- accountant install: bank-роутов вообще нет (а не «401»);
- production-grade auth pattern для on-premise банковского deployment.

## Decision

### 1. Install-level mode (один режим на инсталляцию)

`config.settings.APP_MODE: Literal["bank", "accountant"] = "accountant"`,
синхронизирован с фронтом через `NEXT_PUBLIC_APP_MODE`.

В `create_app(settings)` подключение роутеров условное:

```python
if settings.app_mode == "bank":
    auth_required = [Depends(get_current_analyst)]
    app.include_router(bank_auth_router)            # /login без guard
    app.include_router(bank_search_router)          # сами вызывают CurrentAnalyst
    app.include_router(bank_history_router)
    app.include_router(dossier_router, dependencies=auth_required)
    app.include_router(dossier_pdf_router, dependencies=auth_required)
    app.include_router(draft_router, dependencies=auth_required)
    app.include_router(soliq_upload_router, dependencies=auth_required)
else:
    app.include_router(dossier_router)              # accountant — без auth
    app.include_router(dossier_pdf_router)
    app.include_router(draft_router)
    app.include_router(soliq_upload_router)
```

`health_router` подключён всегда без guard — для k8s/load-balancer проверок.

### 2. Auth-стек

- **Passwords**: bcrypt cost=12 через native `bcrypt` API (passlib 1.7.x не
  поддерживается с 2020 и ломается на bcrypt 5.x).
- **JWT**: HS256, access TTL 15 мин, refresh TTL 7 дней. `python-jose` с
  явным `typ` claim различает access/refresh — decode валидирует тип,
  чтобы access не пролез на refresh-endpoint.
- **Без ротации refresh** в v1: при использовании refresh-токена выдаётся
  новый access, refresh не инвалидируется. v2 добавит ротацию + denylist.
- **Storage**: таблица `analysts` (email unique, password_hash, role, is_active),
  seed через CLI `python -m interfaces.cli.seed_analysts`.

### 3. AuthnPort (ports & adapters)

`application/ports/authn_port.py` — `Protocol` с одним методом
`authenticate(email, password) -> AnalystIdentity | None`. v1 реализация —
`SeededAuthnAdapter` (AnalystRepository + bcrypt verify). v2 — `LdapAuthnAdapter`
или `OAuthAuthnAdapter`, тот же port. Use case `AuthenticateAnalyst` не знает,
откуда identity.

**Mitigation против user enumeration**: в ветке `user not found` adapter
делает фиктивный `verify()` против пред-вычисленного валидного bcrypt-hash —
время отклика выровнено с веткой «user exists, wrong password».

### 4. Dual dependency: optional + strict

```python
async def get_optional_current_analyst(...) -> AnalystIdentity | None:
    # token absent / invalid / inactive → None (без raise)

async def get_current_analyst(optional: Depends(get_optional_current_analyst)) -> AnalystIdentity:
    if optional is None:
        raise HTTPException(401)
    return optional
```

FastAPI кэширует deps по идентичности callable, поэтому когда router-level
ставит `dependencies=[Depends(get_current_analyst)]` И endpoint берёт
`OptionalAnalyst` — оба разрешаются через один cached call внутреннего
`get_optional_current_analyst`. Хэндлерам передаётся optional, а 401-логика
запускается до handler'а.

В accountant-mode router-level guard не ставится, optional возвращает None,
audit пропускается, `source_mode='accountant'` остаётся дефолтом dossier'а.

### 5. Audit log (append-only)

Таблица `audit_log`: `id`, `analyst_id (nullable)`, `event`, `target_type`,
`target_id`, `payload (JSONB)`, `created_at`. События v1:

- `login`, `login_failed`, `logout`
- `search_borrower` (payload: `masked_inn`, `result: not_found|borrower_only|with_dossier`)
- `view_dossier`, `generate_dossier`, `download_pdf` (target=dossier)

**PII маскировка обязательна**: ИНН пишется как `XXXXX1234` через
`INN.masked` property. Это требование Security Hard Rules в CLAUDE.md.

`analyst_id` nullable для `login_failed` — на момент события аналитик ещё
не идентифицирован, утечь причину «такого email нет vs неверный пароль»
наружу нельзя.

### 6. Source mode на dossier (`source_mode` column)

`dossiers.source_mode: VARCHAR(20) NOT NULL DEFAULT 'accountant'` + nullable
FK `created_by_analyst_id → analysts.id`. Это даёт:

- разделение истории: bank-install видит только bank-mode записи (фильтр
  `source_mode='bank'`);
- аудит-trail на уровне записи: кто из аналитиков сгенерировал досье;
- backward compat: legacy записи (Phase 2/3, без analyst) получают
  `source_mode='accountant'` через `server_default` в миграции.

### 7. Frontend: httpOnly cookies через Next BFF

Backend возвращает JSON-токены, **не cookies** (stateless API под любого
клиента — REST, mobile, etc.). Browser-side обёртка — Next 16 route
handlers `app/api/auth/*`:

- `POST /api/auth/login` — proxy → backend `/api/bank/auth/login` →
  пакует `access_token` в httpOnly cookie `ca_access` (path=`/`,
  maxAge=15м, sameSite=lax, secure в проде) + `refresh_token` в
  `ca_refresh` (path=`/api/auth`, 7д). В JS client попадает только
  `AnalystSummary`.
- `GET /api/auth/me`, `POST /api/auth/refresh`, `POST /api/auth/logout` —
  читают cookie, добавляют `Authorization: Bearer ...` к backend-запросу.
- `GET /api/dossier/[id]/pdf` — BFF проксирует binary stream для PDF
  download (same-origin → cookies сами идут, не CORS).

Next `proxy.ts` (бывший `middleware.ts`, переименован в Next 16) делает
cookie-presence check для `/search` и `/history` — early redirect на
`/login` без round-trip к backend. Реальная JWT-валидация — на backend.

## Consequences

### Положительные

- Одна кодовая база покрывает оба режима без runtime-разветвлений в
  handler'ах. Mode-gating сосредоточен в `create_app` (Python) и
  `proxy.ts` + root `page.tsx` (Next).
- Auth-port готовы для v2 (LDAP/OAuth — новый adapter, ничего не меняется
  в use case или endpoints).
- JWT в httpOnly cookies — XSS-resistant (банковский стандарт), при этом
  backend остаётся stateless и клиентоневедающим.
- Audit-trail встроен в use cases, не в endpoints — переиспользуется
  background-jobs'ами и CLI без дубликата.

### Отрицательные

- Refresh без ротации — `refresh_token` остаётся валидным 7 дней даже
  после logout. v1-приемлемо (cookie удалена → browser не пошлёт),
  но если refresh утечёт — нужна v2-ротация или denylist в Redis.
- BFF proxy в Next добавляет один hop в auth-path. Latency negligible
  (lo interface), но удваивает потенциальные точки отказа.
- `passlib` отброшен в пользу native `bcrypt` (несовместимости в 5.x) —
  чуть менее декларативный API, но проще maintain. Migration на argon2
  через тонкий слой `PasswordHasher` остаётся открытым путём.

## Alternatives considered

- **Sessions в БД / Redis**: классический подход, но добавляет stateful
  backend для read-heavy auth. JWT + проверка `is_active` в БД даёт
  тот же effective revoke без отдельного store.
- **OAuth/OIDC из коробки**: overkill для POC, нет identity provider в
  scope первого банка. AuthnPort оставляет дверь открытой для v2.
- **Один Next-app per mode** (turbo monorepo): правильнее для production,
  но требует двойного CI и release-cycle. Откладываем до первого банка
  (см. brainstorming-сессия Phase 4 design spec, Approach C).
- **Multi-tenant на одной install**: запрещено PROJECT_BRIEF Section 11
  («не делать многотенантность в POC»).
