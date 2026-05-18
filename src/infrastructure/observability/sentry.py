"""T3.1 — Sentry/GlitchTip SDK initialization + PII scrubbing.

SaaS Sentry запрещён (PROJECT_BRIEF Sec 8): GlitchTip on-prem обслуживает
тот же protocol. ``SENTRY_DSN=None`` → noop SDK (default off в dev).

PII scrubbing — два слоя защиты:
1. ``send_default_pii=False`` — Sentry не шлёт автоматически IP / user.email
   и request body/headers c PII.
2. Custom ``before_send`` — финальный whitelist-фильтр на случай, если PII
   проскочила через breadcrumb / extra / exception args. Маскирует emails
   через единый ``email_mask``.

Sampling:
* ``traces_sample_rate=0`` — performance traces не отправляем (банкам не
  критично, экономия storage).
* errors 100% — каждое исключение должно быть видно.

Logging integration: sentry-sdk автоматически перехватывает stdlib logs >=
ERROR как events и >= INFO как breadcrumbs. Не конфликтует с T3.2
``setLogRecordFactory`` — наша factory срабатывает на ``LogRecord.__init__``,
sentry handler — на ``emit`` (после factory).
"""

from __future__ import annotations

import re
from typing import Any, cast

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.types import Event, Hint

from config.settings import Settings
from infrastructure.auth.email_mask import mask_email

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PII_KEY_RE = re.compile(
    r"(?:password|token|secret|api[_-]?key|authorization|cookie|"
    r"mfa|backup_codes|pii_enc|jwt)",
    re.IGNORECASE,
)


def _scrub_string(value: str) -> str:
    """Маскирует email-адреса в произвольной строке."""
    return _EMAIL_RE.sub(lambda m: mask_email(m.group(0)), value)


def _scrub_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Pop секрет-подобные ключи; маскирует emails в string-значениях."""
    out: dict[str, Any] = {}
    for key, value in d.items():
        if isinstance(key, str) and _PII_KEY_RE.search(key):
            out[key] = "[scrubbed]"
            continue
        if isinstance(value, str):
            out[key] = _scrub_string(value)
        elif isinstance(value, dict):
            out[key] = _scrub_dict(value)
        else:
            out[key] = value
    return out


def _before_send(event: Event, _hint: Hint) -> Event | None:
    """Финальный фильтр перед отправкой event'а в GlitchTip.

    Drop'аем ``request.data`` и ``request.cookies`` — это body POST'ов
    (могут содержать password / financial figures), и cookies (JWT в
    ca_access/ca_refresh). Маскируем emails в breadcrumbs и в extra.
    """
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = _scrub_dict(headers)

    for key in ("extra", "tags", "contexts"):
        value = event.get(key)
        if isinstance(value, dict):
            cast(dict[str, Any], event)[key] = _scrub_dict(value)

    breadcrumbs = event.get("breadcrumbs", {})
    if isinstance(breadcrumbs, dict):
        values = breadcrumbs.get("values")
        if isinstance(values, list):
            for crumb in values:
                if not isinstance(crumb, dict):
                    continue
                msg = crumb.get("message")
                if isinstance(msg, str):
                    crumb["message"] = _scrub_string(msg)
                data = crumb.get("data")
                if isinstance(data, dict):
                    crumb["data"] = _scrub_dict(data)

    return event


def init_sentry(settings: Settings) -> None:
    """Инициализирует Sentry SDK. DSN=None → SDK остаётся noop."""
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.sentry_release,
        send_default_pii=False,
        traces_sample_rate=0.0,
        before_send=_before_send,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
            LoggingIntegration(level=None, event_level=None),
        ],
    )
    # Глобальные tags, привязанные к процессу: brand_id + app_mode позволяют
    # фильтровать события в GlitchTip UI по инсталляции и режиму.
    scope = sentry_sdk.get_isolation_scope()
    scope.set_tag("brand_id", settings.brand_id)
    scope.set_tag("app_mode", settings.app_mode)
    scope.set_tag("app_env", settings.app_env)
