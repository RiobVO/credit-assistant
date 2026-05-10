#!/usr/bin/env bash
# Поднимает API внутри контейнера: миграции → uvicorn.
# Если миграции не применились — fail-fast, лучше упасть на старте,
# чем отдавать 500 на первом запросе.
set -euo pipefail

echo "[entrypoint] alembic upgrade head"
uv run --no-sync alembic upgrade head

echo "[entrypoint] uvicorn interfaces.api.main:app on 0.0.0.0:8000"
exec uv run --no-sync uvicorn \
    interfaces.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --app-dir src
