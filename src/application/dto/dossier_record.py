"""DossierRecord: запись досье для persistence слоя.

Domain не имеет отдельной сущности Dossier (досье — это композиция результата
прогона правил поверх snapshot). Этот DTO собирает поля, которые сохраняются
в `dossiers`-таблице, без привязки к ORM.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.entities.red_flag import RedFlag


@dataclass(frozen=True, slots=True)
class DossierRecord:
    score: int
    recommendation: str  # approve / review / reject
    severity_breakdown: dict[str, int]
    red_flags: tuple[RedFlag, ...]
    rules_version: str
    rules_evaluated: int
