"""Health-check endpoint. Не требует аутентификации, нужен для liveness-проб."""

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from config.constants import APP_VERSION

router = APIRouter(tags=["shared"])
logger = structlog.get_logger(__name__)


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    # T3.2: instrumental log — служит «единицей измерения» для проверки
    # correlation_id propagation (request_id из middleware попадает в record
    # через LogRecord-factory). Также удобен как probe в production access-log.
    logger.info("health_check")
    return HealthResponse(status="ok", version=APP_VERSION)
