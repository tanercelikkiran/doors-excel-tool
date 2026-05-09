"""Unit tests for api/export.py — DoorsExporter is fully mocked."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import openpyxl
import pytest

from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
from doors_excel.api.sessions import SessionManager


def _make_module_config(attrs: list[str] | None = None) -> ModuleConfig:
    mappings = [
        ColumnMapping(column=a, attribute=a, attribute_type="Text")
        for a in (attrs or ["Object Text"])
    ]
    return ModuleConfig(module_path="/proj/mod", column_mappings=mappings)


def _raw_rows(object_id: int = 1, level: int = 1, attrs: list[str] | None = None) -> list[dict]:
    """Return fake DoorsExporter output rows for one object."""
    attrs = attrs or ["Object Text"]
    return [
        {
            "object_id": object_id,
            "level": level,
            "parent_id": None,
            "has_ole": 0,
            "object_type": "OBJECT",
            "attribute": a,
            "value": f"Value of {a}",
            "rtf_value": "",
            "md_hash": None,
        }
        for a in attrs
        # rtf_value="" skips RTF→Markdown conversion for most tests;
        # tests that need conversion override rtf_value explicitly.
    ]


class TestExportModule:
    def test_returns_path_to_xlsx(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        mock_conn = object()
        with patch(
            "doors_excel.api.export.DoorsExporter.export_module",
            return_value=_raw_rows(),
        ):
            out = export_module(
                "/proj/mod",
                _make_module_config(),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
            )
        assert out.exists()
        assert out.suffix == ".xlsx"

    def test_excel_has_header_row_with_object_id_column(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        mock_conn = object()
        with patch(
            "doors_excel.api.export.DoorsExporter.export_module",
            return_value=_raw_rows(),
        ):
            out = export_module(
                "/proj/mod",
                _make_module_config(),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
            )
        wb = openpyxl.load_workbook(out)
        ws = wb.active
        headers = [c.value for c in ws[1]]
        assert "Absolute Number" in headers

    def test_excel_contains_attribute_column(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        mock_conn = object()
        cfg = _make_module_config(["Object Text", "Short Name"])
        with patch(
            "doors_excel.api.export.DoorsExporter.export_module",
            return_value=_raw_rows(attrs=["Object Text", "Short Name"]),
        ):
            out = export_module("/proj/mod", cfg, tmp_path / "out.xlsx", doors_conn=mock_conn)
        wb = openpyxl.load_workbook(out)
        ws = wb.active
        headers = [c.value for c in ws[1]]
        assert "Object Text" in headers
        assert "Short Name" in headers

    def test_one_object_produces_one_data_row(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        mock_conn = object()
        with patch(
            "doors_excel.api.export.DoorsExporter.export_module",
            return_value=_raw_rows(object_id=42),
        ):
            out = export_module(
                "/proj/mod",
                _make_module_config(),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
            )
        wb = openpyxl.load_workbook(out)
        ws = wb.active
        data_rows = list(ws.iter_rows(min_row=2, values_only=True))
        assert len(data_rows) == 1
        assert 42 in data_rows[0]

    def test_rtf_converted_to_markdown_for_text_attributes(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        mock_conn = object()
        rows = _raw_rows()
        rows[0]["rtf_value"] = "{\\rtf1\\ansi {\\b Bold text}}"
        rows[0]["value"] = "Bold text"
        with patch(
            "doors_excel.api.export.DoorsExporter.export_module",
            return_value=rows,
        ):
            out = export_module(
                "/proj/mod",
                _make_module_config(["Object Text"]),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
            )
        wb = openpyxl.load_workbook(out)
        ws = wb.active
        headers = [c.value for c in ws[1]]
        col_idx = headers.index("Object Text") + 1
        cell_val = ws.cell(row=2, column=col_idx).value
        assert cell_val is not None
        assert "{\\rtf1" not in str(cell_val)

    def test_two_objects_produce_two_data_rows(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        mock_conn = object()
        rows = _raw_rows(object_id=1) + _raw_rows(object_id=2)
        with patch(
            "doors_excel.api.export.DoorsExporter.export_module",
            return_value=rows,
        ):
            out = export_module(
                "/proj/mod",
                _make_module_config(),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
            )
        wb = openpyxl.load_workbook(out)
        ws = wb.active
        data_rows = list(ws.iter_rows(min_row=2, values_only=True))
        assert len(data_rows) == 2

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        mock_conn = object()
        with patch(
            "doors_excel.api.export.DoorsExporter.export_module",
            return_value=[],
        ):
            out = export_module(
                "/proj/mod",
                _make_module_config(),
                tmp_path / "sub" / "out.xlsx",
                doors_conn=mock_conn,
            )
        assert out.exists()

    def test_module_path_embedded_in_workbook_metadata(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module
        from doors_excel.infrastructure.excel.metadata import get_module_path

        mock_conn = object()
        with patch(
            "doors_excel.api.export.DoorsExporter.export_module",
            return_value=_raw_rows(),
        ):
            out = export_module(
                "/proj/mod",
                _make_module_config(),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
            )
        wb = openpyxl.load_workbook(out)
        ws = wb.active
        module_path = get_module_path(wb, ws)
        assert module_path == "/proj/mod"


# ---------------------------------------------------------------------------
# Session-aware export
# ---------------------------------------------------------------------------

class TestSessionAwareExport:
    def test_staging_doors_populated_when_session_manager_provided(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        db_path = tmp_path / "test.db"
        mock_conn = object()
        rows = _raw_rows(object_id=7, attrs=["Object Text"])
        with patch("doors_excel.api.export.DoorsExporter.export_module", return_value=rows):
            mgr = SessionManager(db_path)
            export_module(
                "/proj/mod",
                _make_module_config(["Object Text"]),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
                session_manager=mgr,
            )
            staging = mgr.conn.execute(
                "SELECT * FROM staging_doors WHERE attribute = 'Object Text'"
            ).fetchall()
        assert len(staging) == 1
        assert staging[0]["object_id"] == 7

    def test_staging_baseline_populated_when_session_manager_provided(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        db_path = tmp_path / "test.db"
        mock_conn = object()
        rows = _raw_rows(object_id=7, attrs=["Object Text"])
        with patch("doors_excel.api.export.DoorsExporter.export_module", return_value=rows):
            mgr = SessionManager(db_path)
            export_module(
                "/proj/mod",
                _make_module_config(["Object Text"]),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
                session_manager=mgr,
            )
            baseline = mgr.conn.execute(
                "SELECT * FROM staging_baseline WHERE attribute = 'Object Text'"
            ).fetchall()
        assert len(baseline) == 1

    def test_rollback_snapshots_populated_when_session_manager_provided(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        db_path = tmp_path / "test.db"
        mock_conn = object()
        rows = _raw_rows(object_id=7, attrs=["Object Text"])
        with patch("doors_excel.api.export.DoorsExporter.export_module", return_value=rows):
            mgr = SessionManager(db_path)
            export_module(
                "/proj/mod",
                _make_module_config(["Object Text"]),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
                session_manager=mgr,
            )
            snaps = mgr.conn.execute("SELECT * FROM rollback_snapshots").fetchall()
        assert len(snaps) == 1
        assert snaps[0]["object_id"] == 7

    def test_no_session_created_when_session_manager_not_provided(self, tmp_path: Path) -> None:
        from doors_excel.api.export import export_module

        mock_conn = object()
        with patch("doors_excel.api.export.DoorsExporter.export_module", return_value=_raw_rows()):
            out = export_module(
                "/proj/mod",
                _make_module_config(),
                tmp_path / "out.xlsx",
                doors_conn=mock_conn,
            )
        assert out.exists()  # unchanged behaviour
