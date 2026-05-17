"""Static pre-import validation against staging_excel (REQ-FUN-217).

Reads from ``staging_excel``, writes errors to ``validation_errors``, and
returns aggregate counts as :class:`ValidationResult`.

Error codes
-----------
MISSING_COLUMN         — a mapped column is absent from the Excel sheet
STR_LEN_EXCEEDED       — String attribute exceeds 1024 chars (REQ-FUN-206.1)
ENUM_MISMATCH          — value not in the declared allowed set (REQ-FUN-206)
ORPHAN_PLACEHOLDER     — [IMAGE: N] in a new row (REQ-FUN-217.3)
STRUCT_MARKER_OUT_OF_ORDER — TABLE_ROW/CELL outside TABLE_START/END (REQ-FUN-108.2)
STRUCT_HIERARCHY_MISMATCH  — TABLE_CELL before any TABLE_ROW in its table (REQ-FUN-108.5)
"""
from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass

from doors_excel.core.transformation.image_placeholders import PLACEHOLDER_RE
from doors_excel.core.validation.models import ModuleConfig

_STRING_MAX_LEN = 1024

ErrorCode = str  # one of the constants above


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    blocking_count: int = 0
    warning_count: int = 0

    @property
    def has_errors(self) -> bool:
        return self.blocking_count > 0

    @property
    def total(self) -> int:
        return self.blocking_count + self.warning_count


def validate_session(
    conn: sqlite3.Connection,
    session_id: str,
    module_config: ModuleConfig,
) -> ValidationResult:
    """Validate all ``staging_excel`` rows for *session_id*.

    Clears previous errors for the session, runs all checks, and returns
    aggregate counts.  Idempotent.
    """
    _clear_validation_errors(conn, session_id)

    _check_required_columns(conn, session_id, module_config)
    _check_string_lengths(conn, session_id, module_config)
    _check_enum_values(conn, session_id, module_config)
    _check_orphan_placeholders(conn, session_id, module_config)
    _check_structural_markers(conn, session_id, module_config)

    return _read_result(conn, session_id)


# ---------------------------------------------------------------------------
# Internal check functions
# ---------------------------------------------------------------------------

def _check_required_columns(
    conn: sqlite3.Connection,
    session_id: str,
    module_config: ModuleConfig,
) -> None:
    """MISSING_COLUMN: any mapped column absent from staging_excel."""
    if not conn.execute(
        "SELECT 1 FROM staging_excel WHERE session_id = ? LIMIT 1", (session_id,)
    ).fetchone():
        return  # nothing staged — nothing to check

    present = {
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT attribute FROM staging_excel WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    }

    for mapping in module_config.column_mappings:
        if mapping.column not in present:
            _insert_error(
                conn,
                session_id,
                row_number=0,
                object_id=None,
                attribute=mapping.column,
                error_code="MISSING_COLUMN",
                message=f"Required column '{mapping.column}' is absent from the Excel sheet.",
            )
    conn.commit()


def _check_string_lengths(
    conn: sqlite3.Connection,
    session_id: str,
    module_config: ModuleConfig,
) -> None:
    """STR_LEN_EXCEEDED: String attribute value longer than 1024 chars."""
    for mapping in module_config.column_mappings:
        if mapping.attribute_type != "String":
            continue
        rows = conn.execute(
            """
            SELECT row_number, object_id, value
              FROM staging_excel
             WHERE session_id = ?
               AND attribute  = ?
               AND value IS NOT NULL
               AND length(value) > ?
            """,
            (session_id, mapping.column, _STRING_MAX_LEN),
        ).fetchall()
        for row_number, object_id, value in rows:
            _insert_error(
                conn,
                session_id,
                row_number=row_number,
                object_id=object_id,
                attribute=mapping.column,
                error_code="STR_LEN_EXCEEDED",
                message=(
                    f"Column '{mapping.column}' exceeds the 1024-character limit"
                    f" for String attributes (got {len(value)})."
                ),
            )
    conn.commit()


def _check_enum_values(
    conn: sqlite3.Connection,
    session_id: str,
    module_config: ModuleConfig,
) -> None:
    """ENUM_MISMATCH: value not in the declared enum_values list."""
    for mapping in module_config.column_mappings:
        if mapping.attribute_type not in ("Enum", "MultiEnum"):
            continue
        if not mapping.enum_values:
            continue  # no declared set → cannot validate membership

        allowed = set(mapping.enum_values)
        rows = conn.execute(
            """
            SELECT row_number, object_id, value
              FROM staging_excel
             WHERE session_id = ?
               AND attribute  = ?
               AND value IS NOT NULL
               AND value != ''
            """,
            (session_id, mapping.column),
        ).fetchall()

        for row_number, object_id, value in rows:
            if mapping.attribute_type == "Enum":
                candidates = [value.strip()]
            else:
                candidates = _split_multienum(value)

            for candidate in candidates:
                if candidate and candidate not in allowed:
                    _insert_error(
                        conn,
                        session_id,
                        row_number=row_number,
                        object_id=object_id,
                        attribute=mapping.column,
                        error_code="ENUM_MISMATCH",
                        message=(
                            f"Value {candidate!r} is not an allowed value"
                            f" for column '{mapping.column}'."
                        ),
                    )
    conn.commit()


