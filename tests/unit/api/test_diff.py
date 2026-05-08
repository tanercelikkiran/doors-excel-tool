"""Tests for api/diff.py — run_diff."""
from __future__ import annotations

from doors_excel.api.diff import run_diff
from doors_excel.core.diff.summary import DiffSummary


def _insert_baseline(conn, session_id, rows):
    conn.executemany(
        "INSERT INTO staging_baseline (session_id, object_id, attribute, value, parent_id)"
        " VALUES (:sid, :oid, :attr, :val, NULL)",
        [{"sid": session_id, "oid": r[0], "attr": r[1], "val": r[2]} for r in rows],
    )
    conn.commit()


def _insert_doors(conn, session_id, rows):
    conn.executemany(
        "INSERT INTO staging_doors (session_id, object_id, attribute, value)"
        " VALUES (:sid, :oid, :attr, :val)",
        [{"sid": session_id, "oid": r[0], "attr": r[1], "val": r[2]} for r in rows],
    )
    conn.commit()


def _insert_excel(conn, session_id, rows):
    conn.executemany(
        "INSERT INTO staging_excel (session_id, row_number, object_id, attribute, value)"
        " VALUES (:sid, :row, :oid, :attr, :val)",
        [{"sid": session_id, "row": i + 1, "oid": r[0], "attr": r[1], "val": r[2]}
         for i, r in enumerate(rows)],
    )
    conn.commit()


SID = "diff-api-session"


class TestRunDiff:
    def test_returns_diff_summary(self, mem_conn) -> None:
        result = run_diff(mem_conn, SID)
        assert isinstance(result, DiffSummary)

    def test_empty_staging_returns_clean(self, mem_conn) -> None:
        result = run_diff(mem_conn, SID)
        assert result.is_clean is True
        assert result.total_changes == 0

    def test_updated_row_counted(self, mem_conn) -> None:
        _insert_baseline(mem_conn, SID, [(10, "T", "orig")])
        _insert_doors(mem_conn, SID, [(10, "T", "orig")])
        _insert_excel(mem_conn, SID, [(10, "T", "edited")])
        result = run_diff(mem_conn, SID)
        assert result.updated_count == 1
        assert result.is_clean is False

    def test_conflict_detected(self, mem_conn) -> None:
        _insert_baseline(mem_conn, SID, [(20, "T", "orig")])
        _insert_doors(mem_conn, SID, [(20, "T", "doors-change")])
        _insert_excel(mem_conn, SID, [(20, "T", "excel-change")])
        result = run_diff(mem_conn, SID)
        assert result.conflict_count == 1
        assert result.has_conflicts is True

    def test_baseline_mismatch_forwarded(self, mem_conn) -> None:
        # Object only in doors (not in baseline or excel)
        _insert_doors(mem_conn, SID, [(99, "T", "doors-only")])
        result = run_diff(mem_conn, SID)
        assert result.baseline_mismatch_count == 1
        assert result.has_baseline_mismatch is True

    def test_custom_parent_id_attr(self, mem_conn) -> None:
        # Insert baseline row directly so we can set parent_id column
        mem_conn.execute(
            "INSERT INTO staging_baseline (session_id, object_id, attribute, value, parent_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (SID, 30, "ParentID", "1", 1),
        )
        mem_conn.commit()
        _insert_doors(mem_conn, SID, [(30, "ParentID", "1")])
        _insert_excel(mem_conn, SID, [(30, "ParentID", "9")])
        result = run_diff(mem_conn, SID, parent_id_attr="ParentID")
        assert result.moved_count == 1

    def test_idempotent_rerun(self, mem_conn) -> None:
        _insert_baseline(mem_conn, SID, [(10, "T", "orig")])
        _insert_doors(mem_conn, SID, [(10, "T", "orig")])
        _insert_excel(mem_conn, SID, [(10, "T", "edited")])
        run_diff(mem_conn, SID)
        result2 = run_diff(mem_conn, SID)
        assert result2.updated_count == 1
