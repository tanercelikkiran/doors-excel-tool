"""Tests for core/diff/engine.py — compute_diff and baseline_mismatch_check."""
from __future__ import annotations

import pytest

from doors_excel.core.diff.engine import DiffStats, baseline_mismatch_check, compute_diff

from .conftest import (
    SID,
    fetch_diff,
    insert_baseline,
    insert_doors,
    insert_excel,
)


# ---------------------------------------------------------------------------
# DiffStats
# ---------------------------------------------------------------------------

class TestDiffStats:
    def test_total_sums_all_fields(self) -> None:
        s = DiffStats(new_count=1, deleted_count=2, updated_count=3,
                      conflict_count=4, moved_count=5)
        assert s.total == 15

    def test_total_all_zeros(self) -> None:
        s = DiffStats(0, 0, 0, 0, 0)
        assert s.total == 0

    def test_frozen(self) -> None:
        s = DiffStats(1, 0, 0, 0, 0)
        with pytest.raises(Exception):
            s.new_count = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# NEW objects
# ---------------------------------------------------------------------------

class TestNewObjects:
    def test_null_object_id_is_new(self, conn) -> None:
        insert_excel(conn, [{"row_number": 1, "object_id": None, "attribute": "Title", "value": "Brand new"}])
        stats = compute_diff(conn, SID)
        assert stats.new_count == 1

    def test_new_row_has_correct_change_type(self, conn) -> None:
        insert_excel(conn, [{"row_number": 5, "object_id": None, "attribute": "Title", "value": "x"}])
        compute_diff(conn, SID)
        rows = fetch_diff(conn, "NEW")
        assert len(rows) == 1
        assert rows[0]["change_type"] == "NEW"

    def test_new_row_preserves_row_number(self, conn) -> None:
        insert_excel(conn, [{"row_number": 7, "object_id": None, "attribute": "Title", "value": "y"}])
        compute_diff(conn, SID)
        rows = fetch_diff(conn, "NEW")
        assert rows[0]["row_number"] == 7

    def test_multiple_attrs_on_new_object_counted_once(self, conn) -> None:
        # Two attributes in same row but object_id is NULL for each
        insert_excel(conn, [
            {"row_number": 1, "object_id": None, "attribute": "Title", "value": "T"},
            {"row_number": 1, "object_id": None, "attribute": "Body", "value": "B"},
        ])
        stats = compute_diff(conn, SID)
        # DISTINCT on row_number — only 1 NEW row per row
        assert stats.new_count == 1

    def test_existing_object_not_new(self, conn) -> None:
        insert_baseline(conn, [{"object_id": 10, "attribute": "Title", "value": "v", "parent_id": None}])
        insert_doors(conn, [{"object_id": 10, "attribute": "Title", "value": "v"}])
        insert_excel(conn, [{"row_number": 1, "object_id": 10, "attribute": "Title", "value": "v"}])
        stats = compute_diff(conn, SID)
        assert stats.new_count == 0


# ---------------------------------------------------------------------------
# DELETED objects
# ---------------------------------------------------------------------------

class TestDeletedObjects:
    def test_missing_from_excel_is_deleted(self, conn) -> None:
        insert_baseline(conn, [{"object_id": 20, "attribute": "Title", "value": "x", "parent_id": None}])
        # no insert_excel row for object 20
        stats = compute_diff(conn, SID)
        assert stats.deleted_count == 1

    def test_deleted_row_has_null_attribute(self, conn) -> None:
        insert_baseline(conn, [{"object_id": 30, "attribute": "Title", "value": "x", "parent_id": None}])
        compute_diff(conn, SID)
        rows = fetch_diff(conn, "DELETED")
        assert rows[0]["attribute"] is None

    def test_object_present_in_excel_not_deleted(self, conn) -> None:
        insert_baseline(conn, [{"object_id": 40, "attribute": "Title", "value": "v", "parent_id": None}])
        insert_doors(conn, [{"object_id": 40, "attribute": "Title", "value": "v"}])
        insert_excel(conn, [{"row_number": 1, "object_id": 40, "attribute": "Title", "value": "v"}])
        stats = compute_diff(conn, SID)
        assert stats.deleted_count == 0

    def test_multiple_baseline_attrs_produce_one_deleted_row(self, conn) -> None:
        insert_baseline(conn, [
            {"object_id": 50, "attribute": "Title", "value": "t", "parent_id": None},
            {"object_id": 50, "attribute": "Body",  "value": "b", "parent_id": None},
        ])
        stats = compute_diff(conn, SID)
        # DISTINCT on object_id → one DELETED row
        assert stats.deleted_count == 1


# ---------------------------------------------------------------------------
# UPDATED and CONFLICT attributes
# ---------------------------------------------------------------------------