def _check_orphan_placeholders(
    conn: sqlite3.Connection,
    session_id: str,
    module_config: ModuleConfig,  # noqa: ARG001
) -> None:
    """ORPHAN_PLACEHOLDER: [IMAGE: N] in a new (object_id IS NULL) row."""
    rows = conn.execute(
        """
        SELECT row_number, attribute, value
          FROM staging_excel
         WHERE session_id  = ?
           AND object_id IS NULL
           AND value IS NOT NULL
        """,
        (session_id,),
    ).fetchall()
    for row_number, attribute, value in rows:
        if PLACEHOLDER_RE.search(value):
            _insert_error(
                conn,
                session_id,
                row_number=row_number,
                object_id=None,
                attribute=attribute,
                error_code="ORPHAN_PLACEHOLDER",
                message=(
                    f"Column '{attribute}' in a new row contains an OLE image"
                    " placeholder that cannot be imported (REQ-FUN-217.3)."
                ),
            )
    conn.commit()


def _check_structural_markers(
    conn: sqlite3.Connection,
    session_id: str,
    module_config: ModuleConfig,
) -> None:
    """STRUCT_MARKER_OUT_OF_ORDER / STRUCT_HIERARCHY_MISMATCH: table structure checks."""
    rows = conn.execute(
        """
        SELECT row_number, object_id, value
          FROM staging_excel
         WHERE session_id = ?
           AND attribute  = ?
         ORDER BY row_number
        """,
        (session_id, module_config.object_type_column),
    ).fetchall()

    in_table = False
    in_table_with_row = False
    for row_number, object_id, value in rows:
        if value is None:
            continue
        marker = value.strip()
        if marker == "TABLE_START":
            in_table = True
            in_table_with_row = False
        elif marker == "TABLE_END":
            if not in_table:
                _insert_error(
                    conn,
                    session_id,
                    row_number=row_number,
                    object_id=object_id,
                    attribute=module_config.object_type_column,
                    error_code="STRUCT_MARKER_OUT_OF_ORDER",
                    message="TABLE_END found without a preceding TABLE_START.",
                )
            in_table = False
            in_table_with_row = False
        elif marker == "TABLE_ROW":
            if not in_table:
                _insert_error(
                    conn,
                    session_id,
                    row_number=row_number,
                    object_id=object_id,
                    attribute=module_config.object_type_column,
                    error_code="STRUCT_MARKER_OUT_OF_ORDER",
                    message="TABLE_ROW found outside TABLE_START/TABLE_END.",
                )
            else:
                in_table_with_row = True
        elif marker == "TABLE_CELL":
            if not in_table:
                _insert_error(
                    conn,
                    session_id,
                    row_number=row_number,
                    object_id=object_id,
                    attribute=module_config.object_type_column,
                    error_code="STRUCT_MARKER_OUT_OF_ORDER",
                    message="TABLE_CELL found outside TABLE_START/TABLE_END.",
                )
            elif not in_table_with_row:
                _insert_error(
                    conn,
                    session_id,
                    row_number=row_number,
                    object_id=object_id,
                    attribute=module_config.object_type_column,
                    error_code="STRUCT_HIERARCHY_MISMATCH",
                    message="TABLE_CELL found before any TABLE_ROW in this table.",
                )
    conn.commit()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _clear_validation_errors(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute("DELETE FROM validation_errors WHERE session_id = ?", (session_id,))
    conn.commit()


def _insert_error(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    row_number: int,
    object_id: int | None,
    attribute: str | None,
    error_code: str,
    message: str,
    severity: str = "BLOCKING",
) -> None:
    conn.execute(
        """
        INSERT INTO validation_errors
               (session_id, row_number, object_id, attribute, error_code, message, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, row_number, object_id, attribute, error_code, message, severity),
    )


def _split_multienum(value: str) -> list[str]:
    """Quote-aware semicolon split per REQ-FUN-115 (RFC 4180 style)."""
    reader = csv.reader(io.StringIO(value), delimiter=";", quotechar='"', doublequote=True)
    try:
        return [v.strip() for v in next(reader)]
    except StopIteration:
        return []


def _read_result(conn: sqlite3.Connection, session_id: str) -> ValidationResult:
    rows = conn.execute(
        """
        SELECT severity, COUNT(*) AS cnt
          FROM validation_errors
         WHERE session_id = ?
         GROUP BY severity
        """,
        (session_id,),
    ).fetchall()
    counts = {r[0]: r[1] for r in rows}
    return ValidationResult(
        blocking_count=counts.get("BLOCKING", 0),
        warning_count=counts.get("WARNING", 0),
    )
