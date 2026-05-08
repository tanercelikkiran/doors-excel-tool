"""Tests for core/diff/summary.py — DiffSummary and get_diff_summary."""
from __future__ import annotations

import pytest

from doors_excel.core.diff.engine import compute_diff
from doors_excel.core.diff.summary import DiffSummary, get_diff_summary

from .conftest import SID, insert_baseline, insert_doors, insert_excel


class TestDiffSummaryProperties:
    def test_total_changes_sums_five_counts(self) -> None:
        s = DiffSummary(1, 2, 3, 4, 5, 0)
        assert s.total_changes == 15

    def test_has_conflicts_true(self) -> None:
        s = DiffSummary(0, 0, 0, 1, 0, 0)
        assert s.has_conflicts is True

    def test_has_conflicts_false(self) -> None:
        s = DiffSummary(0, 0, 0, 0, 0, 0)
        assert s.has_conflicts is False

    def test_has_baseline_mismatch_true(self) -> None:
        s = DiffSummary(0, 0, 0, 0, 0, 3)
        assert s.has_baseline_mismatch is True

    def test_has_baseline_mismatch_false(self) -> None:
        s = DiffSummary(0, 0, 0, 0, 0, 0)
        assert s.has_baseline_mismatch is False

    def test_is_clean_all_zeros(self) -> None:
        s = DiffSummary(0, 0, 0, 0, 0, 0)
        assert s.is_clean is True

    def test_is_clean_false_with_changes(self) -> None:
        s = DiffSummary(1, 0, 0, 0, 0, 0)
        assert s.is_clean is False

    def test_is_clean_false_with_mismatch(self) -> None:
        s = DiffSummary(0, 0, 0, 0, 0, 1)
        assert s.is_clean is False

    def test_frozen(self) -> None:
        s = DiffSummary(0, 0, 0, 0, 0, 0)
        with pytest.raises(Exception):
            s.new_count = 1  # type: ignore[misc]


class TestGetDiffSummary:
    def test_empty_db_returns_zeros(self, conn) -> None:
        s = get_diff_summary(conn, SID)
        assert s.total_changes == 0
        assert s.baseline_mismatch_count == 0

    def test_counts_match_compute_diff(self, conn) -> None:
        # Set up one of each change type
        # NEW
        insert_excel(conn, [{"row_number": 1, "object_id": None, "attribute": "T", "value": "n"}])
        # DELETED
        insert_baseline(conn, [{"object_id": 20, "attribute": "T", "value": "d", "parent_id": None}])
        # UPDATED
        insert_baseline(conn, [{"object_id": 30, "attribute": "T", "value": "orig", "parent_id": None}])
        insert_doors(conn, [{"object_id": 30, "attribute": "T", "value": "orig"}])
        insert_excel(conn, [{"row_number": 2, "object_id": 30, "attribute": "T", "value": "upd"}])
        # CONFLICT
        insert_baseline(conn, [{"object_id": 40, "attribute": "T", "value": "orig", "parent_id": None}])
        insert_doors(conn, [{"object_id": 40, "attribute": "T", "value": "doors"}])
        insert_excel(conn, [{"row_number": 3, "object_id": 40, "attribute": "T", "value": "excel"}])
        # MOVED
        insert_baseline(conn, [{"object_id": 50, "attribute": "_Parent_ID", "value": "1", "parent_id": 1}])
        insert_doors(conn, [{"object_id": 50, "attribute": "_Parent_ID", "value": "1"}])
        insert_excel(conn, [{"row_number": 4, "object_id": 50, "attribute": "_Parent_ID", "value": "2"}])

        compute_diff(conn, SID)
        s = get_diff_summary(conn, SID)

        assert s.new_count == 1
        assert s.deleted_count == 1
        # _Parent_ID change for MOVED object also produces an UPDATED row
        assert s.updated_count == 2
        assert s.conflict_count == 1
        assert s.moved_count == 1
        assert s.total_changes == 6

    def test_baseline_mismatch_forwarded(self, conn) -> None:
        compute_diff(conn, SID)
        s = get_diff_summary(conn, SID, baseline_mismatch_count=7)
        assert s.baseline_mismatch_count == 7
        assert s.has_baseline_mismatch is True

    def test_is_clean_true_when_no_changes(self, conn) -> None:
        compute_diff(conn, SID)
        s = get_diff_summary(conn, SID, baseline_mismatch_count=0)
        assert s.is_clean is True

    def test_different_session_not_counted(self, conn) -> None:
        other_sid = "other-session"
        conn.execute(
            """
            INSERT INTO diff_results (session_id, object_id, attribute, change_type)
            VALUES (?, 99, 'T', 'UPDATED')
            """,
            (other_sid,),
        )
        conn.commit()
        s = get_diff_summary(conn, SID)
        assert s.updated_count == 0
