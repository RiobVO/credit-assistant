"""Фабрика FastAPI-приложения. Используется и в проде, и в тестах."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.constants import APP_NAME, APP_VERSION
from config.logging import configure_logging
from config.settings import Settings, get_settings
from interfaces.api.shared.dossier import router as dossier_router
from interfaces.api.shared.draft import router as draft_router
from interfaces.api.shared.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Собирает FastAPI с middleware и роутерами. Тесты могут передавать свои настройки."""
    settings = settings or get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.app_env != "local")

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="Внутренний инструмент банков для досье МСБ-заёмщиков",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(dossier_router)
    app.include_router(draft_router)
    return app
