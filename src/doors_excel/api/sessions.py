"""Session lifecycle management for the import/export pipeline.

A *session* represents one import or export run tied to a specific Excel file
and DOORS module.  It persists as a row in the ``sessions`` SQLite table and
as a ``SESSION_FILE_NAME`` sidecar JSON file next to the Excel workbook so
interrupted operations can be resumed (REQ-SAF-406).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from doors_excel.common.constants import SESSION_FILE_NAME
from doors_excel.common.exceptions import SessionError
from doors_excel.infrastructure.database.connection import init_database
from doors_excel.infrastructure.database.repositories import SessionRepository


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass
class SessionInfo:
    session_id: str
    excel_path: Path
    doors_module: str
    excel_sha256: str
    module_version: str
    db_path: Path

    def to_dict(self) -> dict:
        d = asdict(self)
        d["excel_path"] = str(self.excel_path)
        d["db_path"] = str(self.db_path)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SessionInfo":
        return cls(
            session_id=data["session_id"],
            excel_path=Path(data["excel_path"]),
            doors_module=data["doors_module"],
            excel_sha256=data["excel_sha256"],
            module_version=data.get("module_version", "current"),
            db_path=Path(data["db_path"]),
        )


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def compute_file_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of the raw bytes of *path*."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def session_file_path(excel_path: Path) -> Path:
    """Return the ``SESSION_FILE_NAME`` sidecar path next to *excel_path*."""
    return excel_path.parent / SESSION_FILE_NAME


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------

class SessionManager:
    """Manages session creation, resumption, and closure.

    Opens a single SQLite connection on first use and keeps it open until
    :meth:`close` is called (or the context manager exits).

    Usage::

        with SessionManager(db_path) as mgr:
            info = mgr.create(excel_path, doors_module="/proj/mod")
            ...
            mgr.finish(info.session_id)
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._last_session_id: str | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = init_database(self.db_path)
        return self._conn

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    def create(
        self,
        excel_path: Path | str,
        doors_module: str,
        *,
        module_version: str = "current",
    ) -> SessionInfo:
        """Create a new session, persist it to DB and sidecar JSON.

        Raises :class:`~doors_excel.common.exceptions.SessionError` if
        *excel_path* does not exist.
        """
        p = Path(excel_path)
        if not p.exists():
            raise SessionError(f"Excel file not found: {p}")

        sha256 = compute_file_sha256(p)
        session_id = str(uuid.uuid4())

        SessionRepository(self.conn).create(
            session_id=session_id,
            excel_path=str(p),
            doors_module=doors_module,
            excel_sha256=sha256,
            module_version=module_version,
        )

        info = SessionInfo(
            session_id=session_id,
            excel_path=p,
            doors_module=doors_module,
            excel_sha256=sha256,
            module_version=module_version,
            db_path=self.db_path,
        )
        self._last_session_id = session_id
        _write_session_file(info)
        return info

    @property
    def last_session_id(self) -> str | None:
        """Session ID of the most recently created session, or None."""
        return self._last_session_id

    def resume(self, session_file: Path | str) -> SessionInfo:
        """Load a previous session from *session_file* (the sidecar JSON).

        Verifies that:
        - The session record still exists in the DB.
        - The Excel file's current SHA-256 matches the stored hash.

        Raises :class:`~doors_excel.common.exceptions.SessionError` on any
        integrity failure.
        """
        sf = Path(session_file)
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SessionError(f"Cannot read session file {sf}: {exc}") from exc

        try:
            info = SessionInfo.from_dict(data)
        except KeyError as exc:
            raise SessionError(f"Session file {sf} is malformed: missing key {exc}") from exc

        row = SessionRepository(self.conn).get(info.session_id)
        if row is None:
            raise SessionError(
                f"Session {info.session_id!r} not found in database {self.db_path}"
            )

        if not info.excel_path.exists():
            raise SessionError(f"Excel file no longer exists: {info.excel_path}")

        current_sha = compute_file_sha256(info.excel_path)
        if current_sha != info.excel_sha256:
            raise SessionError(
                f"Excel file has been modified since session was created "
                f"(stored={info.excel_sha256[:12]}…, current={current_sha[:12]}…)"
            )

        return info

    def finish(self, session_id: str, *, status: str = "completed") -> None:
        """Mark the session as *status* in the DB (default ``'completed'``)."""
        SessionRepository(self.conn).update_status(session_id, status)

    def fail(self, session_id: str) -> None:
        """Mark the session as ``'failed'`` in the DB."""
        self.finish(session_id, status="failed")

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "SessionManager":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _write_session_file(info: SessionInfo) -> None:
    sf = session_file_path(info.excel_path)
    sf.write_text(
        json.dumps(info.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
