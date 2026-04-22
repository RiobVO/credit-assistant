# Phase 4 — Bank Mode UI: Design Spec

> Дата: 2026-05-11. Author: founder + Claude (brainstorming session).
> Source of truth для Phase 4. Утверждено перед стартом 4.A.

---

## 1. Контекст и цель

Реализовать **Bank Mode** поверх существующего ядра (Phase 0–3): отдельный UI для банковского кредитного аналитика с auth, поиском заёмщика по ИНН, генерацией досье и историей. Сохранить Accountant Mode рабочим на той же кодовой базе — переключение через `APP_MODE` env-flag, на инсталляции активен ровно один режим.

PROJECT_BRIEF Section 2 определяет два режима как «два UI поверх одного бизнес-ядра». Section 9 Phase 4: login screen, search by INN, trigger dossier generation, view results + PDF, history.

---

## 2. Решения

### 2.1 Mode switching — install-level

- `APP_MODE: Literal["bank", "accountant"] = "accountant"` в `src/config/settings.py`.
- На bank install accountant-роуты не подключаются (FastAPI `include_router` под условием), и наоборот.
- Frontend: `NEXT_PUBLIC_APP_MODE` управляет root-redirect и middleware-гейтом route groups.
- Одна инсталляция = один режим. Без multi-tenant.

### 2.2 Hybrid search → upload flow

`/search` принимает ИНН:
- найден borrower + dossier → карточка «Досье от <date> — Открыть»;
- найден borrower, dossier нет → «Заёмщик найден, досье не создано. Загрузить выгрузки →»;
- не найден → «Не найден. Загрузить выгрузки для нового заёмщика →».

Upload переиспользует существующие `shared/soliq_upload.py` и `shared/manual-input` — на bank install они работают за `get_current_analyst` зависимостью. После генерации досье в БД проставляется `created_by_analyst_id`.

### 2.3 Auth — JWT seeded analysts

- Таблица `analysts` (id/email/password_hash/full_name/role/created_at/is_active).
- Bcrypt cost=12 через passlib.
- JWT HS256: 15 мин access + 7 дней refresh.
- **Без ротации refresh** в v1. Добавим в v2.
- Токены в **httpOnly secure cookies** через Next route handler-proxy. XSS-resistant, банковский стандарт.
- `JWT_SECRET_KEY` ≥ 32 байт в `.env`, placeholder в `.env.example`.
- Seed CLI: `python -m src.interfaces.cli.seed_analysts --email ... --password ...`.

`AuthnPort` — abstract в `application/`, реализация `SeededAuthnAdapter` в `infrastructure/auth/`. LDAP/OAuth берётся в v2 как новый adapter, port не меняется.

### 2.4 History — global queue + filter «Мои / Все»

- На bank install в истории видны все досье с `source_mode='bank'`.
- Фильтр-чип «Мои» применяет WHERE `created_by_analyst_id = current_analyst.id`.
- НЕ per-analyst RLS — банковский стандарт показывает общую очередь команде.
- Accountant-mode dossiers на bank install не существуют (deployment-level разделение).

### 2.5 Audit log

Append-only таблица `audit_log`:

```python
class AuditLog(Base):
    id: UUID
    analyst_id: UUID
    event: str  # 'login' | 'login_failed' | 'logout' | 'view_dossier'
                # | 'generate_dossier' | 'download_pdf' | 'search_borrower'
    target_type: str | None  # 'dossier' | 'borrower' | None
    target_id: UUID | None
    payload: JSONB  # masked context: маскированный ИНН, ip
    created_at: datetime
```

Записывается из use cases через `AuditLogService`, не из endpoints. ИНН в payload маскируется (`XXXXXX1234`) per Security Hard Rules.

### 2.6 Frontend — Approach A (route groups)

