# ADR-0018 — Multi-tenant runtime isolation (Approach A: single-tenant per deployment)

**Status:** Accepted · **Date:** 2026-05-18 · **Context:** T1.4 (Pre-Demo Roadmap)

## Context

PROJECT_BRIEF Section 11 фиксирует архитектурный принцип: «не делать многотенантность в POC — один банк = одна установка». Каждый bank-инстанс получает собственную установку с собственной БД, secrets и infrastructure.

Pre-T1.4 brand-context уже частично присутствует в коде:
- `BRAND_ID` env читается во фронтенде (`web/src/lib/config.ts`, `app/layout.tsx`) для `<html data-brand>` и `BrandProvider`.
- Backend PDF use case вызывает `load_brand()` из `infrastructure/brand/brand_config.py` для tenant-aware шапки досье (Phase 10).
- `config/brands/{default,uzbekbank}.json` — single source of truth для имени банка, primary-цвета, support-контактов, business hours, optional `defaultLang`.

Чего не хватало:
1. **Startup-sanity**: ничто не гарантирует, что `BRAND_ID` env соответствует существующему `config/brands/<id>.json`. Misconfigured deploy запускался молча, frontend ловил error на runtime при первом PDF-рендере.
2. **Audit forensics**: `audit_log` без brand-метки — если оператор ошибочно подключит API одного банка к чужой БД (`DATABASE_URL` miswire), нет способа постфактум обнаружить cross-contamination в логах.
3. **Operations playbook**: нет документа, объясняющего как развернуть 2+ инстансов на одной dev-машине без shared state.

## Decision

**Approach A pure — single-tenant per deployment, defense-in-depth для critical configs.**

### Что добавляется

1. **`Settings.brand_id`** (pydantic-settings) — env `BRAND_ID`, default `"default"`. Single source of truth для backend.
2. **`load_brand(brand_id)` mandatory argument** — env fallback внутри loader удалён. Call-sites обязаны явно пробрасывать `settings.brand_id` (или partial-binding на DI-уровне).
3. **`_validate_runtime_config(settings)` helper в `interfaces/api/app.py`** — обобщает crash-on-boot guards. На текущий момент:
   - `BRAND_ID`: пытаемся `load_brand(settings.brand_id)`, при `BrandConfigError` → `RuntimeError("BRAND_ID=... не резолвится")`.
   - `PII_ENC_KEYS` (T1.3 / ADR-0017): обязателен в `staging`/`prod`. Логика перенесена сюда из inline-check.
4. **`audit_log.brand_id`** (T1.4.2) — VARCHAR(50), NOT NULL DEFAULT `'default'`, indexed `(brand_id, created_at)`. Проставляется из `settings.brand_id` в `audit_log_repository.record(...)`. Backfill `'default'` для existing rows. Forensics use-case: SQL `SELECT DISTINCT brand_id FROM audit_log WHERE created_at > now() - interval '24h'` — обнаруживает cross-contamination за один запрос.
5. **`docs/operations/multi-tenant-deploy.md`** (T1.4.3) — playbook: одна команда `BRAND_ID=<brand> docker compose --project-name <brand> up` на инстанс банка, с offset-портами и separate volumes.

### Что НЕ добавляется (явно out of scope)

- **`brand_id` в `borrowers/dossiers/snapshots/drafts/analysts`** — Approach A полагается на DB-level isolation через separate Postgres контейнеры (compose-project per brand, отдельный volume). Колонка не несёт security value (всегда = `settings.brand_id`), но добавляет cost для миграций и каждой query. Если future shared-DB requirement появится (T2+ или post-demo), добавляется отдельным таском.
- **Cross-tenant SQL guard middleware** — anti-pattern для single-tenant. Magic implicit filter создаёт ложное чувство safety.
- **Runtime brand-switching** — `Settings` singleton кэшируется на process lifetime, brand-id фиксирован. Сменить — restart процесса.

## Rationale

| Approach | Изоляция | Code complexity | Aligns with Sec 11? |
|---|---|---|---|
| **A pure (выбран)** | DB-level через separate Postgres | Минимум (1 колонка для forensics) | ✅ «One bank = one install» |
| B shared-DB row-filter | SQL `WHERE brand_id = ?` | Высокий (N callsites, magic middleware risk) | ❌ Конфликт с anti-pattern |
| C hybrid (Approach A + defensive row filters) | DB-level + redundant row guard | Средний | △ Гибрид с overhead без чёткой угрозы |

**Approach A** соответствует PROJECT_BRIEF Sec 11 буквально. Единственная stable threat-модель для single-tenant — операторская ошибка `DATABASE_URL` (подключение к чужой БД). Решение — `BRAND_ID` mismatch обнаруживается через `audit_log.brand_id` postfactum, не через runtime SQL guard (который только маскирует проблему).

Generalize `_validate_runtime_config` — startup-validation будет расти (BRAND_ID, PII_ENC_KEYS, в будущем LDAP-bind, JWT_SECRET strength). Helper держит логику в одном месте, упрощает дальнейшие добавления.

## Trade-offs

- **No automatic guard для cross-tenant query**: если будущий разработчик случайно подключит API banc-A к БД banc-B (miswire `DATABASE_URL`), endpoint вернёт чужие данные. Defence-in-depth ограничивается audit-log trail. Acceptable: separate-compose-project deploy сводит риск к procedurally-correct deploy; для production используется secrets management (per-brand env files), которое не позволяет accidentally cross-mount.
- **`audit_log.brand_id` DEFAULT `'default'`** для backfill: existing rows записаны без brand-метки, считаем их `'default'` (что правда — мы пока с одним инстансом). Forensics для прошлого периода ограничен, но новые записи защищены.
- **`load_brand` без env-fallback**: каждый новый call-site обязан явно пробросить `settings.brand_id`. Не позволяет «забыть» и получить `'default'` — это feature, не bug.

## Implementation notes

- Settings.brand_id: `str = "default"`. На staging/prod рекомендуется явный override через `.env`/secrets.
- `_validate_runtime_config` зовётся в `create_app` перед `FastAPI(...)`. Тесты `app_test.py` покрывают: missing brand file → RuntimeError; missing PII keys в prod → RuntimeError; happy path для `default`/`uzbekbank`.
- DI для PDF endpoint: `partial(load_brand, settings.brand_id)` — sсhо use case `RenderDossierPdf` принимает `brand_loader: Callable[[], BrandConfig]`.
- Audit-log wiring: 5 callsite'ов — `mfa.py`, `auth.py`, `admin.py`, `search.py`, `authenticate_analyst.py`. Каждый получает `settings.brand_id` через DI или `get_settings()` call.

## Operations playbook

См. `docs/operations/multi-tenant-deploy.md`.

Acceptance: 2 compose-project'а на одной dev-машине (`uzbekbank` + `default`) с offset-портами (`8000`/`8001`, `5433`/`5434`, `6379`/`6380`), separate volumes, separate `.env`. Запросы между инстансами изолированы на network-level (compose project network) и DB-level (раздельные volumes).

## Future work

- LDAP/OAuth (T1.5) добавит `_validate_runtime_config` checks на bind credentials.
- Если будущий клиент потребует shared-DB multi-tenant (например, white-label SaaS для group of banks) — добавляется отдельный ADR с миграцией на `brand_id` колонки + middleware.
- Audit-log export (T3.5) фильтрует по `brand_id` для regulatory отчётов per-bank.
