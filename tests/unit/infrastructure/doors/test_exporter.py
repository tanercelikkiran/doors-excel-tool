"""Unit tests for DoorsExporter — DoorsConnection is fully mocked."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from doors_excel.common.exceptions import DXLExecutionError


def _make_exporter(dxl_output: str) -> "DoorsExporter":  # type: ignore[name-defined]
    from doors_excel.infrastructure.doors.exporter import DoorsExporter
    mock_conn = MagicMock()
    mock_conn.run_dxl.return_value = dxl_output
    return DoorsExporter(mock_conn)


FS = "\x1f"
RS = "\x1e"


def _record(
    abs_no: str,
    level: str,
    parent_id: str,
    has_ole: str,
    *attr_pairs: str,
    obj_type: str = "OBJECT",
    parent_absno: str = "0",
    row_pos: str = "0",
    col_pos: str = "0",
) -> str:
    """Build a DXL record in the new 8-field-header format."""
    fields = [abs_no, level, parent_id, has_ole, obj_type, parent_absno, row_pos, col_pos] + list(attr_pairs)
    return FS.join(fields) + RS + "\n"


class TestParseOutput:
    def test_single_object_single_attribute(self) -> None:
        output = _record("42", "1", "", "0", "Hello world", "{\\rtf1 Hello world}")
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        assert len(rows) == 1
        r = rows[0]
        assert r["object_id"] == 42
        assert r["level"] == 1
        assert r["parent_id"] is None
        assert r["has_ole"] == 0
        assert r["attribute"] == "Object Text"
        assert r["value"] == "Hello world"
        assert r["rtf_value"] == "{\\rtf1 Hello world}"
        assert r["md_hash"] is None

    def test_two_objects_two_attributes(self) -> None:
        output = (
            _record("1", "1", "", "0", "Title", "{\\rtf1 Title}", "Hi", "")
            + _record("2", "2", "1", "0", "Body", "{\\rtf1 Body}", "lo", "")
        )
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text", "Short Name"])
        assert len(rows) == 4  # 2 objects × 2 attributes
        oids = {r["object_id"] for r in rows}
        assert oids == {1, 2}
        attrs = {(r["object_id"], r["attribute"]) for r in rows}
        assert ("Object Text" in {a for _, a in attrs})

    def test_parent_id_resolved(self) -> None:
        output = _record("10", "2", "5", "0", "Child", "")
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        assert rows[0]["parent_id"] == 5

    def test_object_id_zero_skipped(self) -> None:
        output = _record("0", "1", "", "0", "Ignored", "") + _record("1", "1", "", "0", "Kept", "")
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        assert all(r["object_id"] != 0 for r in rows)
        assert len(rows) == 1

    def test_doors_export_error_raises(self) -> None:
        output = "DOORS_EXPORT_ERROR: Cannot open module /missing\n"
        exporter = _make_exporter(output)
        with pytest.raises(DXLExecutionError):
            exporter.export_module("/missing", ["Object Text"])

    def test_empty_output_returns_empty_list(self) -> None:
        exporter = _make_exporter("")
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        assert rows == []

    def test_none_output_returns_empty_list(self) -> None:
        from doors_excel.infrastructure.doors.exporter import DoorsExporter
        mock_conn = MagicMock()
        mock_conn.run_dxl.return_value = None
        exporter = DoorsExporter(mock_conn)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        assert rows == []

    def test_has_ole_flag_parsed(self) -> None:
        output = _record("3", "1", "", "1", "OLE object", "{\\rtf1 ...}")
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        assert rows[0]["has_ole"] == 1

    def test_object_type_defaults_to_object(self) -> None:
        output = _record("1", "1", "", "0", "Text", "")
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        assert rows[0]["object_type"] == "OBJECT"

    def test_run_dxl_called_once(self) -> None:
        from doors_excel.infrastructure.doors.exporter import DoorsExporter
        mock_conn = MagicMock()
        mock_conn.run_dxl.return_value = ""
        exporter = DoorsExporter(mock_conn)
        exporter.export_module("/proj/mod", ["Object Text"])
        mock_conn.run_dxl.assert_called_once()

    def test_no_attributes_returns_empty(self) -> None:
        output = _record("1", "1", "", "0")
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", [])
        assert rows == []


class TestTableTypeParsing:
    def test_table_row_assigned_synthetic_negative_id(self) -> None:
        output = _record("0", "2", "42", "0", "Row text", "",
                         obj_type="TABLE_ROW", parent_absno="42", row_pos="1")
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        tr_rows = [r for r in rows if r["object_type"] == "TABLE_ROW"]
        assert len(tr_rows) == 1
        assert tr_rows[0]["object_id"] < 0
        assert tr_rows[0]["parent_absno"] == 42
        assert tr_rows[0]["row_position"] == 1
        assert tr_rows[0]["col_position"] is None

    def test_table_cell_parsed_with_all_position_fields(self) -> None:
        output = _record("0", "3", "42", "0", "Cell", "",
                         obj_type="TABLE_CELL", parent_absno="42", row_pos="1", col_pos="2")
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        tc_rows = [r for r in rows if r["object_type"] == "TABLE_CELL"]
        assert len(tc_rows) == 1
        assert tc_rows[0]["parent_absno"] == 42
        assert tc_rows[0]["row_position"] == 1
        assert tc_rows[0]["col_position"] == 2

    def test_table_end_injected_after_table_block(self) -> None:
        output = (
            _record("42", "1", "", "0", "", "", obj_type="TABLE")
            + _record("0", "2", "42", "0", "row", "", obj_type="TABLE_ROW", parent_absno="42", row_pos="1")
            + _record("1", "1", "", "0", "Normal obj", "")  # non-table follows
        )
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        types = [r["object_type"] for r in rows]
        assert "TABLE_END" in types
        te_idx = next(i for i, r in enumerate(rows) if r["object_type"] == "TABLE_END")
        obj_idx = next(i for i, r in enumerate(rows) if r["object_type"] == "OBJECT")
        assert te_idx < obj_idx

    def test_table_end_injected_at_end_of_module(self) -> None:
        output = (
            _record("42", "1", "", "0", "", "", obj_type="TABLE")
            + _record("0", "2", "42", "0", "row", "", obj_type="TABLE_ROW", parent_absno="42", row_pos="1")
        )
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        types = [r["object_type"] for r in rows]
        assert types[-1] == "TABLE_END"

    def test_table_end_has_parent_absno_of_table(self) -> None:
        output = (
            _record("99", "1", "", "0", "", "", obj_type="TABLE")
            + _record("0", "2", "99", "0", "row", "", obj_type="TABLE_ROW", parent_absno="99", row_pos="1")
        )
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        te = next(r for r in rows if r["object_type"] == "TABLE_END")
        assert te["parent_absno"] == 99

    def test_object_type_emitted_for_regular_object(self) -> None:
        output = _record("1", "1", "", "0", "Text", "")
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        assert rows[0]["object_type"] == "OBJECT"
        assert rows[0]["parent_absno"] is None
        assert rows[0]["row_position"] is None
        assert rows[0]["col_position"] is None

    def test_two_tables_each_get_own_table_end(self) -> None:
        output = (
            _record("10", "1", "", "0", "", "", obj_type="TABLE")
            + _record("0", "2", "10", "0", "r1", "", obj_type="TABLE_ROW", parent_absno="10", row_pos="1")
            + _record("20", "1", "", "0", "", "", obj_type="TABLE")
            + _record("0", "2", "20", "0", "r2", "", obj_type="TABLE_ROW", parent_absno="20", row_pos="1")
        )
        exporter = _make_exporter(output)
        rows = exporter.export_module("/proj/mod", ["Object Text"])
        table_ends = [r for r in rows if r["object_type"] == "TABLE_END"]
        assert len(table_ends) == 2
        parent_absno_values = {te["parent_absno"] for te in table_ends}
        assert parent_absno_values == {10, 20}
