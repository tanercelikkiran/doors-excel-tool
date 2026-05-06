"""Unit tests for KeepAliveWatchdog."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from doors_excel.infrastructure.doors.keepalive import DEFAULT_INTERVAL_SECONDS, KeepAliveWatchdog


class TestKeepAliveWatchdog:
    def test_default_interval(self) -> None:
        assert DEFAULT_INTERVAL_SECONDS == 60

    def test_is_daemon_thread(self) -> None:
        cb = MagicMock()
        w = KeepAliveWatchdog(ping_callback=cb)
        assert w.daemon is True

    def test_fires_callback_after_interval(self) -> None:
        fired = threading.Event()
        cb = MagicMock(side_effect=lambda: fired.set())
        w = KeepAliveWatchdog(ping_callback=cb, interval=0.05)
        w.start()
        fired.wait(timeout=1.0)
        w.stop()
        cb.assert_called()

    def test_stop_prevents_further_calls(self) -> None:
        call_count: list[int] = [0]

        def cb() -> None:
            call_count[0] += 1

        w = KeepAliveWatchdog(ping_callback=cb, interval=0.05)
        w.start()
        time.sleep(0.12)  # allow ~2 firings
        w.stop()
        count_after_stop = call_count[0]
        time.sleep(0.12)
        assert call_count[0] == count_after_stop  # no new calls after stop

    def test_stop_before_start_is_safe(self) -> None:
        cb = MagicMock()
        w = KeepAliveWatchdog(ping_callback=cb)
        w.stop()  # must not raise

    def test_stop_idempotent(self) -> None:
        cb = MagicMock()
        w = KeepAliveWatchdog(ping_callback=cb, interval=0.05)
        w.start()
        w.stop()
        w.stop()  # second stop must not raise

    def test_callback_exception_does_not_kill_thread(self) -> None:
        call_count: list[int] = [0]

        def bad_cb() -> None:
            call_count[0] += 1
            raise RuntimeError("ping failed")

        w = KeepAliveWatchdog(ping_callback=bad_cb, interval=0.05)
        w.start()
        time.sleep(0.18)  # allow several firings
        w.stop()
        assert call_count[0] >= 2  # kept firing despite exceptions
