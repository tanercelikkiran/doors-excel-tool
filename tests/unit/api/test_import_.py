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
            count = execute_import("s3", conn, doors_conn=MagicMock(), conflict_policy="content-based")

        mock_instance.apply_updates.assert_not_called()
        assert count == 0

    def test_conflict_resolved_with_excel_wins_policy(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import

        conn = self._make_conn(tmp_path)
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s4', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.execute(
            "INSERT INTO diff_results (session_id, object_id, attribute, change_type,"
            " excel_value, doors_value, baseline_value, resolved_value)"
            " VALUES ('s4', 1, 'Object Text', 'CONFLICT', 'excel_val', 'doors_val', 'base_val', NULL)"
        )
        conn.commit()

        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            count = execute_import("s4", conn, doors_conn=MagicMock(), conflict_policy="excel-wins")

        mock_instance.apply_updates.assert_called_once()
        updates = mock_instance.apply_updates.call_args[0][1]
        assert len(updates) == 1
        assert updates[0]["value"] == "excel_val"
        assert count == 1

    def test_text_attribute_converted_to_rtf(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import
        from doors_excel.core.validation.models import ColumnMapping, ModuleConfig

        mod_config = ModuleConfig(
            module_path="/proj/mod",
            column_mappings=[
                ColumnMapping(column="Object Text", attribute="Object Text", attribute_type="Text"),
            ],
        )
        conn = self._make_conn(tmp_path)
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s5', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.execute(
            "INSERT INTO diff_results (session_id, object_id, attribute, change_type,"
            " excel_value, doors_value, baseline_value)"
            " VALUES ('s5', 1, 'Object Text', 'UPDATED', '**bold**', 'original', 'original')"
        )
        conn.commit()

        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            execute_import("s5", conn, doors_conn=MagicMock(), module_config=mod_config)

        updates = mock_instance.apply_updates.call_args[0][1]
        assert updates[0]["value"].startswith("{\\rtf1")

    def test_md_hash_bypass_restores_original_rtf(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import
        from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
        from doors_excel.core.transformation.hashing import hash_markdown

        mod_config = ModuleConfig(
            module_path="/proj/mod",
            column_mappings=[
                ColumnMapping(column="Object Text", attribute="Object Text", attribute_type="Text"),
            ],
        )
        same_hash = hash_markdown("hello world")
        conn = self._make_conn(tmp_path)
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s6', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.execute(
            "INSERT INTO diff_results (session_id, object_id, attribute, change_type,"
            " excel_value, doors_value, baseline_value)"
            " VALUES ('s6', 1, 'Object Text', 'UPDATED', 'hello world', 'hello world (rtf)', 'hello world (rtf)')"
        )
        # staging_excel with matching md_hash
        conn.execute(
            "INSERT INTO staging_excel (session_id, row_number, object_id, attribute, value, md_hash)"
            " VALUES ('s6', 2, 1, 'Object Text', 'hello world', ?)",
            (same_hash,),
        )
        # staging_doors with same md_hash
        conn.execute(
            "INSERT INTO staging_doors (session_id, object_id, attribute, value, md_hash, has_ole)"
            " VALUES ('s6', 1, 'Object Text', 'hello world (rtf)', ?, 0)",
            (same_hash,),
        )
        # rollback snapshot with original RTF
        conn.execute(
            "INSERT INTO rollback_snapshots (session_id, object_id, attribute, original_value, original_rtf)"
            " VALUES ('s6', 1, 'Object Text', 'hello world', '{\\rtf1 original}')"
        )
        conn.commit()

        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            execute_import("s6", conn, doors_conn=MagicMock(), module_config=mod_config)

        updates = mock_instance.apply_updates.call_args[0][1]
        assert updates[0]["value"] == "{\\rtf1 original}"


