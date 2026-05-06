"""SQLite connection management for doors-excel-tool."""
from __future__ import annotations

import contextlib
import sqlite3
from pathlib import Path
from typing import Generator

from doors_excel.infrastructure.database.schema import apply_schema


@contextlib.contextmanager
def open_database(path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    """Yield a WAL-mode SQLite connection; close it on exit.

    Creates parent directories and the database file if they do not exist.
    Does NOT apply the schema — use ``init_database`` for a fully initialised DB.
    """
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        yield conn
    finally:
        conn.close()


def init_database(path: str | Path) -> sqlite3.Connection:
    """Open the database, apply the schema, and return the open connection.

    The caller is responsible for calling ``conn.close()``.
    Use ``open_database`` if you want automatic cleanup via a context manager.
    """
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    apply_schema(conn)
    return conn
