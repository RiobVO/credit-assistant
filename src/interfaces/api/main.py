"""ASGI entry point. Запуск: `uv run uvicorn --app-dir src interfaces.api.main:app`.

Windows event-loop fix должен быть применён ДО создания любого asyncpg-соединения,
поэтому импорт ``create_app`` идёт после ``set_event_loop_policy``.
"""

from __future__ import annotations

import asyncio
import sys

# Windows: дефолтный ProactorEventLoop несовместим с asyncpg —
# соединение рвётся в момент handshake.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from interfaces.api.app import create_app

app = create_app()