class TestAttributeChanges:
    def _setup_three_way(self, conn, *, excel_val, doors_val, baseline_val="original") -> None:
        insert_baseline(conn, [{"object_id": 100, "attribute": "Body", "value": baseline_val, "parent_id": None}])
        insert_doors(conn, [{"object_id": 100, "attribute": "Body", "value": doors_val}])
        insert_excel(conn, [{"row_number": 1, "object_id": 100, "attribute": "Body", "value": excel_val}])

    def test_unchanged_not_in_diff(self, conn) -> None:
        self._setup_three_way(conn, excel_val="original", doors_val="original")
        stats = compute_diff(conn, SID)
        assert stats.updated_count == 0
        assert stats.conflict_count == 0

    def test_excel_changed_doors_unchanged_is_update(self, conn) -> None:
        self._setup_three_way(conn, excel_val="edited", doors_val="original")
        stats = compute_diff(conn, SID)
        assert stats.updated_count == 1
        assert stats.conflict_count == 0

    def test_both_changed_is_conflict(self, conn) -> None:
        self._setup_three_way(conn, excel_val="excel-edit", doors_val="doors-edit")
        stats = compute_diff(conn, SID)
        assert stats.conflict_count == 1
        assert stats.updated_count == 0

    def test_updated_row_stores_values(self, conn) -> None:
        self._setup_three_way(conn, excel_val="new-text", doors_val="original")
        compute_diff(conn, SID)
        rows = fetch_diff(conn, "UPDATED")
        assert rows[0]["excel_value"] == "new-text"
        assert rows[0]["doors_value"] == "original"
        assert rows[0]["baseline_value"] == "original"

    def test_conflict_row_stores_all_three_values(self, conn) -> None:
        self._setup_three_way(conn, excel_val="excel-edit", doors_val="doors-edit")
        compute_diff(conn, SID)
        rows = fetch_diff(conn, "CONFLICT")
        assert rows[0]["excel_value"] == "excel-edit"
        assert rows[0]["doors_value"] == "doors-edit"
        assert rows[0]["baseline_value"] == "original"

    def test_null_value_null_safe_comparison(self, conn) -> None:
        # baseline=NULL, excel=NULL → should be UNCHANGED (not UPDATED)
        insert_baseline(conn, [{"object_id": 200, "attribute": "Body", "value": None, "parent_id": None}])
        insert_doors(conn, [{"object_id": 200, "attribute": "Body", "value": None}])
        insert_excel(conn, [{"row_number": 1, "object_id": 200, "attribute": "Body", "value": None}])
        stats = compute_diff(conn, SID)
        assert stats.updated_count == 0
        assert stats.conflict_count == 0

    def test_null_to_value_is_update(self, conn) -> None:
        # baseline=NULL, excel="new", doors=NULL → UPDATED
        insert_baseline(conn, [{"object_id": 201, "attribute": "Body", "value": None, "parent_id": None}])
        insert_doors(conn, [{"object_id": 201, "attribute": "Body", "value": None}])
        insert_excel(conn, [{"row_number": 1, "object_id": 201, "attribute": "Body", "value": "new"}])
        stats = compute_diff(conn, SID)
        assert stats.updated_count == 1


# ---------------------------------------------------------------------------
# MOVED objects
# ---------------------------------------------------------------------------

class TestMovedObjects:
    def test_parent_changed_is_moved(self, conn) -> None:
        # baseline parent_id=1, excel reports parent=2
        insert_baseline(conn, [{"object_id": 300, "attribute": "_Parent_ID", "value": "1", "parent_id": 1}])
        insert_doors(conn, [{"object_id": 300, "attribute": "_Parent_ID", "value": "1"}])
        insert_excel(conn, [{"row_number": 1, "object_id": 300, "attribute": "_Parent_ID", "value": "2"}])
        stats = compute_diff(conn, SID)
        assert stats.moved_count == 1

    def test_parent_unchanged_not_moved(self, conn) -> None:
        insert_baseline(conn, [{"object_id": 301, "attribute": "_Parent_ID", "value": "1", "parent_id": 1}])
        insert_doors(conn, [{"object_id": 301, "attribute": "_Parent_ID", "value": "1"}])
        insert_excel(conn, [{"row_number": 1, "object_id": 301, "attribute": "_Parent_ID", "value": "1"}])
        stats = compute_diff(conn, SID)
        assert stats.moved_count == 0

    def test_deleted_object_not_moved(self, conn) -> None:
        # Object 302 is in baseline with parent_id=1 but absent from excel → DELETED, not MOVED
        insert_baseline(conn, [{"object_id": 302, "attribute": "_Parent_ID", "value": "1", "parent_id": 1}])
        insert_doors(conn, [{"object_id": 302, "attribute": "_Parent_ID", "value": "1"}])
        # no excel row → DELETED
        stats = compute_diff(conn, SID)
        assert stats.deleted_count == 1
        assert stats.moved_count == 0

    def test_custom_parent_id_attr(self, conn) -> None:
        insert_baseline(conn, [{"object_id": 303, "attribute": "ParentID", "value": "5", "parent_id": 5}])
        insert_doors(conn, [{"object_id": 303, "attribute": "ParentID", "value": "5"}])
        insert_excel(conn, [{"row_number": 1, "object_id": 303, "attribute": "ParentID", "value": "9"}])
        stats = compute_diff(conn, SID, parent_id_attr="ParentID")
        assert stats.moved_count == 1


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_rerun_clears_previous_results(self, conn) -> None:
        insert_excel(conn, [{"row_number": 1, "object_id": None, "attribute": "Title", "value": "new"}])
        compute_diff(conn, SID)
        stats2 = compute_diff(conn, SID)
        # Second run must not double-count
        assert stats2.new_count == 1

    def test_empty_staging_tables_give_zero_stats(self, conn) -> None:
        stats = compute_diff(conn, SID)
        assert stats.total == 0


