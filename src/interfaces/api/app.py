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

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Callable

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.constants import APP_NAME, APP_VERSION
from config.logging import configure_logging
from config.settings import Settings, get_settings
from infrastructure.brand.brand_config import BrandConfigError, load_brand
from infrastructure.jobs.uptime_collector import uptime_collector_loop
from infrastructure.persistence.database import get_session_factory
from interfaces.api.bank.admin import router as bank_admin_router
from interfaces.api.bank.auth import router as bank_auth_router
from interfaces.api.bank.dependencies import get_current_analyst
from interfaces.api.bank.history import router as bank_history_router
from interfaces.api.bank.mfa import router as bank_mfa_router
from interfaces.api.bank.search import router as bank_search_router
from interfaces.api.bank.stats import router as bank_stats_router
from interfaces.api.shared.data_readiness import router as data_readiness_router
from interfaces.api.shared.dossier import router as dossier_router
from interfaces.api.shared.dossier_pdf import router as dossier_pdf_router
from interfaces.api.shared.draft import router as draft_router
from interfaces.api.shared.gnk_certificate import router as gnk_certificate_router
from interfaces.api.shared.health import router as health_router
from interfaces.api.shared.manual_input_parse import router as manual_input_parse_router
from interfaces.api.shared.soliq_upload import router as soliq_upload_router
from interfaces.api.shared.system import router as system_router

logger = logging.getLogger(__name__)


def _build_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], contextlib.AbstractAsyncContextManager[None]]:
    """Возвращает lifespan-контекст-менеджер для FastAPI.

    CA-DS9: при `uptime_collector_enabled` запускает фоновую задачу, которая
    каждые `uptime_collector_interval_seconds` пишет worst-of-day статус в
    `system_uptime_day`. Это убирает зависимость uptime-calendar от
    user-traffic к `/api/system/health`.

    Для тестов collector отключается флагом (см. Settings) — никаких
    фоновых writes на shared pytest session.
    """

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        task: asyncio.Task[None] | None = None
        if settings.uptime_collector_enabled:
            session_factory = get_session_factory()
            task = asyncio.create_task(
                uptime_collector_loop(
                    session_factory,
                    interval_seconds=settings.uptime_collector_interval_seconds,
                ),
                name="uptime_collector",
            )
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    return lifespan


def _validate_runtime_config(settings: Settings) -> None:
    """Startup-validation для критичных secrets/configs.

    Каждый из них — crash-on-boot guard. Запускать misconfigured production
    молча запрещено.

    * BRAND_ID (T1.4 / ADR-0018): `config/brands/<id>.json` обязан существовать
      и парситься. Иначе single-tenant deployment работает в неопределённом
      контексте — audit-log brand_id и PDF chrome ссылаются на несуществующий
      tenant.
    * PII_ENC_KEYS (T1.3 / ADR-0017): обязателен в staging/prod. Без него
      encryption-at-rest деградирует в passthrough.
    """
    try:
        load_brand(settings.brand_id)
    except BrandConfigError as exc:
        raise RuntimeError(
            f"BRAND_ID={settings.brand_id!r} не резолвится в config/brands/ "
            f"(T1.4 / ADR-0018): {exc}"
        ) from exc

    if settings.app_env in ("staging", "prod") and not settings.pii_enc_keys:
        raise RuntimeError(
            "PII_ENC_KEYS обязателен в staging/prod (T1.3 / ADR-0017). "
            "Generate: python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'"
        )

    # T1.5 (ADR-0019): AUTHN_MODE=ldap требует полный набор LDAP-параметров.
    # Лучше упасть на boot, чем при первом login.
    if settings.authn_mode == "ldap":
        missing = [
            name
            for name, value in (
                ("LDAP_URI", settings.ldap_uri),
                ("LDAP_BASE_DN", settings.ldap_base_dn),
                ("LDAP_BIND_DN", settings.ldap_bind_dn),
                ("LDAP_BIND_PASSWORD", settings.ldap_bind_password),
                ("LDAP_ROLE_ANALYST_GROUP", settings.ldap_role_analyst_group),
                (
                    "LDAP_ROLE_SENIOR_ANALYST_GROUP",
                    settings.ldap_role_senior_analyst_group,
                ),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"AUTHN_MODE=ldap требует переменных окружения: "
                f"{', '.join(missing)}. См. ADR-0019, "
                f"docs/operations/ldap-setup.md."
            )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Собирает FastAPI с middleware и роутерами. Тесты могут передавать свои настройки."""
    settings = settings or get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.app_env != "local")

    _validate_runtime_config(settings)

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="Внутренний инструмент банков для досье МСБ-заёмщиков",
        lifespan=_build_lifespan(settings),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    # system_router — без auth, доступен в обоих режимах. Используется UI
    # Settings → О системе (Phase 5) и k8s/load-balancer probes (как health).
    app.include_router(system_router)

    if settings.app_mode == "bank":
        # Bank Mode: auth-роут открыт (login сам выдаёт токен), всё остальное
        # за строгим guard. Shared endpoints доступны, но требуют валидный JWT
        # и проставляют analyst-id + audit (см. shared/dossier.py).
        auth_required = [Depends(get_current_analyst)]
        app.include_router(bank_auth_router)
        # MFA: enrollment + disable требуют auth (рантайм через CurrentAnalyst в
        # handler'ах); /challenge открыт, защищён через short-lived JWT.
        app.include_router(bank_mfa_router)
        app.include_router(bank_search_router)
        app.include_router(bank_history_router)
        app.include_router(bank_stats_router)
        # Admin endpoints (senior_analyst only) — role-check внутри handler'а,
        # router-level guard на auth достаточно: handler сам поднимет 403
        # если role != senior_analyst.
        app.include_router(bank_admin_router, dependencies=auth_required)
        app.include_router(dossier_router, dependencies=auth_required)
        app.include_router(dossier_pdf_router, dependencies=auth_required)
        app.include_router(draft_router, dependencies=auth_required)
        app.include_router(soliq_upload_router, dependencies=auth_required)
        app.include_router(manual_input_parse_router, dependencies=auth_required)
        app.include_router(data_readiness_router, dependencies=auth_required)
        # T0.3: ГНК-справки — manual upload только в bank mode (compliance audit
        # workflow). Accountant install их не использует — router не подключаем.
        app.include_router(gnk_certificate_router, dependencies=auth_required)
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
