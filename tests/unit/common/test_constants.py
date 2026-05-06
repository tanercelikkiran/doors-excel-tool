"""Unit tests for application-wide constants."""
from __future__ import annotations

from doors_excel.common.constants import (
    DEFAULT_COLUMN_NAMES,
    DEFAULT_OBJECT_TYPES,
    DXL_CHUNK_SIZE,
    DXL_LARGE_CONTENT_CHUNK,
    EXCEL_MAX_CELL_CHARS,
    LINK_ENTRY_PATTERN,
    LOG_LEVEL_NOTICE,
    OBJECT_ID_PATTERN,
)


class TestDXLChunkConstants:
    def test_dxl_chunk_size_is_48kb(self) -> None:
        assert DXL_CHUNK_SIZE == 48 * 1024

    def test_large_content_chunk_is_32kb(self) -> None:
        assert DXL_LARGE_CONTENT_CHUNK == 32 * 1024

    def test_large_chunk_less_than_chunk_size(self) -> None:
        assert DXL_LARGE_CONTENT_CHUNK < DXL_CHUNK_SIZE


class TestExcelConstants:
    def test_excel_max_cell_chars(self) -> None:
        assert EXCEL_MAX_CELL_CHARS == 32_767


class TestLogConstants:
    def test_notice_level_is_22(self) -> None:
        assert LOG_LEVEL_NOTICE == 22

    def test_notice_between_info_and_warning(self) -> None:
        assert 20 < LOG_LEVEL_NOTICE < 30  # INFO=20, WARNING=30


class TestDefaultObjectTypes:
    def test_is_dict(self) -> None:
        assert isinstance(DEFAULT_OBJECT_TYPES, dict)

    def test_object_maps_to_OBJECT(self) -> None:
        assert DEFAULT_OBJECT_TYPES["object"] == "OBJECT"

    def test_table_start_maps_correctly(self) -> None:
        assert DEFAULT_OBJECT_TYPES["table_start"] == "TABLE_START"

    def test_table_row_maps_correctly(self) -> None:
        assert DEFAULT_OBJECT_TYPES["table_row"] == "TABLE_ROW"

    def test_table_cell_maps_correctly(self) -> None:
        assert DEFAULT_OBJECT_TYPES["table_cell"] == "TABLE_CELL"

    def test_table_end_maps_correctly(self) -> None:
        assert DEFAULT_OBJECT_TYPES["table_end"] == "TABLE_END"

    def test_new_table_maps_correctly(self) -> None:
        assert DEFAULT_OBJECT_TYPES["new_table"] == "NEW_TABLE"

    def test_all_values_are_uppercase(self) -> None:
        for key, value in DEFAULT_OBJECT_TYPES.items():
            assert value == value.upper(), f"Value for {key!r} not uppercase: {value!r}"


class TestDefaultColumnNames:
    REQUIRED_KEYS = [
        "absolute_number", "object_text", "level", "parent_id",
        "placement", "object_type", "has_ole", "validation_feedback",
    ]

    def test_is_dict(self) -> None:
        assert isinstance(DEFAULT_COLUMN_NAMES, dict)

    def test_all_required_keys_present(self) -> None:
        for key in self.REQUIRED_KEYS:
            assert key in DEFAULT_COLUMN_NAMES, f"Missing key: {key!r}"


class TestRegexPatterns:
    def test_object_id_pattern_matches_integer(self) -> None:
        assert OBJECT_ID_PATTERN.fullmatch("12345") is not None

    def test_object_id_pattern_rejects_non_integer(self) -> None:
        assert OBJECT_ID_PATTERN.fullmatch("abc") is None

    def test_link_entry_pattern_matches_full_metadata_link(self) -> None:
        sample = '[42] (Type: "Satisfies", Mod: "My Module")'
        assert LINK_ENTRY_PATTERN.match(sample) is not None

    def test_link_entry_pattern_matches_del_prefix(self) -> None:
        sample = 'DEL: [42] (Type: "Satisfies", Mod: "My Module")'
        assert LINK_ENTRY_PATTERN.match(sample) is not None

    def test_link_entry_pattern_matches_simple_absolute_number(self) -> None:
        assert LINK_ENTRY_PATTERN.match("99") is not None

    def test_link_entry_pattern_matches_doors_url(self) -> None:
        assert LINK_ENTRY_PATTERN.match("doors://localhost:36677/1234") is not None
