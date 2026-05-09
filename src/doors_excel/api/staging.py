"""Excel worksheet → staging_excel loader (shared by validate and import pipelines)."""
from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from doors_excel.core.transformation.hashing import hash_markdown
from doors_excel.infrastructure.database.repositories import StagingExcelRepository

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

    from doors_excel.core.validation.models import ModuleConfig


def load_excel_to_staging(
    ws: "Worksheet",
    conn: sqlite3.Connection,
    session_id: str,
    module_config: "ModuleConfig",
) -> None:
    """Read all rows from *ws* and insert into ``staging_excel``."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return

    headers = [str(cell) if cell is not None else "" for cell in rows[0]]
    oid_col = module_config.object_id_column

    text_cols = {
        m.column
        for m in module_config.column_mappings
        if m.attribute_type == "Text"
    }

    staging: list[dict] = []
    for row_idx, row in enumerate(rows[1:], start=2):
        object_id: int | None = None
        if oid_col in headers:
            raw_oid = row[headers.index(oid_col)] if headers.index(oid_col) < len(row) else None
            try:
                object_id = int(raw_oid) if raw_oid is not None and str(raw_oid).strip() else None
            except (ValueError, TypeError):
                object_id = None

        for col_idx, header in enumerate(headers):
            if not header:
                continue
            value = row[col_idx] if col_idx < len(row) else None
            str_value = str(value) if value is not None else None
            md_hash = (
                hash_markdown(str_value)
                if header in text_cols and str_value is not None
                else None
            )
            staging.append({
                "session_id": session_id,
                "row_number": row_idx,
                "object_id": object_id,
                "attribute": header,
                "value": str_value,
                "md_hash": md_hash,
            })

    StagingExcelRepository(conn).insert_many(staging)
