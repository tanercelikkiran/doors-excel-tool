"""Human-readable diff summary for a session (REQ-FUN-207, REQ-FUN-208).

``DiffSummary`` aggregates DiffStats counts plus a flag that indicates
whether DOORS has additions that post-date the export (baseline_mismatch).
``get_diff_summary`` populates it from the live database in one pass.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class DiffSummary:
    new_count: int
    deleted_count: int
    updated_count: int
    conflict_count: int
    moved_count: int
    baseline_mismatch_count: int
    format_loss_risk_count: int = 0

    @property
    def total_changes(self) -> int:
        return (
            self.new_count
            + self.deleted_count
            + self.updated_count
            + self.conflict_count
            + self.moved_count
        )

    @property
    def has_conflicts(self) -> bool:
        return self.conflict_count > 0

    @property
    def has_baseline_mismatch(self) -> bool:
        return self.baseline_mismatch_count > 0

    @property
    def has_format_loss_risk(self) -> bool:
        return self.format_loss_risk_count > 0

    @property
    def is_clean(self) -> bool:
        """True when there are no changes and no baseline divergence."""
        return self.total_changes == 0 and not self.has_baseline_mismatch


def get_diff_summary(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    baseline_mismatch_count: int = 0,
) -> DiffSummary:
    """Build a :class:`DiffSummary` from *diff_results* for *session_id*.

    *baseline_mismatch_count* must be supplied by the caller — it comes from
    :func:`~doors_excel.core.diff.engine.baseline_mismatch_check`, which runs
    a separate query against staging tables not read here.
    """
    rows = conn.execute(
        """
        SELECT change_type, COUNT(*) AS cnt
          FROM diff_results
         WHERE session_id = ?
         GROUP BY change_type
        """,
        (session_id,),
    ).fetchall()
    counts: dict[str, int] = {r[0]: r[1] for r in rows}

    risk_row = conn.execute(
        """
        SELECT COUNT(*) AS cnt
          FROM diff_results dr
          JOIN staging_doors sd
            ON sd.session_id = dr.session_id
           AND sd.object_id  = dr.object_id
           AND sd.attribute  = dr.attribute
          LEFT JOIN staging_excel se
            ON se.session_id = dr.session_id
           AND se.object_id  = dr.object_id
           AND se.attribute  = dr.attribute
         WHERE dr.session_id = ?
           AND dr.change_type IN ('UPDATED', 'CONFLICT')
           AND sd.has_rich_format = 1
           AND (se.md_hash IS NULL OR se.md_hash != sd.md_hash)
        """,
        (session_id,),
    ).fetchone()
    format_loss_risk_count = risk_row[0] if risk_row else 0

    return DiffSummary(
        new_count=counts.get("NEW", 0),
        deleted_count=counts.get("DELETED", 0),
        updated_count=counts.get("UPDATED", 0),
        conflict_count=counts.get("CONFLICT", 0),
        moved_count=counts.get("MOVED", 0),
        baseline_mismatch_count=baseline_mismatch_count,
        format_loss_risk_count=format_loss_risk_count,
    )
