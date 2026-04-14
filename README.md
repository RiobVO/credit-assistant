# Credit Assistant MSB

> Внутренний инструмент банков Узбекистана для автоматизации сбора и предобработки данных МСБ-заёмщиков. См. [`PROJECT_BRIEF.md`](./PROJECT_BRIEF.md) — единственный источник правды по продукту.

## Status

**Phase 0 — Foundation: complete.** `/health`-эндпоинт, главная страница с проверкой соединения, локальная инфра в Docker Compose, CI на GitHub Actions.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (менеджер Python-зависимостей)
- Node.js 20+
- Docker Desktop (для локальной Postgres + Redis)

## Quick start

```bash
# 1. Python: установить deps и поднять backend
uv sync
cp .env.example .env
uv run uvicorn --app-dir src interfaces.api.main:app --reload

# 2. Frontend (в отдельном терминале)
cd web
npm install
cp .env.local.example .env.local
npm run dev

# 3. Инфраструктура (опционально, нужна с Phase 1)
docker compose up -d postgres redis
```

После старта:
- `http://localhost:8000/health` — backend health
- `http://localhost:8000/docs` — OpenAPI / Swagger
- `http://localhost:3000` — frontend, отображает status backend

## Verification commands

```bash
# Python
uv run ruff check .
uv run mypy src tests
uv run pytest -q

# Web
cd web
npm run lint
npx tsc --noEmit
npm run build
```

## Layout

| Путь | Назначение |
|---|---|
| `src/domain/` | Бизнес-логика без I/O. Pure functions, entities, rules. |
| `src/application/` | Use cases, оркестрация, ports (абстрактные интерфейсы). |
| `src/infrastructure/` | Адаптеры, persistence, отчёты, auth — реализация ports. |
| `src/interfaces/` | API + CLI. Тонкий слой над use cases. |
| `src/config/` | Настройки, логирование, константы. |
| `tests/` | Зеркало `src/`. |
| `web/` | Next.js (App Router) + shadcn/ui. |
| `config/rules/` | YAML с red-flag правилами (Phase 1). |
| `docs/adr/` | Architecture Decision Records. |

См. подробности в `PROJECT_BRIEF.md` Section 4 и `docs/adr/`.

## Documentation

- [`PROJECT_BRIEF.md`](./PROJECT_BRIEF.md) — продуктовый brief, источник правды
- [`CLAUDE.md`](./CLAUDE.md) — статус проекта и рабочие соглашения
- [`docs/adr/`](./docs/adr/) — architecture decision records
