"""Shared fixtures for core/validation tests."""
from __future__ import annotations

import sqlite3

import pytest

from doors_excel.core.validation.models import ColumnMapping, ModuleConfig
from doors_excel.infrastructure.database.schema import apply_schema

SID = "val-session-001"


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    apply_schema(c)
    return c


@pytest.fixture()
def basic_config() -> ModuleConfig:
    return ModuleConfig(
        module_path="/Project/Module",
        column_mappings=[
            ColumnMapping(column="Object Text", attribute="Object Text", attribute_type="Text"),
            ColumnMapping(column="Short Name", attribute="Short Name", attribute_type="String"),
            ColumnMapping(column="Status", attribute="Status", attribute_type="Enum",
                          enum_values=["Open", "Closed", "In Progress"]),
            ColumnMapping(column="Tags", attribute="Tags", attribute_type="MultiEnum",
                          enum_values=["Alpha", "Beta", "Gamma"]),
        ],
    )


def insert_excel_row(
    conn: sqlite3.Connection,
    row_number: int,
    object_id: int | None,
    attributes: dict[str, str | None],
) -> None:
    for attr, value in attributes.items():
        conn.execute(
            """
            INSERT INTO staging_excel (session_id, row_number, object_id, attribute, value)
            VALUES (?, ?, ?, ?, ?)
            """,
            (SID, row_number, object_id, attr, value),
        )
    conn.commit()


def fetch_errors(conn: sqlite3.Connection, error_code: str | None = None) -> list[dict]:
    if error_code:
        rows = conn.execute(
            "SELECT * FROM validation_errors WHERE session_id = ? AND error_code = ?",
            (SID, error_code),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM validation_errors WHERE session_id = ?", (SID,)
        ).fetchall()
    cols = [d[0] for d in conn.execute("SELECT * FROM validation_errors LIMIT 0").description]
    return [dict(zip(cols, r)) for r in rows]
