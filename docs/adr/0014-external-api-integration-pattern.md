# ADR-0014 — External API integration pattern (CBU as reference)

**Status:** Accepted · **Date:** 2026-05-17 · **Context:** T0.2 (Pre-Demo Roadmap)

## Context

T0.2 (CBU API real integration) — первая external integration в проекте. К моменту демо банку нас будет ещё ≥ 2: CA-DS28 (ГНК public lookup) и T2.4 (faktura.uz). Без зафиксированного pattern каждая интеграция будет «изобретена заново»: разный retry, разный кэш, разный fallback, разные тесты. Это технический долг до того, как код написан.

Public regulatory data (CBU rates, ГНК статус) — на одной полке. Internal partner APIs (faktura.uz) — на другой, но базовая структура та же: external boundary, timeouts, errors, fallback на DB-cached, fallback на static config.

## Decision

Закрепляем единый pattern для всех external integrations:

1. **Folder layout.**
   - HTTP-клиент: `src/infrastructure/external/<service>_client.py` — только I/O, без business logic.
   - DB-кэш: `src/infrastructure/persistence/repositories/<service>_repository.py` поверх Postgres table.
   - Orchestration: `src/application/services/<service>_service.py` — fallback chain.
   - Endpoint: `src/interfaces/api/shared/<group>.py` через DI service.

2. **Fallback chain (template).**

   ```
   env override (ops escape hatch)
     ↓ если нет
   DB row на сегодня (валидный кэш)
     ↓ если нет
   external live fetch → save в DB → return
     ↓ если CBU/GNK/… down
   DB latest (любая дата — last-known good)
     ↓ если DB пустая
   static bootstrap (config/<service>/*.json)
     ↓ если bust
   raise <Service>Error
   ```

   Source enum обязательно сериализуется в response (`env | live | db_cached | manual | fallback`) — клиент видит из какого слоя данные.

3. **Retry / timeout policy.** Tight budget — внешний endpoint не должен подвешивать user-facing API.
   - Timeout per attempt: ≤ 3s.
   - Retries: ≤ 2 (с exponential backoff 0.5s, 1s).
   - Total budget: ≤ 8s. После — fallback на DB cached, не блокировать ответ.

4. **HTTP client lifecycle.** Per-call `async with httpx.AsyncClient(...)`, без global singletons.
   - Endpoint вызывается редко (DB-cache hits в 99% случаев).
   - Connection-pool overhead vs lifecycle complexity не выгоден.
   - Никаких leaks на shutdown.

5. **DB caching.**
   - Granularity: 1 row на «единицу обновления» (день, час — по нативной частоте источника).
   - PK = временной идентификатор (`date` для daily rates, `cert_id` для справок).
   - **`ON CONFLICT (...) DO NOTHING`** на save — конкурентные writes из параллельных requests идемпотентны.
   - `raw_response jsonb` для аудита и forensics. Размер несущественен (≤ 100KB/год для daily rates).
   - Index по `(updated_at DESC)` или эквиваленту для `get_latest()`.

6. **User-Agent identity.** Polite-identification для operations team источника.
   - Формат: `credit-assistant/<version> (+contact:<email>)`.
   - Применимо ко всем outgoing HTTP-вызовам.

7. **Config через env с default.**
   - `CBU_API_URL` / `GNK_API_URL` env переменные с hardcoded default.
   - Покрывает DR (URL changed) и тестовые окружения.

8. **Legal-review checklist** перед каждой новой integration:
   - `robots.txt` источника не disallows endpoint.
   - Crawl-delay соблюдается (если есть).
   - User-Agent identifiable.
   - Узб-юрист 30-минутный review на терms of service / data usage.

9. **Tests.**
   - Unit (mock `httpx.MockTransport`): success, non-200, timeout, malformed JSON, empty payload, retry recovers.
   - Service unit (FakeRepo + mock client): каждая ветка fallback chain.
   - Repository integration (testcontainers Postgres): save → get_for_date → get_latest, ON CONFLICT idempotency.
   - Endpoint integration: mock external client, проверить source enum по каждой ветке.

## Rationale

- **Fallback chain vs «либо API, либо ошибка»**: банк не терпит endpoint 500 из-за внешней системы. Cached/static data старее, но валиднее чем downtime.
- **Per-call client vs singleton**: при низкой частоте singleton — преждевременная оптимизация с lifecycle-долгом.
- **DB-кэш на 1 row/day, не TTL-cache**: дешевле, проще, audit-friendly (raw_response сохраняется).
- **Source enum в response**: frontend знает что показать (фрэш / устаревший / fallback badge) без догадок.
- **ON CONFLICT DO NOTHING vs UPSERT**: для daily rates первый write — истина (CBU не меняет курс задним числом). Второй write бесполезен. UPSERT добавил бы окно для «последний победил» race condition.

## Trade-offs

- **Static bootstrap fallback (`config/exchange/rates.json`)**: устаревает со временем. Требует ручного обновления при cold-start окружениях. Но без него endpoint всегда 503 на empty DB + CBU down — хуже.
- **Retry budget tight**: при flap'ах источника часть запросов всё равно дойдёт до fallback. Acceptable trade-off vs медленный endpoint.
- **`raw_response jsonb`** растёт линейно по времени. На 90+ дней retention — несущественно. Удаление обсуждается в T3 (operational readiness).
- **Per-version layout dispatch для будущих изменений API**: если CBU/ГНК поменяют формат, новая версия client нужна. Не пытаемся universal-parser — лучше явный per-version код.

## Implementation reference

T0.2 (CBU API) — first использование pattern. См. файлы:
- `src/infrastructure/external/cbu_client.py`
- `src/infrastructure/persistence/repositories/usd_rate_repository.py`
- `src/application/services/usd_rate_service.py`
- `src/infrastructure/persistence/migrations/versions/20260517_2000_add_usd_uzs_rates.py`

Будущие T0.3 (ГНК Phase A manual upload — не external, но similar fallback) и CA-DS28 (ГНК Phase B public lookup), T2.4 (faktura.uz) переиспользуют этот pattern целиком.
