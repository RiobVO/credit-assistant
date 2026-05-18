"""Конфигурация structlog + stdlib bridge.

T3.2 (correlation_id): structlog и stdlib-логгеры **должны делить один**
processor pipeline — иначе legacy ``logging.getLogger(__name__)`` call-sites
(16 файлов на момент T3.2) не получают ``request_id`` из
``structlog.contextvars`` и audit-trail разваливается.

Решение — ``structlog.stdlib.ProcessorFormatter``:
* root logger получает один StreamHandler с этим formatter'ом;
* structlog wrapping использует ``LoggerFactory()`` → пишет в stdlib;
* ``foreign_pre_chain`` прогоняет stdlib records через тот же набор
  processors (включая ``merge_contextvars``), что и structlog records.

Renderer: JSON для не-local окружений, console для local.

``configure_logging`` идемпотентен (тесты дёргают его многократно):
root-handlers чистятся перед добавлением — иначе каждый log line
печатался бы N раз.
"""

import logging
from typing import Any

import structlog

_CONFIGURED = False


def _install_contextvars_factory() -> None:
    """Глобальный hook на создание ``LogRecord``: инжектит ключи из
    ``structlog.contextvars`` в каждый record.

    Почему factory, а не ``logging.Filter`` на root:
    * filters на logger applied только к records, эмитируемым **самим**
      этим logger'ом — propagated records от child loggers их минуют
      (Python design, см. docs ``logging.Logger.filter``);
    * filter на каждом handler работает, но caplog/Sentry/любой downstream
      handler динамичен — пришлось бы хукать addHandler;
    * setLogRecordFactory — единая точка, отрабатывает на ``LogRecord.__init__``
      ещё до filters/handlers и для structlog (через stdlib LoggerFactory),
      и для legacy ``getLogger().info(...)``.

    Не перетираем явные атрибуты — ``extra={}`` на call-site приоритетнее
    contextvar (точнее знает локальный контекст).
    """
    base_factory = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = base_factory(*args, **kwargs)
        for key, value in structlog.contextvars.get_contextvars().items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return record

    logging.setLogRecordFactory(factory)


def _shared_processors() -> list[Any]:
    """Pre-chain, общий для structlog и stdlib-foreign records.

    ``merge_contextvars`` — единая точка для T3.2 request_id propagation.
    ``add_log_level`` / ``TimeStamper`` / ``StackInfoRenderer`` /
    ``format_exc_info`` зеркалят прежнюю configure_logging.
    """
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]


def configure_logging(level: str = "INFO", *, json_logs: bool = False) -> None:
    """Настраивает structlog + stdlib глобально. Безопасно вызывать многократно.

    Idempotency: первый вызов делает полную настройку (handler + structlog
    configure). Повторные вызовы обновляют только log-level — это страхует
    от двух регрессий:
    * накопление duplicate-handlers (каждый log line печатался бы N раз);
    * снос pytest ``caplog``-handler'а при повторной инициализации, из-за
      которого тесты переставали видеть records.
    """
    global _CONFIGURED
    log_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    if _CONFIGURED:
        return

    shared = _shared_processors()

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    # stdlib root: один StreamHandler через ProcessorFormatter.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root.addHandler(handler)
    _install_contextvars_factory()

    # structlog wrapping — пишет в stdlib (LoggerFactory). Processors
    # завершаются wrap_for_formatter, который передаёт event_dict в
    # ProcessorFormatter.
    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True
