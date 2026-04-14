"""ASGI entry point. Запуск: `uv run uvicorn --app-dir src interfaces.api.main:app`."""

from interfaces.api.app import create_app

app = create_app()
