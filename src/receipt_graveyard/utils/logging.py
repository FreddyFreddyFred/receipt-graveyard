"""JSON logging configuration for the Receipt Graveyard application."""

from __future__ import annotations

import logging
import os
import sys
from typing import TextIO

import structlog

LOG_LEVEL_ENV = "RECEIPT_GRAVEYARD_LOG_LEVEL"
DEFAULT_LOG_LEVEL = "INFO"
_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _resolve_level(level: str | int | None) -> int:
    if level is None:
        level = os.getenv(LOG_LEVEL_ENV, DEFAULT_LOG_LEVEL)
    if isinstance(level, bool):
        raise TypeError("log level must be a name or a standard logging level")
    if isinstance(level, int):
        if level not in _LEVELS.values():
            raise ValueError(f"unsupported log level: {level}")
        return level
    if not isinstance(level, str):
        raise TypeError("log level must be a name or a standard logging level")
    try:
        return _LEVELS[level.strip().upper()]
    except KeyError as exc:
        names = ", ".join(sorted(_LEVELS))
        raise ValueError(f"unsupported log level '{level}'; choose from {names}") from exc


def configure_logging(*, level: str | int | None = None, stream: TextIO | None = None) -> None:
    """Configure structlog JSON output at ``level`` or the environment level.

    ``RECEIPT_GRAVEYARD_LOG_LEVEL`` controls the default and falls back to INFO.
    The optional stream is primarily useful for tests and embedded applications.
    """
    minimum_level = _resolve_level(level)
    processors: list[structlog.typing.Processor] = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(sort_keys=True),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(minimum_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr if stream is None else stream),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger, optionally bound to an application name."""
    logger = structlog.get_logger()
    if name is not None:
        return logger.bind(logger=name)
    return logger
