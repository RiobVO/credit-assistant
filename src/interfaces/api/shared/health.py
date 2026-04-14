"""Health-check endpoint. Не требует аутентификации, нужен для liveness-проб."""

from fastapi import APIRouter
from pydantic import BaseModel

from config.constants import APP_VERSION

router = APIRouter(tags=["shared"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=APP_VERSION)
