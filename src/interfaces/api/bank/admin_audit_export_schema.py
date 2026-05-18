"""Pydantic-схема для GET /api/bank/admin/audit-log/export query params."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AuditExportQuery(BaseModel):
    """Query params для CSV-экспорта audit-лога.

    * ``from_``/``to`` — ISO8601 UTC; включительная нижняя граница, исключительная
      верхняя (классический ``[from, to)``).
    * ``event`` — опциональный фильтр по точному совпадению ``audit_log.event``.
    """

    from_: datetime = Field(alias="from")
    to: datetime
    event: str | None = None

    @field_validator("to")
    @classmethod
    def _to_after_from(cls, value: datetime, info: object) -> datetime:
        data = getattr(info, "data", {})
        from_value = data.get("from_") if isinstance(data, dict) else None
        if isinstance(from_value, datetime) and value <= from_value:
            raise ValueError("'to' must be strictly after 'from'")
        return value

    model_config = {"populate_by_name": True}
