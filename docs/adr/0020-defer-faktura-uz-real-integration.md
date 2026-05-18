# ADR-0020 — Defer faktura.uz real integration until bank-provided token

**Status:** Accepted · **Date:** 2026-05-18 · **Context:** T2.4 (Pre-Demo Roadmap)

## Context

api.faktura.uz — узбекский B2B-сервис электронных счетов-фактур (ЭСФ). Предоставляет JSON-выгрузки реестра ЭСФ для конкретного ЮЛ при наличии OAuth-токена владельца этого ЮЛ. Сценарий выдачи токена:

1. Банк-клиент договаривается с заёмщиком о доступе к faktura.uz tenant.
2. Заёмщик подтверждает доступ через ЭЦП / corporate identity.
3. Банк передаёт OAuth-токен в Credit Assistant (через secure config или Vault).
4. Credit Assistant использует токен для daily ESF-выгрузок.

Сейчас (до пилот-банка) у нас нет:
- Действующего OAuth-приложения зарегистрированного в faktura.uz.
- Реальных токенов для тестирования.
- Документации API (api.faktura.uz/help требует tenant-аккаунта).
- Real-data fixtures для regression тестов.

Параллельный путь поступления ESF — Excel-выгрузка реестра счетов-фактур (Приложение №4) из my3.soliq.uz. Этот путь:
- Работает на real-data (4 фирмы × VAT_REGISTRY_ILOVA fixtures).
- Не требует OAuth-токена — заёмщик/банк выгружает Excel и загружает в Credit Assistant.
- Покрыт парсером `vat_registry_parser.py` (T0.5 + T2.1).
- Использует ту же бизнес-логику ESF (counterparty / amount_excl_vat / vat_amount).

В roadmap CA-DS11 значится как «`/api/system/health` всегда `not_implemented`». Это messaging gap, а не функциональный — UI показывает «В разработке» badge, что вводит в заблуждение («скоро будет», но на самом деле — «только когда банк даст токен»).

## Decision

**Не реализуем real client для faktura.uz до прихода пилот-банка с OAuth-токеном.** Вместо этого делаем honest stub:

1. `/api/system/health` faktura_uz tip обновлён: явное упоминание OAuth-токена и альтернативного пути (Soliq Excel).
2. Frontend badge `service_status_not_implemented` переименован: «В разработке» → «Опционально», «Ishlab chiqilmoqda» → «Ixtiyoriy». Status enum в API contract не меняется.
3. Real-client integration переезжает в backlog как **T2.4b** с pre-condition: «банк-пилот предоставил OAuth-токен для тестового ЮЛ».
4. Когда T2.4b активируется — реализация **полностью переиспользует ADR-0014 pattern** (`infrastructure/external/faktura_client.py` + `esf_repository.py` + `esf_service.py` + endpoint, fallback chain env → DB → live → cached → static).

## Rationale

- **Mock-only client без real-data = fake-green risk.** Мы не знаем точного формата JSON-выгрузки api.faktura.uz. Тесты на mock с придуманным форматом дают ложное confidence: когда придёт настоящий OAuth-токен с настоящим payload, придётся переписывать client под реальный формат. Хуже всего — переписывать ассерты, которые сейчас выглядят зелёными.
- **Demo для банков не требует faktura.uz.** Excel-путь полностью закрывает MVP-need: ESF parser работает, real fixtures от папы есть, integration smoke прошёл. Банк-пилот сначала увидит работающий продукт, а уже потом решит — давать ли OAuth-токен для real-time выгрузки.
- **Опциональность лучше отражает реальность.** «Опционально» = «дополнительный канал данных, который банк может включить если хочет». «В разработке» = «мы скоро доделаем». Первое честное, второе — обещание, которое мы не контролируем (зависит от tenant-аккаунта банка).
- **ADR-0014 pattern уже отработан** (T0.2 CBU + T0.3 ГНК Phase A). Когда T2.4b активируется, scope понятен и измерим — 4-5 коммитов по шаблону.

## Trade-offs

- **`not_implemented` остаётся в API contract.** Альтернатива — переименовать в `optional`. Не делаем потому что: (1) frontend rendering завязан на `not_implemented` enum value в `about-section.tsx` + `use-system-health.ts`; (2) `system_uptime_repository.NOT_IMPLEMENTED_STATUS` использует тот же sentinel и завязан на uptime-calendar агрегацию; (3) переименование — invasive рефактор без user-facing payoff (badge label поменялся, enum остался).
- **Frontend amber tone остаётся** (`isWarn` branch включает `not_implemented`). Это потенциально misleading — «опционально» не ошибка. Возможный follow-up: разделить tone — `not_implemented` → neutral info-style. Откладываем как visual UX-таск, scope T2.4 — messaging only.
- **CA-DS11 формально не закрывает full integration**, только messaging gap. Тот, кто прочитает roadmap год спустя, должен понять: T2.4 == honest stub, T2.4b == real client. См. backlog entry.

## Implementation reference

T2.4.1 (`b7b96df`) — honest stub messaging + frontend i18n update.

Когда T2.4b активируется:
- `src/infrastructure/external/faktura_client.py` — OAuth client, per-call `httpx.AsyncClient`, token из `FAKTURA_OAUTH_TOKEN` env (или Vault в production).
- `src/infrastructure/persistence/repositories/esf_repository.py` — DB-кэш реестра ЭСФ (PK = `(inn, date)`).
- `src/application/services/esf_service.py` — fallback chain (env → DB today → live → DB latest → ManualUpload).
- `src/interfaces/api/shared/...` — endpoint, integrated в parse_manual_input_files flow.
- ADR-0014 чек-лист: User-Agent, timeout ≤3s, retry ≤2, legal review faktura.uz ToS.
- Status `not_implemented` в health endpoint при активации меняется на `ok` (или `degraded` при token expiry).
