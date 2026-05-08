"""SQL-based 3-way merge engine (REQ-FUN-207, REQ-FUN-116).

Algorithm
---------
Three staging tables feed the diff:

    staging_baseline  — snapshot from the last export (common ancestor)
    staging_doors     — current live DOORS state
    staging_excel     — current Excel state (post-export edits)

Change classification (attribute-level for existing objects):

    UNCHANGED  : excel IS baseline  (no edit, even if DOORS drifted)
    UPDATED    : excel IS NOT baseline  AND  doors IS baseline
                 → Excel changed, DOORS did not → safe to apply
    CONFLICT   : excel IS NOT baseline  AND  doors IS NOT baseline
                 → both sides changed → needs resolution (REQ-FUN-207)
    NEW        : object-level — object_id IS NULL or not in baseline
    DELETED    : object-level — baseline object absent from Excel
    MOVED      : existing object whose parent changed vs baseline

NOTE — REQ-FUN-105.4 (md_hash bypass): staging_excel has no md_hash column.
A cell whose Markdown hashes to staging_doors.md_hash was not edited since
export and MUST be UNCHANGED even if the string representation drifted during
RTF↔MD round-trip.  This bypass requires staging_excel to carry md_hash or
the engine to accept pre-computed hash pairs.  Currently NOT implemented.
# TODO REQ-FUN-105.4: add md_hash to staging_excel and wire hash comparison.

NOTE — DOORS-only additions: objects added to DOORS by another user since
export are detected separately via baseline_mismatch_check() below; they do
not appear in diff_results change types because the schema does not permit an
additional type and they are reported as a module-level warning (REQ-FUN-208).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DiffStats:
    new_count: int
    deleted_count: int
    updated_count: int
    conflict_count: int
    moved_count: int

    @property
    def total(self) -> int:
        return self.new_count + self.deleted_count + self.updated_count + self.conflict_count + self.moved_count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_diff(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    parent_id_attr: str = "_Parent_ID",
) -> DiffStats:
    """Populate diff_results for *session_id* and return change counts.

    Idempotent: existing diff_results for the session are cleared first.
    *parent_id_attr* names the Excel attribute that holds the parent object ID.
    """
    _clear_diff(conn, session_id)

    _insert_new_objects(conn, session_id)
    _insert_deleted_objects(conn, session_id)
    _insert_attribute_changes(conn, session_id)
    _insert_moved_objects(conn, session_id, parent_id_attr=parent_id_attr)

    return _read_stats(conn, session_id)


def baseline_mismatch_check(conn: sqlite3.Connection, session_id: str) -> int:
    """Return count of DOORS objects added after export (not in baseline or Excel).

    These are not written to diff_results; they surface as a module-level
    warning (REQ-FUN-208) to alert the user that DOORS has diverged.
    """
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT d.object_id)
        FROM staging_doors d
        WHERE d.session_id = ?
          AND d.object_id NOT IN (
              SELECT DISTINCT object_id FROM staging_baseline WHERE session_id = ?
          )
          AND d.object_id NOT IN (
              SELECT DISTINCT object_id FROM staging_excel WHERE session_id = ? AND object_id IS NOT NULL
          )
        """,
        (session_id, session_id, session_id),
    ).fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clear_diff(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute("DELETE FROM diff_results WHERE session_id = ?", (session_id,))
    conn.commit()


def _insert_new_objects(conn: sqlite3.Connection, session_id: str) -> None:
    """NEW: rows in staging_excel with no object_id (brand-new objects)."""
    conn.execute(
        """
        INSERT INTO diff_results
               (session_id, object_id, attribute, change_type, row_number)
        SELECT DISTINCT :sid, NULL, NULL, 'NEW', row_number
        FROM staging_excel
        WHERE session_id = :sid
          AND object_id IS NULL
        """,
        {"sid": session_id},
    )
    conn.commit()


def _insert_deleted_objects(conn: sqlite3.Connection, session_id: str) -> None:
    """DELETED: object_ids in baseline but absent from staging_excel."""
    conn.execute(
        """
        INSERT INTO diff_results
               (session_id, object_id, attribute, change_type)
        SELECT DISTINCT :sid, b.object_id, NULL, 'DELETED'
        FROM staging_baseline b
        WHERE b.session_id = :sid
          AND b.object_id NOT IN (
              SELECT object_id FROM staging_excel
              WHERE session_id = :sid AND object_id IS NOT NULL
          )
        """,
        {"sid": session_id},
    )
    conn.commit()


def _insert_attribute_changes(conn: sqlite3.Connection, session_id: str) -> None:
    """UPDATED and CONFLICT: per-attribute diffs for existing objects.

    'Existing' means the object_id appears in staging_baseline (not NEW).
    """
    conn.execute(
        """
        WITH three_way AS (
            SELECT
                e.object_id,
                e.attribute,
                e.value            AS excel_value,
                b.value            AS baseline_value,
                d.value            AS doors_value,
                e.row_number
            FROM staging_excel e
            LEFT JOIN staging_baseline b
                ON  b.session_id = :sid
                AND b.object_id  = e.object_id
                AND b.attribute  = e.attribute
            LEFT JOIN staging_doors d
                ON  d.session_id = :sid
                AND d.object_id  = e.object_id
                AND d.attribute  = e.attribute
            WHERE e.session_id  = :sid
              AND e.object_id IS NOT NULL
              AND e.object_id IN (
                  SELECT DISTINCT object_id
                  FROM staging_baseline WHERE session_id = :sid
              )
        ),
        classified AS (
            SELECT
                object_id,
                attribute,
                excel_value,
                baseline_value,
                doors_value,
                row_number,
                CASE
                    -- Excel unchanged from baseline → UNCHANGED regardless of DOORS
                    WHEN excel_value IS baseline_value                           THEN 'UNCHANGED'
                    -- Excel changed, DOORS did not → safe UPDATE
                    WHEN (excel_value IS NOT baseline_value)
                     AND (doors_value IS     baseline_value)                    THEN 'UPDATED'
                    -- Both sides changed → CONFLICT
                    WHEN (excel_value IS NOT baseline_value)
                     AND (doors_value IS NOT baseline_value)                    THEN 'CONFLICT'
                    ELSE 'UNCHANGED'
                END AS change_type
            FROM three_way
        )
        INSERT INTO diff_results
               (session_id, object_id, attribute, change_type,
                excel_value, doors_value, baseline_value, row_number)
        SELECT :sid, object_id, attribute, change_type,
               excel_value, doors_value, baseline_value, row_number
        FROM classified
        WHERE change_type != 'UNCHANGED'
        """,
        {"sid": session_id},
    )
    conn.commit()


def _insert_moved_objects(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    parent_id_attr: str,
) -> None:
    """MOVED: existing objects whose parent changed in Excel vs baseline.

    Hierarchy is stored in staging_baseline.parent_id (a column).
    In staging_excel it appears as an attribute row named *parent_id_attr*.
    """
    conn.execute(
        """
        INSERT INTO diff_results
               (session_id, object_id, attribute, change_type,
                excel_value, baseline_value, row_number)
        SELECT :sid, e.object_id, :attr, 'MOVED',
               e.value, CAST(b_struct.parent_id AS TEXT), e.row_number
        FROM staging_excel e
        JOIN staging_baseline b_struct
            ON  b_struct.session_id = :sid
            AND b_struct.object_id  = e.object_id
        WHERE e.session_id = :sid
          AND e.attribute  = :attr
          AND e.object_id IS NOT NULL
          AND e.value IS NOT CAST(b_struct.parent_id AS TEXT)
          AND e.object_id NOT IN (
              SELECT object_id FROM diff_results
              WHERE session_id = :sid AND change_type = 'DELETED'
          )
        GROUP BY e.object_id
        """,
        {"sid": session_id, "attr": parent_id_attr},
    )
    conn.commit()


def _read_stats(conn: sqlite3.Connection, session_id: str) -> DiffStats:
    rows = conn.execute(
        """
        SELECT change_type, COUNT(*) AS cnt
        FROM diff_results
        WHERE session_id = ?
        GROUP BY change_type
        """,
        (session_id,),
    ).fetchall()
    counts = {r[0]: r[1] for r in rows}
    return DiffStats(
        new_count=counts.get("NEW", 0),
        deleted_count=counts.get("DELETED", 0),
        updated_count=counts.get("UPDATED", 0),
        conflict_count=counts.get("CONFLICT", 0),
        moved_count=counts.get("MOVED", 0),
    )
