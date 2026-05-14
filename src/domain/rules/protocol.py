"""Контракт правила: pure-функция возвращает факт срабатывания (FiringEvidence) или None.

Метаданные правила (severity, source, id, version) живут в Rule/YAML, а не в самой fn —
правило знает «когда сработать», registry знает «как это описать». Это даёт нам:
* единственный источник правды для severity/source (YAML);
* возможность переиспользовать одну fn с разной severity для разных банков (later);
* fn легко тестировать — она зависит только от снапшота.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from domain.entities.borrower_snapshot import BorrowerSnapshot


@dataclass(frozen=True, slots=True)
class FiringEvidence:
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    # T0.4 follow-up B2: UZ-перевод message. Soft default="" для test-fixtures.
    # Production rule-функции формируют обе строки параллельно (strategy D).
    message_uz: str = ""

    def __hash__(self) -> int:
        return hash(self.message)


type RuleFn = Callable[[BorrowerSnapshot], FiringEvidence | None]
