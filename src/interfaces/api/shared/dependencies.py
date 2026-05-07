"""DI-провайдеры для FastAPI Depends.

RuleRegistry грузится из YAML один раз на процесс (lru_cache). Тесты могут
переопределить через ``app.dependency_overrides`` для inject custom registry.
"""

from functools import lru_cache
from pathlib import Path

from domain.rules.rule import RuleRegistry
from domain.services.scoring_service import ScoringService
from infrastructure.rules.registry_factory import load_registry

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_RULES_YAML = _REPO_ROOT / "config" / "rules" / "v1_uz_msb.yaml"


@lru_cache(maxsize=1)
def get_rule_registry() -> RuleRegistry:
    return load_registry(_DEFAULT_RULES_YAML)


@lru_cache(maxsize=1)
def get_scoring_service() -> ScoringService:
    return ScoringService()
