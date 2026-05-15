"""DoorsConnection — thin wrapper around the pywin32 COM bridge."""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

# Lazy import so non-Windows test environments can import this module.
# On Windows, pywin32 is installed; tests patch win32com_gencache at module level.
if sys.platform == "win32":  # pragma: no cover
    from win32com.client import gencache as win32com_gencache
else:
    win32com_gencache = None  # type: ignore[assignment]


@dataclass
class DoorsConnection:
    """Manages a single pywin32 COM session with IBM DOORS."""

    _app: object = field(default=None, repr=False)

    @classmethod
    def open(cls) -> "DoorsConnection":
        """Open a COM connection to a running DOORS instance."""
        app = win32com_gencache.EnsureDispatch("DOORS.Application")
        return cls(_app=app)

    def run_dxl(self, script: str) -> str | None:
        """Execute *script* via the DOORS COM interface; retries up to 3 times on COM errors.

        Exponential backoff: 2 s, 4 s, 8 s between attempts.
        RuntimeError (connection not open) propagates immediately without retry.
        """
        from loguru import logger

        if self._app is None:
            raise RuntimeError("DoorsConnection is not open")

        delay = 2.0
        for attempt in range(4):  # 1 initial + 3 retries
            try:
                return self._app.runScript(script)  # type: ignore[union-attr]
            except RuntimeError:
                raise
            except Exception as exc:
                if attempt == 3:
                    raise
                logger.warning(
                    "DOORS COM error (attempt {}/3): {}. Retrying in {}s...",
                    attempt + 1,
                    exc,
                    delay,
                )
                time.sleep(delay)
                delay *= 2
        return None  # unreachable, satisfies type checker

    def close(self) -> None:
        """Release the COM reference."""
        self._app = None

    def __enter__(self) -> "DoorsConnection":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
