"""Tests for core/validation/validator.py — validate_session and helpers."""
from __future__ import annotations

import pytest

from doors_excel.core.validation.validator import ValidationResult, validate_session

from .conftest import SID, basic_config, fetch_errors, insert_excel_row


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

class TestValidationResult:
    def test_has_errors_true_when_blocking(self) -> None:
        r = ValidationResult(blocking_count=1, warning_count=0)
        assert r.has_errors is True

    def test_has_errors_false_when_clean(self) -> None:
        r = ValidationResult(blocking_count=0, warning_count=5)
        assert r.has_errors is False

    def test_total_sums_both(self) -> None:
        r = ValidationResult(blocking_count=2, warning_count=3)
        assert r.total == 5


# ---------------------------------------------------------------------------
# validate_session — idempotency and empty staging
# ---------------------------------------------------------------------------

class TestValidateSessionBasics:
    def test_empty_staging_returns_zero_errors(self, conn, basic_config) -> None:
        result = validate_session(conn, SID, basic_config)
        assert result.blocking_count == 0

    def test_idempotent_on_rerun(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {"Object Text": "x", "Short Name": "a", "Status": "Open"})
        validate_session(conn, SID, basic_config)
        result2 = validate_session(conn, SID, basic_config)
        # Should not double-count errors
        assert result2.blocking_count == validate_session(conn, SID, basic_config).blocking_count

    def test_valid_row_produces_no_errors(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "hello",
            "Short Name": "x" * 10,
            "Status": "Open",
            "Tags": "Alpha",
        })
        result = validate_session(conn, SID, basic_config)
        assert result.blocking_count == 0


# ---------------------------------------------------------------------------
# MISSING_COLUMN
# ---------------------------------------------------------------------------

class TestMissingColumn:
    def test_missing_mapped_column_reported(self, conn, basic_config) -> None:
        # Only provide some columns — "Short Name" will be missing
        insert_excel_row(conn, 1, 10, {"Object Text": "hello"})
        validate_session(conn, SID, basic_config)
        errors = fetch_errors(conn, "MISSING_COLUMN")
        missing = {e["attribute"] for e in errors}
        assert "Short Name" in missing
        assert "Status" in missing
        assert "Tags" in missing

    def test_all_columns_present_no_missing_error(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "x",
            "Short Name": "y",
            "Status": "Open",
            "Tags": "Alpha",
        })
        validate_session(conn, SID, basic_config)
        assert fetch_errors(conn, "MISSING_COLUMN") == []

    def test_missing_column_error_is_blocking(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {"Object Text": "x"})
        validate_session(conn, SID, basic_config)
        errors = fetch_errors(conn, "MISSING_COLUMN")
        assert all(e["severity"] == "BLOCKING" for e in errors)

    def test_row_number_zero_for_missing_column(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {"Object Text": "x"})
        validate_session(conn, SID, basic_config)
        errors = fetch_errors(conn, "MISSING_COLUMN")
        assert all(e["row_number"] == 0 for e in errors)


# ---------------------------------------------------------------------------
# STR_LEN_EXCEEDED
# ---------------------------------------------------------------------------

class TestStringLength:
    def test_value_over_1024_is_blocking(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "ok",
            "Short Name": "x" * 1025,
            "Status": "Open",
            "Tags": "Alpha",
        })
        validate_session(conn, SID, basic_config)
        errors = fetch_errors(conn, "STR_LEN_EXCEEDED")
        assert len(errors) == 1
        assert errors[0]["attribute"] == "Short Name"
        assert errors[0]["severity"] == "BLOCKING"

    def test_exactly_1024_chars_is_ok(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "ok",
            "Short Name": "x" * 1024,
            "Status": "Open",
            "Tags": "Alpha",
        })
        result = validate_session(conn, SID, basic_config)
        assert fetch_errors(conn, "STR_LEN_EXCEEDED") == []

    def test_text_type_not_length_checked(self, conn, basic_config) -> None:
        # Object Text is attribute_type="Text" — no length limit
        insert_excel_row(conn, 1, 10, {
            "Object Text": "x" * 9999,
            "Short Name": "y",
            "Status": "Open",
            "Tags": "Alpha",
        })
        validate_session(conn, SID, basic_config)
        assert fetch_errors(conn, "STR_LEN_EXCEEDED") == []

    def test_multiple_offending_rows(self, conn, basic_config) -> None:
        for row in (1, 2, 3):
            insert_excel_row(conn, row, row * 10, {
                "Object Text": "ok",
                "Short Name": "x" * 2000,
                "Status": "Open",
                "Tags": "Alpha",
            })
        validate_session(conn, SID, basic_config)
        assert len(fetch_errors(conn, "STR_LEN_EXCEEDED")) == 3


# ---------------------------------------------------------------------------
# ENUM_MISMATCH
# ---------------------------------------------------------------------------

