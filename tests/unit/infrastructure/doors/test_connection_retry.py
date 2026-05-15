"""Tests for COM reconnect retry logic (REQ-REL-602)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestRunDxlRetry:
    def test_success_on_first_attempt_returns_result(self) -> None:
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        conn = DoorsConnection.__new__(DoorsConnection)
        mock_app = MagicMock()
        mock_app.runScript.return_value = "ok"
        conn._app = mock_app

        result = conn.run_dxl("some script")

        assert result == "ok"
        mock_app.runScript.assert_called_once_with("some script")

    def test_transient_com_error_retried(self) -> None:
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        conn = DoorsConnection.__new__(DoorsConnection)
        mock_app = MagicMock()
        # Fail twice, succeed on third call
        mock_app.runScript.side_effect = [Exception("COM error"), Exception("COM error"), "ok"]
        conn._app = mock_app

        with patch("time.sleep"):
            result = conn.run_dxl("script")

        assert result == "ok"
        assert mock_app.runScript.call_count == 3

    def test_permanent_com_error_raises_after_max_retries(self) -> None:
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        conn = DoorsConnection.__new__(DoorsConnection)
        mock_app = MagicMock()
        mock_app.runScript.side_effect = Exception("persistent COM error")
        conn._app = mock_app

        with patch("time.sleep"), pytest.raises(Exception, match="persistent COM error"):
            conn.run_dxl("script")

        # 1 initial + 3 retries = 4 total attempts
        assert mock_app.runScript.call_count == 4

    def test_runtime_error_not_retried(self) -> None:
        """RuntimeError (app is None) propagates immediately without retry."""
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        conn = DoorsConnection.__new__(DoorsConnection)
        conn._app = None

        with pytest.raises(RuntimeError, match="not open"):
            conn.run_dxl("script")

    def test_sleep_uses_exponential_backoff(self) -> None:
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        conn = DoorsConnection.__new__(DoorsConnection)
        mock_app = MagicMock()
        mock_app.runScript.side_effect = [
            Exception("err"), Exception("err"), Exception("err"), Exception("err"),
        ]
        conn._app = mock_app

        sleep_calls = []
        with patch("time.sleep", side_effect=lambda d: sleep_calls.append(d)):
            with pytest.raises(Exception):
                conn.run_dxl("script")

        # 3 retries → 3 sleeps: 2, 4, 8
        assert sleep_calls == [2.0, 4.0, 8.0]
