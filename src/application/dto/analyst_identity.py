"""AnalystIdentity: identity банковского аналитика на application-границе.

Не содержит password_hash — это infrastructure detail. Используется
use case'ами после успешной аутентификации и в `get_current_analyst`
зависимости.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AnalystIdentity:
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