# ---------------------------------------------------------------------------
# baseline_mismatch_check
# ---------------------------------------------------------------------------

class TestBaselineMismatchCheck:
    def test_no_mismatch_returns_zero(self, conn) -> None:
        # doors and baseline have same objects
        insert_baseline(conn, [{"object_id": 400, "attribute": "Title", "value": "v", "parent_id": None}])
        insert_doors(conn, [{"object_id": 400, "attribute": "Title", "value": "v"}])
        insert_excel(conn, [{"row_number": 1, "object_id": 400, "attribute": "Title", "value": "v"}])
        assert baseline_mismatch_check(conn, SID) == 0

    def test_doors_only_object_counted(self, conn) -> None:
        # object 500 exists in DOORS but NOT in baseline or excel
        insert_doors(conn, [{"object_id": 500, "attribute": "Title", "value": "added"}])
        assert baseline_mismatch_check(conn, SID) == 1

    def test_object_in_baseline_not_mismatch(self, conn) -> None:
        insert_baseline(conn, [{"object_id": 501, "attribute": "Title", "value": "v", "parent_id": None}])
        insert_doors(conn, [{"object_id": 501, "attribute": "Title", "value": "v"}])
        assert baseline_mismatch_check(conn, SID) == 0

    def test_object_in_excel_not_mismatch(self, conn) -> None:
        insert_doors(conn, [{"object_id": 502, "attribute": "Title", "value": "v"}])
        insert_excel(conn, [{"row_number": 1, "object_id": 502, "attribute": "Title", "value": "v"}])
        assert baseline_mismatch_check(conn, SID) == 0

    def test_multiple_attrs_same_object_counted_once(self, conn) -> None:
        insert_doors(conn, [
            {"object_id": 503, "attribute": "Title", "value": "a"},
            {"object_id": 503, "attribute": "Body",  "value": "b"},
        ])
        assert baseline_mismatch_check(conn, SID) == 1

    def test_empty_staging_returns_zero(self, conn) -> None:
        assert baseline_mismatch_check(conn, SID) == 0


# ---------------------------------------------------------------------------
# md_hash bypass (REQ-FUN-105.4)
# ---------------------------------------------------------------------------

def test_md_hash_column_present_in_staging_excel(conn) -> None:
    """staging_excel.md_hash column exists (REQ-FUN-105.4)."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(staging_excel)").fetchall()]
    assert "md_hash" in cols


def test_md_hash_bypass_classifies_unchanged(conn) -> None:
    """Objects with matching md_hash are classified UNCHANGED even if string differs (REQ-FUN-105.4)."""
    same_hash = "abc123"
    conn.execute(
        "INSERT INTO staging_baseline (session_id, object_id, attribute, value)"
        " VALUES (?, 1, 'Object Text', 'original rtf text')",
        (SID,),
    )
    conn.execute(
        "INSERT INTO staging_doors (session_id, object_id, attribute, value, md_hash, has_ole)"
        " VALUES (?, 1, 'Object Text', 'original rtf text', ?, 0)",
        (SID, same_hash),
    )
    # Excel has a slightly different string (RTF->MD round-trip drift) but same hash
    conn.execute(
        "INSERT INTO staging_excel (session_id, row_number, object_id, attribute, value, md_hash)"
        " VALUES (?, 2, 1, 'Object Text', 'original rtf text (normalized)', ?)",
        (SID, same_hash),
    )
    conn.commit()

    stats = compute_diff(conn, SID)
    assert stats.updated_count == 0
    assert stats.conflict_count == 0


def test_md_hash_bypass_does_not_suppress_conflict_when_doors_also_changed(conn) -> None:
    """When DOORS diverged from baseline, matching hashes must not suppress a CONFLICT."""
    same_hash = "abc123"
    conn.execute(
        "INSERT INTO staging_baseline (session_id, object_id, attribute, value)"
        " VALUES (?, 1, 'Object Text', 'foo')",
        (SID,),
    )
    conn.execute(
        "INSERT INTO staging_doors"
        " (session_id, object_id, attribute, value, md_hash, has_ole)"
        " VALUES (?, 1, 'Object Text', 'bar', ?, 0)",
        (SID, same_hash),
    )
    conn.execute(
        "INSERT INTO staging_excel"
        " (session_id, row_number, object_id, attribute, value, md_hash)"
        " VALUES (?, 2, 1, 'Object Text', 'bar', ?)",
        (SID, same_hash),
    )
    conn.commit()
    stats = compute_diff(conn, SID)
    assert stats.conflict_count == 1
    assert stats.updated_count == 0
