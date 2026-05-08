"""SQL-based 3-way merge and change detection engine (SQLite CTEs)."""
from __future__ import annotations

from doors_excel.core.diff.conflict import apply_conflict_policy
from doors_excel.core.diff.engine import (
    DiffStats,
    baseline_mismatch_check,
    compute_diff,
)
from doors_excel.core.diff.summary import DiffSummary, get_diff_summary

__all__ = [
    # engine
    "DiffStats",
    "compute_diff",
    "baseline_mismatch_check",
    # conflict resolution
    "apply_conflict_policy",
    # summary
    "DiffSummary",
    "get_diff_summary",
]
