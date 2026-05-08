"""Diff API — compute a 3-way merge and return a human-readable summary."""
from __future__ import annotations

import sqlite3

from doors_excel.core.diff.engine import baseline_mismatch_check, compute_diff
from doors_excel.core.diff.summary import DiffSummary, get_diff_summary


def run_diff(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    parent_id_attr: str = "_Parent_ID",
) -> DiffSummary:
    """Run the full 3-way merge for *session_id* and return a :class:`DiffSummary`.

    Combines :func:`~doors_excel.core.diff.engine.compute_diff`,
    :func:`~doors_excel.core.diff.engine.baseline_mismatch_check`, and
    :func:`~doors_excel.core.diff.summary.get_diff_summary` into a single
    call that the CLI and GUI can use directly.

    The staging tables (``staging_baseline``, ``staging_doors``,
    ``staging_excel``) must be populated before calling this function.
    """
    compute_diff(conn, session_id, parent_id_attr=parent_id_attr)
    mismatch = baseline_mismatch_check(conn, session_id)
    return get_diff_summary(conn, session_id, baseline_mismatch_count=mismatch)
