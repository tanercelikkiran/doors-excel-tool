"""Shared fixtures for core/diff tests."""
from __future__ import annotations

import sqlite3

import pytest

from doors_excel.infrastructure.database.schema import apply_schema


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with the full schema applied."""
    c = sqlite3.connect(":memory:")
    apply_schema(c)
    return c


SID = "test-session-001"


def insert_baseline(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO staging_baseline (session_id, object_id, attribute, value, parent_id)
        VALUES (:sid, :oid, :attr, :val, :parent_id)
        """,
        [
            {
                "sid": SID,
                "oid": r["object_id"],
                "attr": r["attribute"],
                "val": r.get("value"),
                "parent_id": r.get("parent_id"),
            }
            for r in rows
        ],
    )
    conn.commit()


def insert_doors(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO staging_doors (session_id, object_id, attribute, value)
        VALUES (:sid, :oid, :attr, :val)
        """,
        [
            {
                "sid": SID,
                "oid": r["object_id"],
                "attr": r["attribute"],
                "val": r.get("value"),
            }
            for r in rows
        ],
    )
    conn.commit()


def insert_excel(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO staging_excel (session_id, row_number, object_id, attribute, value)
        VALUES (:sid, :row, :oid, :attr, :val)
        """,
        [
            {
                "sid": SID,
                "row": r.get("row_number", 1),
                "oid": r.get("object_id"),
                "attr": r["attribute"],
                "val": r.get("value"),
            }
            for r in rows
        ],
    )
    conn.commit()


def fetch_diff(conn: sqlite3.Connection, change_type: str | None = None) -> list[dict]:
    if change_type:
        rows = conn.execute(
            "SELECT * FROM diff_results WHERE session_id = ? AND change_type = ?",
            (SID, change_type),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM diff_results WHERE session_id = ?",
            (SID,),
        ).fetchall()
    cols = [d[0] for d in conn.execute("SELECT * FROM diff_results LIMIT 0").description]
    return [dict(zip(cols, r)) for r in rows]
