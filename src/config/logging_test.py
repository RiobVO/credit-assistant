"""Тесты для T3.2.1: stdlib → structlog bridge через contextvars.

После ``configure_logging`` stdlib-логгеры должны автоматически
проинжектить ключи из ``structlog.contextvars`` в каждый log record —
чтобы legacy call-sites (``logging.getLogger(__name__)``) получали
correlation_id через тот же механизм, что и structlog-call-sites.
"""

from __future__ import annotations

import logging

import pytest
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from config.logging import configure_logging


@pytest.fixture(autouse=True)
def _isolate_contextvars() -> None:
    """Гарантируем чистый contextvar state между тестами."""
    clear_contextvars()


def test_stdlib_logger_without_bind_has_no_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    configure_logging(level="INFO")
    logger = logging.getLogger("ca.test.no_bind")
    with caplog.at_level(logging.INFO, logger="ca.test.no_bind"):
        logger.info("event_without_bind")

    record = caplog.records[-1]
    assert getattr(record, "request_id", None) is None


def test_stdlib_logger_with_bind_emits_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    configure_logging(level="INFO")
    logger = logging.getLogger("ca.test.with_bind")
    bind_contextvars(request_id="abc123")
    with caplog.at_level(logging.INFO, logger="ca.test.with_bind"):
        logger.info("event_with_bind")

    record = caplog.records[-1]
    assert getattr(record, "request_id", None) == "abc123"


def test_configure_logging_idempotent_does_not_duplicate_handlers() -> None:
    """Повторный вызов ``configure_logging`` не должен накапливать handlers.

    ``create_app`` дёргается тестами многократно — без guard'а каждый
    log line печатался бы N раз и handler-list рос неограниченно.
    """
    configure_logging(level="INFO")
    root_handlers_after_first = list(logging.getLogger().handlers)
    configure_logging(level="INFO")
    root_handlers_after_second = list(logging.getLogger().handlers)

    assert len(root_handlers_after_second) == len(root_handlers_after_first)


def test_structlog_logger_with_bind_emits_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """structlog-call-sites должны видеть request_id напрямую через
    ``merge_contextvars`` processor — это уже работало в configure_logging,
    тест защищает от регрессии при изменении processor-chain."""
    configure_logging(level="INFO")
    bind_contextvars(request_id="zzz999")
    logger = structlog.get_logger("ca.test.structlog")
    with caplog.at_level(logging.INFO):
        logger.info("structlog_event")

    record = caplog.records[-1]
    assert getattr(record, "request_id", None) == "zzz999"
