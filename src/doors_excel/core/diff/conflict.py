"""Conflict-policy resolution for diff_results (REQ-FUN-207).

Three policies are supported:

    excel-wins    — Excel value overwrites DOORS for every CONFLICT row
    doors-wins    — DOORS value is preserved; Excel change is discarded
    content-based — No automatic resolution; CONFLICT rows are left with
                    resolved_value=NULL for per-attribute manual review in the UI

Returns the number of rows that were auto-resolved (0 for content-based).
"""
from __future__ import annotations

import sqlite3

from doors_excel.common.types import ConflictPolicy


def apply_conflict_policy(
    conn: sqlite3.Connection,
    session_id: str,
    policy: ConflictPolicy,
) -> int:
    """Set *resolved_value* on all CONFLICT rows for *session_id*.

    Returns the number of rows updated (0 for ``'content-based'``).
    """
    if policy == "excel-wins":
        return _resolve_with_column(conn, session_id, "excel_value")
    if policy == "doors-wins":
        return _resolve_with_column(conn, session_id, "doors_value")
    # content-based: leave resolved_value NULL; manual resolution required
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_with_column(
    conn: sqlite3.Connection,
    session_id: str,
    source_col: str,
) -> int:
    cursor = conn.execute(
        f"""
        UPDATE diff_results
           SET resolved_value = {source_col}
         WHERE session_id  = ?
           AND change_type = 'CONFLICT'
        """,
        (session_id,),
    )
    conn.commit()
    return cursor.rowcount
