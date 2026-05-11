"""Фабрика FastAPI-приложения. Используется и в проде, и в тестах.

Phase 4.D: маршруты подключаются условно по ``settings.app_mode``:
* ``bank``: bank-routers (auth/search/history) + shared-routers с строгим
  ``get_current_analyst`` на router-уровне → 401 на любую попытку без токена.
* ``accountant``: только shared-routers без auth. Bank-маршрутов нет вовсе
  (запрос → 404), что соответствует «одна инсталляция = один режим» из
  PROJECT_BRIEF Section 2.

Health endpoint доступен в обоих режимах без auth — для k8s/load-balancer
проверок.
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.constants import APP_NAME, APP_VERSION
from config.logging import configure_logging
from config.settings import Settings, get_settings
from interfaces.api.bank.auth import router as bank_auth_router
from interfaces.api.bank.dependencies import get_current_analyst
from interfaces.api.bank.history import router as bank_history_router
from interfaces.api.bank.search import router as bank_search_router
from interfaces.api.shared.data_readiness import router as data_readiness_router
from interfaces.api.shared.dossier import router as dossier_router
from interfaces.api.shared.dossier_pdf import router as dossier_pdf_router
from interfaces.api.shared.draft import router as draft_router
from interfaces.api.shared.health import router as health_router
from interfaces.api.shared.manual_input_parse import router as manual_input_parse_router
from interfaces.api.shared.soliq_upload import router as soliq_upload_router


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

    if settings.app_mode == "bank":
        # Bank Mode: auth-роут открыт (login сам выдаёт токен), всё остальное
        # за строгим guard. Shared endpoints доступны, но требуют валидный JWT
        # и проставляют analyst-id + audit (см. shared/dossier.py).
        auth_required = [Depends(get_current_analyst)]
        app.include_router(bank_auth_router)
        app.include_router(bank_search_router)
        app.include_router(bank_history_router)
        app.include_router(dossier_router, dependencies=auth_required)
        app.include_router(dossier_pdf_router, dependencies=auth_required)
        app.include_router(draft_router, dependencies=auth_required)
        app.include_router(soliq_upload_router, dependencies=auth_required)
        app.include_router(manual_input_parse_router, dependencies=auth_required)
        app.include_router(data_readiness_router, dependencies=auth_required)
    else:
        # Accountant Mode: bank-роуты не подключаются. Shared — без auth,
        # OptionalAnalyst в handler'ах возвращает None → audit пропускается.
        app.include_router(dossier_router)
        app.include_router(dossier_pdf_router)
        app.include_router(draft_router)
        app.include_router(soliq_upload_router)
        app.include_router(manual_input_parse_router)
        app.include_router(data_readiness_router)

    return app
