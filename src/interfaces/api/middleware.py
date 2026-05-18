"""T3.2 — ``RequestIDMiddleware``.

Для каждого запроса:
* читает ``X-Request-ID`` header; если нет — генерирует ``uuid.uuid4().hex``;
* биндит ``request_id`` в ``structlog.contextvars`` — все log records
  внутри handler-цепочки (use-case, repository, adapter) получают этот ID
  через ``LogRecord``-factory из ``config/logging.py``;
* echo обратно в response header — analyst видит ID в DevTools и
  передаёт в support / Sentry поиск;
* unbind в ``finally`` — между запросами context чистый, ничего не течёт.

ID-формат — 32 hex chars (uuid4 без dashes). Header — ``X-Request-ID``
(Heroku/AWS convention).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import sentry_sdk
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from structlog.contextvars import bind_contextvars, unbind_contextvars

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp


REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        bind_contextvars(request_id=rid)
        # T3.1: tag для GlitchTip — если Sentry SDK активен, событие
        # получит request_id в tag-секции (поверх логов в structured logs).
        # Без активного SDK — noop.
        sentry_sdk.get_current_scope().set_tag("request_id", rid)
        try:
            response = await call_next(request)
        finally:
            unbind_contextvars("request_id")
        response.headers[REQUEST_ID_HEADER] = rid
        return response
