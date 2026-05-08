"""Shared fixtures for api/ tests."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import openpyxl
import pytest

from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
from doors_excel.infrastructure.database.schema import apply_schema


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def mem_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    apply_schema(conn)
    return conn


@pytest.fixture()
def basic_module_config() -> ModuleConfig:
    return ModuleConfig(
        module_path="/Project/TestModule",
        column_mappings=[
            ColumnMapping(column="Object Text", attribute="Object Text", attribute_type="Text"),
            ColumnMapping(column="Short Name", attribute="Short Name", attribute_type="String"),
            ColumnMapping(column="Status", attribute="Status", attribute_type="Enum",
                          enum_values=["Open", "Closed"]),
        ],
        object_id_column="Absolute Number",
    )


def make_xlsx(
    tmp_path: Path,
    headers: list[str],
    rows: list[list],
    filename: str = "test.xlsx",
) -> Path:
    """Create a minimal xlsx file with given headers and data rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TestModule"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    p = tmp_path / filename
    wb.save(p)
    return p
