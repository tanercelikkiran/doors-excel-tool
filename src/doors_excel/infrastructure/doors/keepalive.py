"""Background watchdog thread that pings DOORS to prevent session timeout."""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

DEFAULT_INTERVAL_SECONDS: int = 60

_log = logging.getLogger(__name__)


class KeepAliveWatchdog(threading.Thread):
    """Daemon thread that fires *ping_callback* every *interval* seconds."""

    def __init__(
        self,
        ping_callback: Callable[[], None],
        interval: float = DEFAULT_INTERVAL_SECONDS,
    ) -> None:
        super().__init__(name="doors-keepalive", daemon=True)
        self._callback = ping_callback
        self._interval = interval
        self._stop_event = threading.Event()

    def run(self) -> None:
        while not self._stop_event.wait(timeout=self._interval):
            try:
                self._callback()
            except Exception:
                _log.debug("KeepAlive ping raised an exception", exc_info=True)

    def stop(self) -> None:
        """Signal the watchdog to exit and wait for it to terminate."""
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=self._interval + 1)
