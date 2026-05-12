"""Tests for smart_split — 32 767-char Excel cell limit handling (C-3)."""
from __future__ import annotations


class TestSmartSplit:
    def test_short_text_returns_single_chunk(self):
        from doors_excel.core.transformation.smart_split import smart_split
        result = smart_split("short text")
        assert result == ["short text"]

    def test_text_at_limit_returns_single_chunk(self):
        from doors_excel.core.transformation.smart_split import smart_split, EXCEL_CELL_LIMIT
        text = "x" * EXCEL_CELL_LIMIT
        result = smart_split(text)
        assert len(result) == 1
        assert result[0] == text

    def test_text_over_limit_splits_into_two(self):
        from doors_excel.core.transformation.smart_split import smart_split, EXCEL_CELL_LIMIT
        text = "x" * (EXCEL_CELL_LIMIT + 1)
        result = smart_split(text)
        assert len(result) == 2
        assert "".join(result) == text

    def test_splits_prefer_newline_boundary(self):
        from doors_excel.core.transformation.smart_split import smart_split, EXCEL_CELL_LIMIT
        # First paragraph fills limit-10 chars, second is 20 chars
        para1 = "a" * (EXCEL_CELL_LIMIT - 10)
        para2 = "b" * 20
        text = para1 + "\n" + para2
        result = smart_split(text)
        assert len(result) == 2
        # First chunk ends with the newline included
        assert result[0].rstrip("\n") == para1
        assert "b" * 20 in result[1]

    def test_split_column_headers_single(self):
        from doors_excel.core.transformation.smart_split import split_column_headers
        assert split_column_headers("Object Text", 1) == ["Object Text"]

    def test_split_column_headers_multiple(self):
        from doors_excel.core.transformation.smart_split import split_column_headers
        result = split_column_headers("Object Text", 3)
        assert result == ["Object Text", "Object Text_1", "Object Text_2"]

    def test_join_split_columns_single(self):
        from doors_excel.core.transformation.smart_split import join_split_columns
        row = {"Object Text": "hello"}
        assert join_split_columns("Object Text", row) == "hello"

    def test_join_split_columns_multiple(self):
        from doors_excel.core.transformation.smart_split import join_split_columns
        row = {"Object Text": "part1", "Object Text_1": "part2", "Object Text_2": "part3"}
        assert join_split_columns("Object Text", row) == "part1part2part3"

    def test_join_split_columns_missing_overflow_ignored(self):
        from doors_excel.core.transformation.smart_split import join_split_columns
        row = {"Object Text": "only"}
        assert join_split_columns("Object Text", row) == "only"