```
web/src/app/
├── (accountant)/           # без изменений
│   ├── manual-input/
│   └── dossier/[id]/       # thin re-export DossierView
└── (bank)/                 # новое
    ├── layout.tsx          # header + sidebar (Поиск / История) + analyst.full_name + Logout
    ├── login/page.tsx
    ├── search/page.tsx
    ├── history/page.tsx
    └── dossier/[id]/page.tsx  # thin re-export DossierView + bank action-bar
```

**DossierView extraction:** внутренности `(accountant)/dossier/[id]/page.tsx` → `web/src/features/dossier/dossier-view.tsx`. Обе route-страницы рендерят его, chrome (action-bar, breadcrumbs) — на уровне route page.

Auth helpers: `web/src/lib/auth/{server,client}.ts`. Next middleware закрывает `(bank)/*` кроме `/login` — проверяет наличие cookie, реальная JWT-валидация на backend через `/auth/me`.

---

## 3. Архитектура слоёв (Clean)

### `domain/`
Без изменений. Analyst — это infrastructure concept (identity), а не business entity.

### `application/`
- `application/ports/authn_port.py` — `AuthnPort.authenticate(email, password) -> AnalystIdentity | None`
- `application/use_cases/authenticate_analyst.py`
- `application/use_cases/list_dossiers.py` — фильтр mine/all, search q, pagination
- `application/use_cases/search_borrower.py` — INN lookup → DossierViewSummary | None
- `application/dto/analyst_identity.py`
- `application/dto/dossier_summary.py`

### `infrastructure/`
- `infrastructure/auth/password_hasher.py` (passlib bcrypt cost=12)
- `infrastructure/auth/jwt_service.py` (python-jose, HS256)
- `infrastructure/auth/seeded_authn_adapter.py`
- `infrastructure/auth/audit_log_service.py`
- `infrastructure/persistence/models/analyst.py`
- `infrastructure/persistence/models/audit_log.py`
- `infrastructure/persistence/repositories/analyst_repository.py`
- `infrastructure/persistence/repositories/audit_log_repository.py`
- Alembic migration: `analysts`, `audit_log`, `dossier.created_by_analyst_id` (nullable FK), `dossier.source_mode` (enum 'bank' | 'accountant', default 'accountant' для существующих)

### `interfaces/`
- `interfaces/api/bank/auth.py` — `POST /api/bank/auth/login`, `POST /api/bank/auth/refresh`, `POST /api/bank/auth/logout`, `GET /api/bank/auth/me`
- `interfaces/api/bank/search.py` — `GET /api/bank/borrowers/search?inn=...`
- `interfaces/api/bank/history.py` — `GET /api/bank/dossiers?filter=mine|all&q=...&page=...&page_size=...`
- `interfaces/api/shared/dependencies.py` — добавляем `get_current_analyst` (Depends → JWT decode + analyst lookup)
- `interfaces/api/main.py` — conditional router include по `APP_MODE`
- `interfaces/cli/seed_analysts.py`

---

## 4. API контракты (черновик)

### `POST /api/bank/auth/login`
Request: `{ "email": str, "password": str }`
Response 200: `{ "access_token": str, "refresh_token": str, "analyst": { id, email, full_name, role } }`
Response 401: `{ "error": "invalid_credentials" }`
Side effect: запись `login` или `login_failed` в audit_log.

### `POST /api/bank/auth/refresh`
Request: `{ "refresh_token": str }`
Response 200: `{ "access_token": str }` (refresh без ротации в v1)
Response 401: `{ "error": "invalid_token" }`

### `GET /api/bank/auth/me`
Header: `Authorization: Bearer <access_token>`
Response 200: `{ id, email, full_name, role }`
Response 401: `{ "error": "unauthorized" }`

### `GET /api/bank/borrowers/search?inn=123456789`
Response 200:
```
{
  "found": bool,
  "borrower_name": str | null,
  "dossier_id": str | null,
  "risk_score": int | null,
  "created_at": ISO8601 | null
}
```
Audit: `search_borrower` с masked ИНН.

