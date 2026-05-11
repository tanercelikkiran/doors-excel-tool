"""Tests for api/staging.py — load_excel_to_staging."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import openpyxl
import pytest

from doors_excel.core.transformation.hashing import hash_markdown
from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
from doors_excel.infrastructure.database.schema import apply_schema


def _make_module_config() -> ModuleConfig:
    return ModuleConfig(
        module_path="/proj/mod",
        column_mappings=[
            ColumnMapping(column="Object Text", attribute="Object Text", attribute_type="Text"),
        ],
    )


def _make_module_config_mixed() -> ModuleConfig:
    """Config with one Text column and one String column."""
    return ModuleConfig(
        module_path="/proj/mod",
        column_mappings=[
            ColumnMapping(column="Object Text", attribute="Object Text", attribute_type="Text"),
            ColumnMapping(column="Short Name", attribute="Short Name", attribute_type="String"),
        ],
    )


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_schema(conn)
    return conn


def _make_worksheet(data: list[list]):
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in data:
        ws.append(row)
    return ws


class TestLoadExcelToStaging:
    def test_header_row_not_staged(self) -> None:
        from doors_excel.api.staging import load_excel_to_staging

        conn = _make_conn()
        ws = _make_worksheet([
            ["Absolute Number", "Object Text"],
            [1, "hello"],
        ])
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s1', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.commit()
        load_excel_to_staging(ws, conn, "s1", _make_module_config())
        rows = conn.execute("SELECT * FROM staging_excel WHERE session_id = 's1'").fetchall()
        # Data row produces 2 staged cells (Absolute Number, Object Text)
        assert len(rows) == 2

    def test_object_id_resolved_from_absolute_number_column(self) -> None:
        from doors_excel.api.staging import load_excel_to_staging

        conn = _make_conn()
        ws = _make_worksheet([
            ["Absolute Number", "Object Text"],
            [42, "value"],
        ])
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s1', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.commit()
        load_excel_to_staging(ws, conn, "s1", _make_module_config())
        rows = conn.execute(
            "SELECT object_id FROM staging_excel WHERE session_id = 's1' AND attribute = 'Object Text'"
        ).fetchall()
        assert rows[0]["object_id"] == 42

    def test_empty_worksheet_inserts_nothing(self) -> None:
        from doors_excel.api.staging import load_excel_to_staging

        conn = _make_conn()
        ws = _make_worksheet([])
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s1', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.commit()
        load_excel_to_staging(ws, conn, "s1", _make_module_config())
        rows = conn.execute("SELECT * FROM staging_excel WHERE session_id = 's1'").fetchall()
        assert len(rows) == 0

    def test_multiple_rows_all_staged(self) -> None:
        from doors_excel.api.staging import load_excel_to_staging

        conn = _make_conn()
        ws = _make_worksheet([
            ["Absolute Number", "Object Text"],
            [1, "a"],
            [2, "b"],
        ])
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s1', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.commit()
        load_excel_to_staging(ws, conn, "s1", _make_module_config())
        rows = conn.execute(
            "SELECT DISTINCT object_id FROM staging_excel WHERE session_id = 's1'"
        ).fetchall()
        assert {r["object_id"] for r in rows} == {1, 2}

    def test_md_hash_computed_for_text_columns(self) -> None:
        from doors_excel.api.staging import load_excel_to_staging

        conn = _make_conn()
        ws = _make_worksheet([
            ["Absolute Number", "Object Text", "Short Name"],
            [1, "**bold content**", "short"],
        ])
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s1', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.commit()
        load_excel_to_staging(ws, conn, "s1", _make_module_config_mixed())

        rows = conn.execute(
            "SELECT md_hash FROM staging_excel WHERE session_id='s1' AND attribute='Object Text'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["md_hash"] == hash_markdown("**bold content**")

    def test_md_hash_null_for_non_text_columns(self) -> None:
        from doors_excel.api.staging import load_excel_to_staging

        conn = _make_conn()
        ws = _make_worksheet([
            ["Absolute Number", "Object Text", "Short Name"],
            [1, "**bold content**", "short"],
        ])
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('s1', 'f.xlsx', '/proj/mod', 'abc', 'current')"
        )
        conn.commit()
        load_excel_to_staging(ws, conn, "s1", _make_module_config_mixed())

        rows = conn.execute(
            "SELECT md_hash FROM staging_excel WHERE session_id='s1' AND attribute='Short Name'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["md_hash"] is None

    def test_string_cell_whitespace_is_trimmed(self) -> None:
        """REQ-FUN-211: leading/trailing whitespace stripped from String cells."""
        from doors_excel.api.staging import load_excel_to_staging

        conn = _make_conn()
        ws = _make_worksheet([
            ["Absolute Number", "Short Name"],
            [1, "  hello  "],   # leading + trailing space
        ])
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('sid1', 'f.xlsx', '/p/mod', 'abc', 'current')"
        )
        conn.commit()

        mod_cfg = ModuleConfig(
            module_path="/p/mod",
            column_mappings=[
                ColumnMapping(column="Short Name", attribute="Short Name", attribute_type="String"),
            ],
        )
        load_excel_to_staging(ws, conn, "sid1", mod_cfg)

        row = conn.execute(
            "SELECT value FROM staging_excel WHERE session_id='sid1' AND attribute='Short Name'"
        ).fetchone()
        assert row["value"] == "hello"

    def test_string_cell_whitespace_preserved_when_disabled(self) -> None:
        """REQ-FUN-211: trimming can be disabled."""
        from doors_excel.api.staging import load_excel_to_staging

        conn = _make_conn()
        ws = _make_worksheet([
            ["Absolute Number", "Short Name"],
            [1, "  hello  "],
        ])
        conn.execute(
            "INSERT INTO sessions (session_id, excel_path, doors_module, excel_sha256, module_version)"
            " VALUES ('sid1', 'f.xlsx', '/p/mod', 'abc', 'current')"
        )
        conn.commit()

        mod_cfg = ModuleConfig(
            module_path="/p/mod",
            column_mappings=[
                ColumnMapping(column="Short Name", attribute="Short Name", attribute_type="String"),
            ],
        )
        load_excel_to_staging(ws, conn, "sid1", mod_cfg, trim_whitespace=False)

        row = conn.execute(
            "SELECT value FROM staging_excel WHERE session_id='sid1' AND attribute='Short Name'"
        ).fetchone()
        assert row["value"] == "  hello  "
