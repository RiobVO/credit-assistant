# ADR 0005: Auth черновиков формы по знанию UUID

- **Status**: Accepted (для Phase 2). Подлежит замене в Phase 4.
- **Date**: 2026-05-08
- **Phase**: 2 (persistence)

## Context

Phase 2.5.6 ввёл endpoints `/api/manual-input/draft` (POST/GET/PUT) для частичного сохранения формы досье в Accountant Mode. Бухгалтер заполняет форму в 3 шага, drafts сохраняются автоматически на переходах step 1→2, 2→3 (Phase 2.5.6.b).

В Phase 2 нет аутентификации пользователей: Accountant Mode задумывается как локальный режим (один бухгалтер на инстанс). Bank Mode с SSO появится в Phase 4. До тех пор draft-у нужна модель доступа, которая:

1. Не требует пользователей в БД (их нет).
2. Не блокирует автосейв на бэкенде «check session, redirect to login».
3. Не оставляет за собой долгий шлейф persistent-данных, если бухгалтер бросил черновик.
4. Не растёт линейно по утечкам — потерянная ссылка не равна катастрофе.

Альтернативы:

- **(A) Cookie-based session.** Минус: накладывает auth-инфраструктуру на Phase 2; на той же машине несколько вкладок = шарят cookie = шарят drafts; никак не работает в режиме «передал ссылку на черновик папе».
- **(B) Owner = client-side fingerprint (browser id).** Минус: false sense of security; легко подменяется, не аудируется.
- **(C, выбрано) Auth по знанию UUID + TTL 30 дней.** Кто знает `draft_id`, тот владелец. Без owner-поля.

## Decision

1. **Идентификатор**: `draft_id: UUID4`. 122 бита энтропии — brute-force через URL-пространство практически невозможен.
2. **Отсутствие owner**: в `drafts` нет колонки `owner_user_id`. Любой клиент с валидным UUID получает payload через GET и обновляет через PUT.
3. **TTL = 30 дней** (`Settings.draft_ttl_days`):
   - На каждом POST/PUT — `expires_at = now() + draft_ttl_days`.
   - GET для истёкшего draft возвращает 404 (строка может ещё лежать в БД).
   - `purge_expired()` удаляет истёкшие; вызов — пока ручной (см. Open items).
4. **Payload — `dict[str, Any]` без strict-валидации**: UI шлёт partial формы по ходу заполнения. Контракт проверяется только финальным `POST /api/manual-input`.
5. **Без чувствительных PII в Phase 2**: payload — это входные данные формы досье (ИНН заёмщика, его наименование, фин. показатели). ИНН юрлица — публичная информация (есть в открытых реестрах). Личных данных бухгалтера в payload нет. См. Section 8 PROJECT_BRIEF.md, security hard rules.

## Угрозы и mitigation

| Угроза | Реалистичность | Mitigation |
|---|---|---|
| Brute-force через URL space | Практически 0 (2^122 ID) | TTL=30d ограничивает живой пул |
| Утечка ссылки через логи | Средняя | UUID не пишется в access-логи (отдельная задача DoD); никогда не логируется payload |
| Утечка ссылки через шеринг URL | Низкая для целевого пользователя (свой инстанс) | TTL=30d; в Phase 4 заменяется на session auth |
| Перебор истёкших drafts | Низкая (404 неотличим от «не было») | get-фильтр по `expires_at > now()` атомарен |
| Накопление мусора в БД | Средняя при росте использования | `SqlAlchemyDraftRepository.purge_expired()` готов; cron/ARQ — Phase 4 |

## Что НЕ покрыто этим ADR

- **Rate-limit** на endpoints — отдельная задача (slowapi) перед production.
- **Audit log** доступа к draft — нужен в Bank Mode, не в Accountant Mode.
- **Encryption at rest** — задача deployment-уровня (Postgres TDE / encrypted volume), не приложения.

## Phase 4 plan (Bank Mode)

Когда появится Bank SSO:

1. Добавить колонку `drafts.owner_user_id: UUID NOT NULL` (миграция с дефолтом для существующих строк = `NIL_UUID`, потом not null).
2. Endpoints читают `current_user` из JWT, проверяют `draft.owner_user_id == current_user.id`.
3. UUID-only auth остаётся валидным fallback для Accountant Mode (отдельный installer без SSO).
4. Bank Mode приживёт scheduled `purge_expired` через ARQ; пока — ручной запуск или manual cron.

## Phase 2 persistence — Definition of Done

| Item | Status | Где |
|---|---|---|
| Async SQLAlchemy 2.0 + asyncpg engine | ✅ | `src/infrastructure/persistence/database.py` |
| Alembic init + reversible миграция | ✅ | `migrations/versions/1e51c05eab8c_initial_schema.py` (smoke `upgrade head → downgrade base → upgrade head` пройден в 2.5.3) |
| 4 ORM модели (borrower, snapshot, dossier, draft) | ✅ | `src/infrastructure/persistence/models/` |
| 4 порта в application/ + 4 SQLAlchemy-репозитория | ✅ | `application/ports/`, `infrastructure/persistence/repositories/` |
| Mappers domain ↔ ORM с детерминированным JSONB | ✅ | `infrastructure/persistence/mappers/` |
| `_json_default` обрабатывает Decimal + date/datetime | ✅ | bug-find в 2.5.7 — закрыт `isinstance(obj, datetime \| date) → isoformat()` |
| `POST /api/manual-input` персистит borrower+snapshot+dossier одной транзакцией | ✅ | `interfaces/api/shared/dossier.py` через `DossierStorage` (DI) |
| Drafts API: POST/GET/PUT с TTL | ✅ | `interfaces/api/shared/draft.py` |
| Frontend draft integration (`useFormDraft`) | ✅ | `web/src/app/(accountant)/manual-input/_hooks/use-form-draft.ts` |
| Integration tests против real Postgres (testcontainers) | ✅ | `tests/integration/` — 17 тестов, в т.ч. e2e API |
| ADR-фиксация модели auth для drafts | ✅ | этот документ |
| `LoanRequest` VO end-to-end (CA-005) | ✅ | закрыт в 2.5.5 |
| Hydration mismatch на caseId (CA-007) | ✅ | закрыт коммитом `18eeb74` |

## Open items (не блокируют закрытие 2.5)

- **TODO[CA-006]**: дубль `ix_borrowers_inn` рядом с `UniqueConstraint("inn")` (`borrowers_inn_key`). Косметика, отдельной миграцией перед production deploy.
- **TODO[CA-003]**: реальный лукап ГНК для ИНН — UI-зона.
- **TODO[CA-004]**: per-year taxes UI на Шаге 2 — UI-зона.
- **purge_expired scheduling**: метод `SqlAlchemyDraftRepository.purge_expired()` реализован и протестирован, но не вызывается scheduled job'ом. До Phase 4 — ручной запуск (`uv run python -c "from infrastructure.persistence.repositories.draft_repository import SqlAlchemyDraftRepository; ..."`).
- **Rate-limit / audit log**: production-readiness, не Phase 2 scope.

## References

- `PROJECT_BRIEF.md` Section 8 — Security hard rules; Section 9 — Phase 2 roadmap.
- `CLAUDE.md` — Phase 2 декомпозиция и договорённости.
- `src/interfaces/api/shared/draft.py` — endpoints.
- `src/infrastructure/persistence/repositories/draft_repository.py` — repo с TTL и purge.
- `tests/integration/persistence/draft_repository_test.py` + `tests/integration/api/manual_input_e2e_test.py` — покрытие.
