# syntax=docker/dockerfile:1.7
# Backend API image для Credit Assistant.
#
# WeasyPrint (Phase 3.C) тащит native-зависимости (Pango/HarfBuzz/Fontconfig),
# поэтому образ собирается на python:3.12-slim с нужными deb-пакетами. На
# Windows-хосте это единственный путь рендерить PDF локально — см. ADR 0008.

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Native libs для WeasyPrint + curl для healthcheck.
# Pango/HarfBuzz/Fontconfig обязательны — без них падает import weasyprint.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libfontconfig1 \
        fonts-dejavu-core \
        curl \
    && rm -rf /var/lib/apt/lists/*

# uv ставится бинарём, не через pip — так быстрее и не плодит окружения.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app

# Сначала только манифесты — кеш слоя сохранится между сборками,
# пока pyproject.toml/uv.lock не меняются.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Теперь исходники + конфиг Alembic + YAML-правила (registry грузит на старте).
# scripts/ — operational tooling (seed_demo_borrowers, etc.), запускается из
# /app с PYTHONPATH=/app/src. `_smoke_*` остаются вне image (gitignored, dev-only).
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY alembic.ini ./

# Финальная установка проекта (после COPY src — иначе уплыл бы в кеш).
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Entrypoint применяет миграции и поднимает uvicorn. Делать это раздельно
# через compose-команды менее надёжно — health-старт ловит rolled-out схему.
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