### `GET /api/bank/dossiers`
Query: `filter=mine|all` (default `all`), `q` (ИНН или substring имени), `page` (default 1), `page_size` (default 20, max 100).
Response 200:
```
{
  "items": [
    { "dossier_id", "inn", "borrower_name", "risk_score", "created_at", "analyst_name" }
  ],
  "total": int,
  "page": int,
  "page_size": int
}
```

### Существующие `GET /api/dossier/{id}`, `GET /api/dossier/{id}/pdf`, `POST /api/soliq-upload`, `POST /api/manual-input`
На bank install получают зависимость `get_current_analyst`. Сами контракты не меняются. Audit log пишется из use cases.

---

## 5. Atomic decomposition

| ID | Subject | Files (примерно) |
|---|---|---|
| **4.A** | DB & domain: миграция (`analysts`, `audit_log`, `dossier.created_by_analyst_id`, `dossier.source_mode`), ORM, repositories, seed CLI, unit-тесты | ~10 |
| **4.B** | Auth: JWT service, password hasher, AuthnPort + SeededAuthnAdapter, `POST /api/bank/auth/{login,refresh,logout}`, `GET /me`, `get_current_analyst` dependency, integration-тесты на testcontainers | ~8 |
| **4.C** | Bank API endpoints: `bank/borrowers/search`, `bank/dossiers` (list с filter), AuditLogService wiring в существующие endpoints | ~6 |
| **4.D** | Mode gating: `APP_MODE` env, conditional router include в `interfaces/api/main.py`, integration-тест 404 на accountant-роутах при bank install | ~4 |
| **4.E** | Frontend foundation: `(bank)` route group, layout (header+sidebar), login screen, auth client/server helpers, Next middleware, root redirect по `NEXT_PUBLIC_APP_MODE` | ~8 |
| **4.F** | Frontend search & history: `/search` гибридный flow (reuse upload UI), `/history` TanStack Table + filters + pagination | ~6 |
| **4.G** | Dossier view reuse: extract `DossierView` в `features/dossier/`, thin wrappers в обоих route groups, action-bar для bank | ~4 |
| **4.H** | E2E smoke: `docker compose up` + seed analyst + полный путь login → search → upload → dossier → PDF; CLAUDE.md update; ADR-0009 (auth & mode-gating) | docs + smoke |

Каждый блок — отдельный коммит с conventional message (`feat(auth): ...`, `feat(api/bank): ...`).

---

## 6. Definition of Done

- ruff + mypy --strict + tsc + eslint + next build зелёные.
- Новые unit-тесты для `domain`/`application` ≥ 80% lines.
- Integration-тесты с testcontainers Postgres для auth + bank endpoints ≥ 60%.
- Ручной smoke через `docker compose up -d --build api` + `npm run dev`, прохождение полного пути на bank install.
- CLAUDE.md обновлён (Current Status, Активные договорённости).
- ADR-0009 `docs/adr/0009-auth-and-mode-gating.md` написан и закоммичен.

---

## 7. Open items (вне scope v1)

- **TODO[CA-003]** Реальный ГНК lookup — pill «Проверено в ГНК» остаётся по format-валидации.
- LDAP / OAuth — port готов, новый adapter в v2.
- Refresh-token rotation — v2.
- Per-team / per-branch RLS — v2.
- Multi-tenant — out of product scope для POC.

---

## 8. Antipattern guard (PROJECT_BRIEF Section 11)

- ❌ Не используем ChatGPT-style buzzwords в UI (login screen — банковский серьёзный).
- ❌ Не делаем multi-tenant в POC.
- ❌ Не лезем в ML — Bank Mode UI это front + auth + чтение.
- ❌ Не делаем «красивые» анимации — банкиры серьёзные.
- ❌ Не SaaS-зависимости — JWT/bcrypt всё локально.
- ❌ Не публичный GitHub — продолжаем private.
