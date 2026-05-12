"""DI-провайдеры для FastAPI Depends.

RuleRegistry грузится из YAML один раз на процесс (lru_cache). Тесты могут
переопределить через ``app.dependency_overrides`` для inject custom registry.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.usd_rate_service import UsdRateService
from domain.rules.rule import RuleRegistry
from domain.services.scoring_service import ScoringService
from infrastructure.persistence.database import get_session
from infrastructure.persistence.repositories.usd_rate_repository import (
    SqlAlchemyUsdRateRepository,
)
from infrastructure.rules.registry_factory import load_registry

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_RULES_YAML = _REPO_ROOT / "config" / "rules" / "v1_uz_msb.yaml"

# Annotated form для FastAPI Depends — позволяет ruff B008 (запрет на вызов
# в default arg) и переиспользовать тип в нескольких endpoint'ах.
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@lru_cache(maxsize=1)
def get_rule_registry() -> RuleRegistry:
    return load_registry(_DEFAULT_RULES_YAML)


@lru_cache(maxsize=1)
def get_scoring_service() -> ScoringService:
    return ScoringService()


def get_usd_rate_service(session: SessionDep) -> UsdRateService:
    """Per-request factory — repository wraps current session, service composes
    fallback chain (env → DB → CBU → DB cached → JSON). См. T0.2."""
    return UsdRateService(SqlAlchemyUsdRateRepository(session))
