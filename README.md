# Credit Assistant MSB

> Внутренний инструмент банков Узбекистана для автоматизации сбора и предобработки данных МСБ-заёмщиков. См. [`PROJECT_BRIEF.md`](./PROJECT_BRIEF.md) — единственный источник правды по продукту.

## Status

**Pre-demo MVP ready** (ADR-0024 Day 4 closed 2026-05-20). 24 red-flag правил, value objects, entities, BorrowerSnapshot, ScoringService, YAML-конфигурация (`config/rules/v1_uz_msb.yaml`). Подробнее — `CLAUDE.md` и `docs/audit/2026-05-21/00-summary.md`.

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
uv run pytest -q                                # unit + быстрые integration
uv run pytest -q -m "not integration"           # без Docker (быстро)
uv run pytest -q -m integration                 # только testcontainers (нужен Docker Desktop)

# Web
cd web
npm run lint
npx tsc --noEmit
npm run build
```

`integration` маркер гонит тесты против real Postgres из `testcontainers`.
Без поднятого Docker daemon весь пакет `tests/integration/` авто-skip-ается
с понятным reason — основной suite остаётся зелёным.

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
- [`config/rules/v1_uz_msb.yaml`](./config/rules/v1_uz_msb.yaml) — все 24 red-flag правил с metadata

## Как добавить новое правило

1. Создать pure-функцию в `src/domain/rules/<category>/<rule_id_lower>.py`:
   ```python
   # RULE_SOURCE: <ссылка на регуляторику или industry source>
   # CONFIDENCE: HIGH | MEDIUM | LOW
   # VALIDATED_BY: []

   def rule_id_lower(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
       ...
   ```
2. Добавить co-located тест `<rule_id_lower>_test.py` (минимум: positive / negative / edge / missing-data).
3. Зарегистрировать в `src/infrastructure/rules/registry_factory.py`:
   ```python
   from domain.rules.<category>.<rule_id_lower> import rule_id_lower

   CODE_RULES["RULE_ID_UPPER"] = rule_id_lower
   ```
4. Описать в `config/rules/v1_uz_msb.yaml` (id, name, category, severity, source, formula, rationale).
5. Прогнать `uv run pytest -q` — `load_registry()` упадёт, если id не совпадают между кодом и YAML.
