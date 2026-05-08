"""Rollback API — generate an import-ready Excel from a session snapshot."""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

from doors_excel.infrastructure.excel.writer import create_workbook, save_workbook

_OBJECT_ID_HEADER = "Absolute Number"


def generate_rollback_excel(
    session_id: str,
    conn: sqlite3.Connection,
    output_path: Path | str,
) -> Path:
    """Build a rollback Excel from the ``rollback_snapshots`` table.

    Each object's attributes are pivoted into a single row.  The first column
    is always ``Absolute Number``; remaining columns are discovered from the
    snapshot data in insertion order.

    Returns the resolved path to the saved file.
    """
    snapshots = conn.execute(
        "SELECT object_id, attribute, original_value FROM rollback_snapshots"
        " WHERE session_id = ? ORDER BY object_id, attribute",
        (session_id,),
    ).fetchall()

    objects: dict[int, dict[str, str | None]] = defaultdict(dict)
    attr_order: list[str] = []
    seen_attrs: set[str] = set()

    for row in snapshots:
        oid: int = row[0]
        attr: str = row[1]
        val: str | None = row[2]
        objects[oid][attr] = val
        if attr not in seen_attrs:
            seen_attrs.add(attr)
            attr_order.append(attr)

    wb = create_workbook()
    ws = wb.create_sheet(title="Rollback")

    headers = [_OBJECT_ID_HEADER] + attr_order
    ws.append(headers)

    for oid in sorted(objects):
        row_vals = [oid] + [objects[oid].get(attr) for attr in attr_order]
        ws.append(row_vals)

    return save_workbook(wb, output_path)
