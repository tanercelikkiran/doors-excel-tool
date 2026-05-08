"""Tests for core/diff/conflict.py — apply_conflict_policy."""
from __future__ import annotations

import pytest

from doors_excel.core.diff.conflict import apply_conflict_policy
from doors_excel.core.diff.engine import compute_diff

from .conftest import SID, fetch_diff, insert_baseline, insert_doors, insert_excel


def _make_conflict(conn) -> None:
    """Insert one CONFLICT row: both excel and doors changed from baseline."""
    insert_baseline(conn, [{"object_id": 1, "attribute": "Body", "value": "original", "parent_id": None}])
    insert_doors(conn, [{"object_id": 1, "attribute": "Body", "value": "doors-edit"}])
    insert_excel(conn, [{"row_number": 1, "object_id": 1, "attribute": "Body", "value": "excel-edit"}])
    compute_diff(conn, SID)


class TestExcelWins:
    def test_returns_count_of_resolved_rows(self, conn) -> None:
        _make_conflict(conn)
        count = apply_conflict_policy(conn, SID, "excel-wins")
        assert count == 1

    def test_resolved_value_is_excel_value(self, conn) -> None:
        _make_conflict(conn)
        apply_conflict_policy(conn, SID, "excel-wins")
        rows = fetch_diff(conn, "CONFLICT")
        assert rows[0]["resolved_value"] == "excel-edit"

    def test_change_type_remains_conflict(self, conn) -> None:
        _make_conflict(conn)
        apply_conflict_policy(conn, SID, "excel-wins")
        rows = fetch_diff(conn, "CONFLICT")
        assert rows[0]["change_type"] == "CONFLICT"

    def test_multiple_conflicts_all_resolved(self, conn) -> None:
        for oid in (10, 11, 12):
            insert_baseline(conn, [{"object_id": oid, "attribute": "T", "value": "orig", "parent_id": None}])
            insert_doors(conn, [{"object_id": oid, "attribute": "T", "value": "d"}])
            insert_excel(conn, [{"row_number": oid, "object_id": oid, "attribute": "T", "value": "e"}])
        compute_diff(conn, SID)
        count = apply_conflict_policy(conn, SID, "excel-wins")
        assert count == 3

    def test_no_conflict_rows_returns_zero(self, conn) -> None:
        count = apply_conflict_policy(conn, SID, "excel-wins")
        assert count == 0


class TestDoorsWins:
    def test_resolved_value_is_doors_value(self, conn) -> None:
        _make_conflict(conn)
        apply_conflict_policy(conn, SID, "doors-wins")
        rows = fetch_diff(conn, "CONFLICT")
        assert rows[0]["resolved_value"] == "doors-edit"

    def test_returns_resolved_count(self, conn) -> None:
        _make_conflict(conn)
        count = apply_conflict_policy(conn, SID, "doors-wins")
        assert count == 1

    def test_updated_rows_unaffected(self, conn) -> None:
        # Also add an UPDATED row — it must not get resolved_value set
        insert_baseline(conn, [{"object_id": 2, "attribute": "X", "value": "orig", "parent_id": None}])
        insert_doors(conn, [{"object_id": 2, "attribute": "X", "value": "orig"}])
        insert_excel(conn, [{"row_number": 2, "object_id": 2, "attribute": "X", "value": "edited"}])
        _make_conflict(conn)
        apply_conflict_policy(conn, SID, "doors-wins")
        updated = fetch_diff(conn, "UPDATED")
        assert all(r["resolved_value"] is None for r in updated)


class TestContentBased:
    def test_returns_zero(self, conn) -> None:
        _make_conflict(conn)
        count = apply_conflict_policy(conn, SID, "content-based")
        assert count == 0

    def test_resolved_value_remains_null(self, conn) -> None:
        _make_conflict(conn)
        apply_conflict_policy(conn, SID, "content-based")
        rows = fetch_diff(conn, "CONFLICT")
        assert rows[0]["resolved_value"] is None

    def test_no_rows_returns_zero(self, conn) -> None:
        count = apply_conflict_policy(conn, SID, "content-based")
        assert count == 0


class TestSessionIsolation:
    def test_only_current_session_resolved(self, conn) -> None:
        other_sid = "other-session"
        # CONFLICT in another session
        conn.execute(
            """
            INSERT INTO diff_results (session_id, object_id, attribute, change_type,
                                      excel_value, doors_value, baseline_value)
            VALUES (?, 99, 'X', 'CONFLICT', 'e', 'd', 'orig')
            """,
            (other_sid,),
        )
        conn.commit()
        _make_conflict(conn)
        apply_conflict_policy(conn, SID, "excel-wins")
        # other session's resolved_value must remain NULL
        row = conn.execute(
            "SELECT resolved_value FROM diff_results WHERE session_id = ? AND object_id = 99",
            (other_sid,),
        ).fetchone()
        assert row[0] is None
