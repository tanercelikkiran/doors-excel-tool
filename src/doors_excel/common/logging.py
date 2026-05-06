"""Loguru logging configuration for doors-excel-tool.

Call ``setup_logging()`` once at application startup before any log messages
are emitted. Subsequent calls are safe (idempotent level registration).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

if TYPE_CHECKING:
    from loguru import Logger

from doors_excel.common.constants import LOG_LEVEL_NOTICE

NOTICE_LEVEL_NAME: str = "NOTICE"
NOTICE_COLOR: str = "<bold><cyan>"
NOTICE_ICON: str = "\U0001f514"  # 🔔

_STDERR_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

_FILE_FORMAT: str = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} - {message}"
)


def setup_logging(
    *,
    log_file: Optional[str] = None,
    level: str = "DEBUG",
    rotation: str = "10 MB",
    retention: str = "14 days",
) -> Logger:
    """Configure Loguru sinks and register the NOTICE level.

    Parameters
    ----------
    log_file:
        Optional path for a rotating file sink. ``None`` = stderr only.
    level:
        Minimum severity for the stderr sink (e.g. ``"DEBUG"``, ``"INFO"``).
    rotation:
        Loguru rotation trigger for the file sink.
    retention:
        Loguru retention policy for the file sink.
    """
    logger.remove()

    try:
        logger.level(
            NOTICE_LEVEL_NAME,
            no=LOG_LEVEL_NOTICE,
            color=NOTICE_COLOR,
            icon=NOTICE_ICON,
        )
    except (TypeError, ValueError):
        pass  # level already registered on a previous call

    logger.add(
        sys.stderr,
        format=_STDERR_FORMAT,
        level=level,
        colorize=True,
    )

    if log_file is not None:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            format=_FILE_FORMAT,
            level=level,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
        )

    return logger