class TestEnumMismatch:
    def test_valid_enum_value_no_error(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "x", "Short Name": "y",
            "Status": "Open", "Tags": "Alpha",
        })
        validate_session(conn, SID, basic_config)
        assert fetch_errors(conn, "ENUM_MISMATCH") == []

    def test_invalid_enum_value_is_blocking(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "x", "Short Name": "y",
            "Status": "Unknown", "Tags": "Alpha",
        })
        validate_session(conn, SID, basic_config)
        errors = fetch_errors(conn, "ENUM_MISMATCH")
        assert len(errors) == 1
        assert errors[0]["attribute"] == "Status"
        assert errors[0]["severity"] == "BLOCKING"

    def test_null_enum_value_not_checked(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "x", "Short Name": "y",
            "Status": None, "Tags": "Alpha",
        })
        validate_session(conn, SID, basic_config)
        assert fetch_errors(conn, "ENUM_MISMATCH") == []

    def test_multienum_all_valid(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "x", "Short Name": "y",
            "Status": "Open", "Tags": "Alpha;Beta",
        })
        validate_session(conn, SID, basic_config)
        assert fetch_errors(conn, "ENUM_MISMATCH") == []

    def test_multienum_one_invalid_token(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "x", "Short Name": "y",
            "Status": "Open", "Tags": "Alpha;Unknown;Gamma",
        })
        validate_session(conn, SID, basic_config)
        errors = fetch_errors(conn, "ENUM_MISMATCH")
        assert len(errors) == 1
        assert "Unknown" in errors[0]["message"]

    def test_multienum_quoted_value_with_semicolon(self, conn, basic_config) -> None:
        # RFC 4180: "Alpha;with;semicolons" is one token
        insert_excel_row(conn, 1, 10, {
            "Object Text": "x", "Short Name": "y",
            "Status": "Open", "Tags": '"Alpha;with;semicolons"',
        })
        validate_session(conn, SID, basic_config)
        # "Alpha;with;semicolons" (stripped of quotes) is not in enum_values → mismatch
        errors = fetch_errors(conn, "ENUM_MISMATCH")
        assert len(errors) == 1

    def test_no_enum_values_declared_skips_check(self, conn) -> None:
        from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
        config = ModuleConfig(
            module_path="/p",
            column_mappings=[
                ColumnMapping(column="Status", attribute="Status", attribute_type="Enum"),
            ],
        )
        insert_excel_row(conn, 1, 10, {"Status": "AnythingGoes"})
        result = validate_session(conn, SID, config)
        assert fetch_errors(conn, "ENUM_MISMATCH") == []


# ---------------------------------------------------------------------------
# ORPHAN_PLACEHOLDER
# ---------------------------------------------------------------------------

class TestOrphanPlaceholder:
    def test_placeholder_in_new_row_is_blocking(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, None, {
            "Object Text": "See [IMAGE: 1] for details",
            "Short Name": "new",
            "Status": "Open",
            "Tags": "Alpha",
        })
        validate_session(conn, SID, basic_config)
        errors = fetch_errors(conn, "ORPHAN_PLACEHOLDER")
        assert len(errors) == 1
        assert errors[0]["severity"] == "BLOCKING"

    def test_placeholder_in_existing_row_not_flagged(self, conn, basic_config) -> None:
        # object_id is NOT NULL → existing object → placeholder restoration is valid
        insert_excel_row(conn, 1, 42, {
            "Object Text": "See [IMAGE: 1] for details",
            "Short Name": "existing",
            "Status": "Open",
            "Tags": "Alpha",
        })
        validate_session(conn, SID, basic_config)
        assert fetch_errors(conn, "ORPHAN_PLACEHOLDER") == []

    def test_no_placeholder_new_row_clean(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, None, {
            "Object Text": "Plain text",
            "Short Name": "new",
            "Status": "Open",
            "Tags": "Alpha",
        })
        validate_session(conn, SID, basic_config)
        assert fetch_errors(conn, "ORPHAN_PLACEHOLDER") == []


# ---------------------------------------------------------------------------
# STRUCT_MARKER_OUT_OF_ORDER
# ---------------------------------------------------------------------------

class TestStructuralMarkers:
    def _insert_markers(self, conn, markers: list[tuple[int, str | None]]) -> None:
        """markers: list of (row_number, object_type_value)."""
        for row_num, ot in markers:
            insert_excel_row(conn, row_num, row_num * 10 if ot else None, {
                "Object Type": ot,
            })

    def test_valid_table_block_no_error(self, conn) -> None:
        from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
        config = ModuleConfig(
            module_path="/p",
            column_mappings=[ColumnMapping(column="Object Type", attribute="Object Type")],
        )
        self._insert_markers(conn, [
            (1, "TABLE_START"),
            (2, "TABLE_ROW"),
            (3, "TABLE_CELL"),
            (4, "TABLE_END"),
        ])
        result = validate_session(conn, SID, config)
        assert fetch_errors(conn, "STRUCT_MARKER_OUT_OF_ORDER") == []

    def test_table_row_outside_table_is_error(self, conn) -> None:
        from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
        config = ModuleConfig(
            module_path="/p",
            column_mappings=[ColumnMapping(column="Object Type", attribute="Object Type")],
        )
        self._insert_markers(conn, [(1, "TABLE_ROW")])
        validate_session(conn, SID, config)
        errors = fetch_errors(conn, "STRUCT_MARKER_OUT_OF_ORDER")
        assert len(errors) == 1
        assert "TABLE_ROW" in errors[0]["message"]

    def test_table_end_without_start_is_error(self, conn) -> None:
        from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
        config = ModuleConfig(
            module_path="/p",
            column_mappings=[ColumnMapping(column="Object Type", attribute="Object Type")],
        )
        self._insert_markers(conn, [(1, "TABLE_END")])
        validate_session(conn, SID, config)
        errors = fetch_errors(conn, "STRUCT_MARKER_OUT_OF_ORDER")
        assert len(errors) == 1
        assert "TABLE_END" in errors[0]["message"]

    def test_normal_objects_not_flagged(self, conn, basic_config) -> None:
        insert_excel_row(conn, 1, 10, {
            "Object Text": "hello",
            "Short Name": "s",
            "Status": "Open",
            "Tags": "Alpha",
            "Object Type": "OBJECT",
        })
        validate_session(conn, SID, basic_config)
        assert fetch_errors(conn, "STRUCT_MARKER_OUT_OF_ORDER") == []
