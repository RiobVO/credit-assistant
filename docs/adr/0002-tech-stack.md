# ADR 0002: Tech stack

- **Status**: Accepted
- **Date**: 2026-05-08
- **Phase**: 0

## Context

Брифом (Section 3) зафиксирован стек. Здесь — снимок реальных версий, выбранных при scaffold, и пара отступлений от брифа.

## Decision

### Backend

| Слой | Выбор | Почему |
|---|---|---|
| Язык | Python 3.12 | Async, performance, AI-orchestration friendly. |
| Менеджер deps | `uv` | Быстрее `poetry`/pip, lock-файл, единый бинарь. Бриф разрешал uv или poetry. |
| Web framework | FastAPI 0.136 | Async, OpenAPI из коробки, Pydantic-нативный. |
| Validation | Pydantic v2 + pydantic-settings | Один тип данных от env до API. |
| Логирование | structlog 25 | Structured logs, JSON в проде, без PII заёмщиков. |
| Тесты | pytest + pytest-asyncio + httpx | Стандарт; ASGITransport для in-process E2E. |
| Lint/type | ruff 0.15 + mypy 2.0 (--strict) | Один инструмент линта, mypy strict-режим обязателен. |

### Frontend

| Слой | Выбор | Почему |
|---|---|---|
| Framework | Next.js 16.2 (App Router) | См. отступление ниже. |
| Язык | TypeScript 5 strict | `noEmit` в CI, никакого `any`. |
| UI kit | shadcn/ui + Tailwind 4 | Профессиональный вид без AI-эстетики. |
| State | TanStack Query | Server state. `zustand` подключим, когда появится локальный UI-state. |
| Build/dev | Turbopack (Next 16 default) | Быстрее webpack, активно поддерживается. |

### Infra

| Слой | Выбор | Почему |
|---|---|---|
| Контейнеризация | Docker Compose | Локальные Postgres 16 + Redis 7. Backend пока запускаем локально через uv. |
| CI | GitHub Actions | Два job: python и web. См. `.github/workflows/ci.yml`. |
| Reverse proxy | (не сейчас) | Caddy подключим в production-варианте compose, Phase 6+. |

## Отступления от брифа

1. **Next.js 15 → Next.js 16.2.6.** На дату scaffold (2026-05-08) Next 16 — текущий стабильный. App Router и React 19 сохранены, миграция с 15 минимальная. Бриф писался ранее, версионная цифра — не догма.
2. **`next-intl` отложен.** План Phase 0 предусматривал baseline i18n, но без реальных строк это пустой код. Подключим в Phase 3 (генерация отчётов с ru/uz).
3. **Backend в Docker отложен.** Compose поднимает только Postgres + Redis. Backend Dockerfile — когда появится что упаковывать (Phase 4+).

## Consequences

- Любые изменения tech-stack — через новый ADR с обоснованием.
- Ленивая загрузка тяжёлых deps (WeasyPrint, openpyxl, pandas) — только когда появится их потребитель в Phase 2-3, чтобы не раздувать `pyproject.toml` раньше времени.

## References

- `PROJECT_BRIEF.md` Section 3 — оригинальный список стека.
- `pyproject.toml` — фиксированные версии Python deps.
- `web/package.json` — фиксированные версии web deps.
