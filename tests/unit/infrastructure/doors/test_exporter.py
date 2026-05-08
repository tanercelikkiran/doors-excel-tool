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


def _record(*fields: str) -> str:
    """Build a single DXL record string (fields joined by FS, terminated with RS)."""
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
