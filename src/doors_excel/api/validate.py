"""Excel and config file validation API (REQ-FUN-217, REQ-INF-004).

Two entry points:

``validate_config``
    Loads and validates a JSON config file via Pydantic.  Raises
    :class:`~doors_excel.common.exceptions.ConfigurationError` on failure.

``validate_excel``
    Opens an Excel workbook, reads all rows of the target worksheet into
    ``staging_excel``, and runs the full static validation suite.  Returns a
    :class:`~doors_excel.core.validation.validator.ValidationResult`.
"""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from doors_excel.common.exceptions import ConfigurationError
from doors_excel.core.validation.models import ModuleConfig, ProjectConfig, load_config
from doors_excel.core.validation.validator import ValidationResult, validate_session
from doors_excel.infrastructure.database.connection import init_database
from doors_excel.infrastructure.database.repositories import StagingExcelRepository
from doors_excel.infrastructure.excel.reader import FormulaPolicy, open_workbook

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet


def validate_config(config_path: Path | str) -> ProjectConfig:
    """Load and validate a JSON config file.

    Thin wrapper around :func:`~doors_excel.core.validation.models.load_config`
    that is importable from the API surface.

    Raises :class:`~doors_excel.common.exceptions.ConfigurationError` on any
    read, parse, or schema failure.
    """
    return load_config(config_path)


def validate_excel(
    excel_path: Path | str,
    module_config: ModuleConfig,
    *,
    db_path: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
    session_id: str | None = None,
) -> ValidationResult:
    """Validate *excel_path* against *module_config* and return error counts.

    Workflow
    --------
    1. Open the workbook (data_only mode).
    2. Find the first worksheet whose title matches *module_config.module_path*,
       or fall back to the active sheet.
    3. Read all rows into a temporary ``staging_excel`` DB session.
    4. Run :func:`~doors_excel.core.validation.validator.validate_session`.
    5. Return the :class:`~doors_excel.core.validation.validator.ValidationResult`.

    Parameters
    ----------
    excel_path:
        Path to the ``.xlsx`` / ``.xlsm`` file to validate.
    module_config:
        Column mapping and metadata for the target module.
    db_path:
        SQLite DB path.  If *conn* is provided this is ignored.
        Defaults to an in-memory database when both are ``None``.
    conn:
        An already-open connection.  Caller owns the lifecycle.
    session_id:
        Explicit session ID.  Generated automatically when ``None``.
    """
    p = Path(excel_path)

    # validate_excel is a stateless operation — FK enforcement is unnecessary
    # for its temporary staging session, so we always use apply_schema only
    # (not init_database, which enables PRAGMA foreign_keys = ON).
    _owns_conn = conn is None
    if conn is None:
        import sqlite3 as _sqlite3
        from doors_excel.infrastructure.database.schema import apply_schema as _apply

        target = str(db_path) if db_path is not None else ":memory:"
        conn = _sqlite3.connect(target)
        _apply(conn)

    sid = session_id or str(uuid.uuid4())

    try:
        wb = open_workbook(p, formula_policy=FormulaPolicy.DATA_ONLY)
        ws = _pick_worksheet(wb, module_config)
        _load_worksheet_to_staging(ws, conn, sid, module_config)
        return validate_session(conn, sid, module_config)
    finally:
        if _owns_conn:
            conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pick_worksheet(wb, module_config: ModuleConfig):
    """Return the best-matching worksheet, falling back to the active sheet."""
    # Try exact title match on last segment of module_path
    module_name = module_config.module_path.rstrip("/").rsplit("/", 1)[-1]
    for ws in wb.worksheets:
        if ws.title == module_name or module_name in ws.title:
            return ws
    return wb.active


def _load_worksheet_to_staging(
    ws: "Worksheet",
    conn: sqlite3.Connection,
    session_id: str,
    module_config: ModuleConfig,
) -> None:
    """Read all rows from *ws* and insert into ``staging_excel``."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return

    headers = [str(cell) if cell is not None else "" for cell in rows[0]]
    oid_col = module_config.object_id_column

    staging: list[dict] = []
    for row_idx, row in enumerate(rows[1:], start=2):
        # Resolve object_id from the "Absolute Number" column
        object_id: int | None = None
        if oid_col in headers:
            raw_oid = row[headers.index(oid_col)] if headers.index(oid_col) < len(row) else None
            try:
                object_id = int(raw_oid) if raw_oid is not None and str(raw_oid).strip() else None
            except (ValueError, TypeError):
                object_id = None

        for col_idx, header in enumerate(headers):
            if not header:
                continue
            value = row[col_idx] if col_idx < len(row) else None
            staging.append({
                "session_id": session_id,
                "row_number": row_idx,
                "object_id": object_id,
                "attribute": header,
                "value": str(value) if value is not None else None,
            })

    StagingExcelRepository(conn).insert_many(staging)
