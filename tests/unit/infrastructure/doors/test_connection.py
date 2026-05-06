"""Unit tests for DoorsConnection — COM interactions are fully mocked."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _make_connection(mock_app: MagicMock) -> "DoorsConnection":  # type: ignore[name-defined]
    from doors_excel.infrastructure.doors.connection import DoorsConnection
    conn = DoorsConnection.__new__(DoorsConnection)
    conn._app = mock_app
    return conn


class TestDoorsConnectionOpen:
    def test_open_calls_ensure_dispatch(self, mocker: "pytest_mock.MockerFixture") -> None:  # type: ignore[name-defined]
        mock_gencache = mocker.patch(
            "doors_excel.infrastructure.doors.connection.win32com_gencache",
            create=True,
        )
        mock_gencache.EnsureDispatch.return_value = MagicMock()
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        conn = DoorsConnection.open()
        mock_gencache.EnsureDispatch.assert_called_once_with("DOORS.Application")
        assert conn._app is mock_gencache.EnsureDispatch.return_value

    def test_open_raises_on_com_error(self, mocker: "pytest_mock.MockerFixture") -> None:  # type: ignore[name-defined]
        mock_gencache = mocker.patch(
            "doors_excel.infrastructure.doors.connection.win32com_gencache",
            create=True,
        )
        mock_gencache.EnsureDispatch.side_effect = Exception("COM error")
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        with pytest.raises(Exception, match="COM error"):
            DoorsConnection.open()


class TestDoorsConnectionRunDxl:
    def test_run_dxl_calls_runscript(self, mocker: "pytest_mock.MockerFixture") -> None:  # type: ignore[name-defined]
        mock_app = MagicMock()
        mock_app.runScript.return_value = None
        conn = _make_connection(mock_app)
        conn.run_dxl("print 1\n")
        mock_app.runScript.assert_called_once_with("print 1\n")

    def test_run_dxl_returns_output(self, mocker: "pytest_mock.MockerFixture") -> None:  # type: ignore[name-defined]
        mock_app = MagicMock()
        mock_app.runScript.return_value = "result_string"
        conn = _make_connection(mock_app)
        result = conn.run_dxl("print foo\n")
        assert result == "result_string"

    def test_run_dxl_on_closed_conn_raises(self) -> None:
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        conn = DoorsConnection.__new__(DoorsConnection)
        conn._app = None  # type: ignore[assignment]
        with pytest.raises(RuntimeError, match="not open"):
            conn.run_dxl("print 1\n")


class TestDoorsConnectionClose:
    def test_close_nulls_app(self, mocker: "pytest_mock.MockerFixture") -> None:  # type: ignore[name-defined]
        mock_app = MagicMock()
        conn = _make_connection(mock_app)
        conn.close()
        assert conn._app is None

    def test_close_idempotent(self) -> None:
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        conn = DoorsConnection.__new__(DoorsConnection)
        conn._app = None  # type: ignore[assignment]
        conn.close()  # must not raise


class TestDoorsConnectionContextManager:
    def test_context_manager_opens_and_closes(self, mocker: "pytest_mock.MockerFixture") -> None:  # type: ignore[name-defined]
        mock_gencache = mocker.patch(
            "doors_excel.infrastructure.doors.connection.win32com_gencache",
            create=True,
        )
        mock_app = MagicMock()
        mock_gencache.EnsureDispatch.return_value = mock_app
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        with DoorsConnection.open() as conn:
            assert conn._app is mock_app
        assert conn._app is None

    def test_context_manager_closes_on_exception(self, mocker: "pytest_mock.MockerFixture") -> None:  # type: ignore[name-defined]
        mock_gencache = mocker.patch(
            "doors_excel.infrastructure.doors.connection.win32com_gencache",
            create=True,
        )
        mock_app = MagicMock()
        mock_gencache.EnsureDispatch.return_value = mock_app
        from doors_excel.infrastructure.doors.connection import DoorsConnection
        with pytest.raises(ValueError):
            with DoorsConnection.open() as conn:
                raise ValueError("oops")
        assert conn._app is None
