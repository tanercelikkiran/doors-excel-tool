"""Tests for api/import_.py — stage_import and execute_import."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
from doors_excel.infrastructure.database.schema import apply_schema


def _make_module_config() -> ModuleConfig:
    return ModuleConfig(
        module_path="/proj/mod",
        column_mappings=[
            ColumnMapping(column="Object Text", attribute="Object Text", attribute_type="Text"),
        ],
    )


def _write_xlsx(tmp_path: Path, rows: list[list]) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "mod"
    for row in rows:
        ws.append(row)
    p = tmp_path / "data.xlsx"
    wb.save(p)
    return p


def _seed_staging(conn: sqlite3.Connection, session_id: str) -> None:
    """Seed staging tables so diff engine has data to work with."""
    conn.execute(
        "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
        " VALUES (?, 'f.xlsx', '/proj/mod', 'abc', 'current')",
        (session_id,),
    )
    # staging_baseline: object 1 had value "original"
    conn.execute(
        "INSERT INTO staging_baseline (session_id, object_id, attribute, value)"
        " VALUES (?, 1, 'Object Text', 'original')",
        (session_id,),
    )
    # staging_doors: object 1 still has "original" (DOORS unchanged)
    conn.execute(
        "INSERT INTO staging_doors (session_id, object_id, attribute, value, has_ole)"
        " VALUES (?, 1, 'Object Text', 'original', 0)",
        (session_id,),
    )
    # staging_excel: object 1 now has "updated" (user changed it)
    conn.execute(
        "INSERT INTO staging_excel (session_id, row_number, object_id, attribute, value)"
        " VALUES (?, 2, 1, 'Object Text', 'updated')",
        (session_id,),
    )
    conn.commit()


class TestStageImport:
    def test_returns_session_id_and_diff_stats(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import stage_import

        xlsx = _write_xlsx(tmp_path, [
            ["Absolute Number", "Object Text"],
            [1, "updated"],
        ])
        doors_rows = [
            {
                "object_id": 1, "level": 1, "parent_id": None, "has_ole": 0,
                "object_type": "OBJECT", "attribute": "Object Text",
                "value": "original", "rtf_value": "", "md_hash": None,
            }
        ]
        with patch("doors_excel.api.import_.DoorsExporter.export_module", return_value=doors_rows):
            session_id, stats = stage_import(
                xlsx,
                _make_module_config(),
                db_path=tmp_path / "test.db",
                doors_conn=object(),
            )
        assert isinstance(session_id, str)
        assert stats.updated_count >= 1

    def test_staging_excel_populated(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import stage_import
        from doors_excel.infrastructure.database.connection import init_database

        xlsx = _write_xlsx(tmp_path, [
            ["Absolute Number", "Object Text"],
            [1, "hello"],
        ])
        doors_rows = [
            {
                "object_id": 1, "level": 1, "parent_id": None, "has_ole": 0,
                "object_type": "OBJECT", "attribute": "Object Text",
                "value": "original", "rtf_value": "", "md_hash": None,
            }
        ]
        db_path = tmp_path / "test.db"
        with patch("doors_excel.api.import_.DoorsExporter.export_module", return_value=doors_rows):
            session_id, _ = stage_import(
                xlsx,
                _make_module_config(),
                db_path=db_path,
                doors_conn=object(),
            )
        conn = init_database(db_path)
        rows = conn.execute(
            "SELECT * FROM staging_excel WHERE session_id = ?", (session_id,)
        ).fetchall()
        conn.close()
        assert len(rows) > 0


class TestExecuteImport:
    def _make_conn(self, tmp_path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        conn.row_factory = sqlite3.Row
        apply_schema(conn)
        return conn

    def test_updated_rows_passed_to_importer(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import

        conn = self._make_conn(tmp_path)
        _seed_staging(conn, "s1")

        from doors_excel.core.diff.engine import compute_diff
        compute_diff(conn, "s1")

        mock_doors = MagicMock()
        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_importer_instance = MagicMock()
            MockImporter.return_value = mock_importer_instance
            execute_import("s1", conn, doors_conn=mock_doors)

        mock_importer_instance.apply_updates.assert_called_once()
        args = mock_importer_instance.apply_updates.call_args
        updates = args[0][1]  # second positional arg
        assert len(updates) == 1
        assert updates[0]["attribute"] == "Object Text"
        assert updates[0]["value"] == "updated"

    def test_returns_count_of_updates_applied(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import
        from doors_excel.core.diff.engine import compute_diff

        conn = self._make_conn(tmp_path)
        _seed_staging(conn, "s1")
        compute_diff(conn, "s1")

        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            MockImporter.return_value = MagicMock()
            count = execute_import("s1", conn, doors_conn=MagicMock())

        assert count == 1

    def test_no_updates_when_diff_results_empty(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import

        conn = self._make_conn(tmp_path)
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s2', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.commit()

        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            count = execute_import("s2", conn, doors_conn=MagicMock())

        mock_instance.apply_updates.assert_not_called()
        assert count == 0

    def test_conflict_rows_skipped_without_resolved_value(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import

        conn = self._make_conn(tmp_path)
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s3', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.execute(
            "INSERT INTO diff_results (session_id, object_id, attribute, change_type,"
            " excel_value, doors_value, baseline_value, resolved_value)"
            " VALUES ('s3', 1, 'Object Text', 'CONFLICT', 'excel', 'doors', 'base', NULL)"
        )
        conn.commit()

        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            count = execute_import("s3", conn, doors_conn=MagicMock())

        mock_instance.apply_updates.assert_not_called()
        assert count == 0
