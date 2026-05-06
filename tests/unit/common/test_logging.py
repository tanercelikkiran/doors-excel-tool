"""Unit tests for Loguru-based logging setup with custom NOTICE level."""
from __future__ import annotations

import pathlib

import pytest
from loguru import logger

from doors_excel.common.constants import LOG_LEVEL_NOTICE
from doors_excel.common.logging import (
    NOTICE_COLOR,
    NOTICE_ICON,
    NOTICE_LEVEL_NAME,
    setup_logging,
)


class TestNoticeConstants:
    def test_level_name_is_NOTICE(self) -> None:
        assert NOTICE_LEVEL_NAME == "NOTICE"

    def test_icon_is_bell(self) -> None:
        assert NOTICE_ICON == "🔔"

    def test_color_contains_bold_and_cyan(self) -> None:
        assert "<bold>" in NOTICE_COLOR
        assert "<cyan>" in NOTICE_COLOR


class TestSetupLogging:
    def test_returns_logger(self) -> None:
        result = setup_logging()
        assert result is logger

    def test_notice_level_usable_after_setup(self) -> None:
        setup_logging()
        try:
            logger.log("NOTICE", "test message")
        except ValueError as exc:
            pytest.fail(f"NOTICE level not registered: {exc}")

    def test_notice_severity_is_22(self) -> None:
        setup_logging()
        assert logger.level("NOTICE").no == LOG_LEVEL_NOTICE

    def test_notice_between_info_and_warning(self) -> None:
        setup_logging()
        assert logger.level("INFO").no < logger.level("NOTICE").no < logger.level("WARNING").no

    def test_idempotent_second_call_does_not_raise(self) -> None:
        setup_logging()
        setup_logging()  # must not raise ValueError for already-registered level

    def test_with_log_file_does_not_raise(self, tmp_path: pathlib.Path) -> None:
        log_file = str(tmp_path / "test.log")
        result = setup_logging(log_file=log_file)
        assert result is logger