class TestExecuteNewObjects:
    def _make_conn_with_new_rows(self, tmp_path: Path) -> tuple:
        """Return (conn, session_id) with two NEW diff rows."""
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        conn.row_factory = sqlite3.Row
        apply_schema(conn)
        sid = "snew"
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES (?, 'f.xlsx', '/proj/mod', 'abc', 'current')",
            (sid,),
        )
        conn.execute(
            "INSERT INTO diff_results (session_id, object_id, attribute, change_type, row_number)"
            " VALUES (?, NULL, NULL, 'NEW', 2)",
            (sid,),
        )
        conn.execute(
            "INSERT INTO staging_excel (session_id, row_number, object_id, attribute, value)"
            " VALUES (?, 2, NULL, 'Object Text', 'new text')",
            (sid,),
        )
        conn.execute(
            "INSERT INTO staging_excel (session_id, row_number, object_id, attribute, value)"
            " VALUES (?, 2, NULL, '_Parent_ID', '5')",
            (sid,),
        )
        conn.commit()
        return conn, sid

    def test_new_objects_passed_to_create_objects(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import
        from doors_excel.core.validation.models import ColumnMapping, ModuleConfig

        mod_config = ModuleConfig(
            module_path="/proj/mod",
            column_mappings=[
                ColumnMapping(column="Object Text", attribute="Object Text", attribute_type="Text"),
            ],
        )
        conn, sid = self._make_conn_with_new_rows(tmp_path)

        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            count = execute_import(
                sid, conn, doors_conn=MagicMock(),
                include_new=True, module_config=mod_config,
            )

        mock_instance.create_objects.assert_called_once()
        objects = mock_instance.create_objects.call_args[0][1]
        assert len(objects) == 1
        assert objects[0]["parent_id"] == 5
        assert objects[0]["attributes"]["Object Text"] == "new text"
        assert "_Parent_ID" not in objects[0]["attributes"]
        assert "_Placement" not in objects[0]["attributes"]
        assert count >= 1

    def test_new_objects_skipped_when_include_new_false(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import

        conn, sid = self._make_conn_with_new_rows(tmp_path)

        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            execute_import(sid, conn, doors_conn=MagicMock(), include_new=False)

        mock_instance.create_objects.assert_not_called()


class TestExecuteDeletedObjects:
    def _make_conn_with_deleted_rows(self, tmp_path: Path) -> tuple:
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        conn.row_factory = sqlite3.Row
        apply_schema(conn)
        sid = "sdel"
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES (?, 'f.xlsx', '/proj/mod', 'abc', 'current')",
            (sid,),
        )
        conn.execute(
            "INSERT INTO diff_results (session_id, object_id, attribute, change_type)"
            " VALUES (?, 99, NULL, 'DELETED')",
            (sid,),
        )
        conn.commit()
        return conn, sid

    def test_deleted_objects_ignored_by_default(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import

        conn, sid = self._make_conn_with_deleted_rows(tmp_path)
        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            execute_import(sid, conn, doors_conn=MagicMock(), deletion_policy="ignore")

        mock_instance.delete_objects.assert_not_called()
        mock_instance.apply_updates.assert_not_called()

    def test_purge_calls_delete_objects(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import

        conn, sid = self._make_conn_with_deleted_rows(tmp_path)
        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            execute_import(sid, conn, doors_conn=MagicMock(), deletion_policy="purge")

        mock_instance.delete_objects.assert_called_once()
        args = mock_instance.delete_objects.call_args
        assert 99 in args[0][1]

    def test_soft_delete_calls_apply_updates_with_status(self, tmp_path: Path) -> None:
        from doors_excel.api.import_ import execute_import

        conn, sid = self._make_conn_with_deleted_rows(tmp_path)
        with patch("doors_excel.api.import_.DoorsImporter") as MockImporter:
            mock_instance = MagicMock()
            MockImporter.return_value = mock_instance
            execute_import(
                sid, conn, doors_conn=MagicMock(),
                deletion_policy="soft-delete",
                soft_delete_attribute="Status",
                soft_delete_value="Deleted",
            )

        mock_instance.apply_updates.assert_called_once()
        updates = mock_instance.apply_updates.call_args[0][1]
        assert updates[0] == {"object_id": 99, "attribute": "Status", "value": "Deleted"}
