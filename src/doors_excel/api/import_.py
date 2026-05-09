"""Import API — orchestrates Excel→DOORS import pipeline."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from doors_excel.api.sessions import SessionManager
from doors_excel.api.staging import load_excel_to_staging
from doors_excel.common.types import ConflictPolicy
from doors_excel.core.diff.conflict import apply_conflict_policy as _apply_policy
from doors_excel.core.diff.engine import DiffStats, compute_diff
from doors_excel.core.transformation.hashing import hash_markdown as _hash_md
from doors_excel.core.transformation.rtf_to_markdown import rtf_to_markdown
from doors_excel.core.validation.models import ModuleConfig
from doors_excel.infrastructure.database.repositories import (
    StagingBaselineRepository,
    StagingDoorsRepository,
)
from doors_excel.infrastructure.doors.exporter import DoorsExporter
from doors_excel.infrastructure.doors.importer import DoorsImporter
from doors_excel.infrastructure.excel.reader import FormulaPolicy, open_workbook


def stage_import(
    excel_path: Path | str,
    module_config: ModuleConfig,
    *,
    db_path: Path | str,
    doors_conn: object,
    baseline: str = "current",
) -> tuple[str, DiffStats]:
    """Stage an Excel import: load Excel + DOORS data into SQLite, compute diff.

    Returns ``(session_id, DiffStats)``.
    """
    from doors_excel.api.validate import _pick_worksheet

    p = Path(excel_path)
    attributes = [m.attribute for m in module_config.column_mappings]

    mgr = SessionManager(db_path)
    try:
        info = mgr.create(p, module_config.module_path)
        sid = info.session_id
        conn = mgr.conn

        # --- Stage Excel ---
        wb = open_workbook(p, formula_policy=FormulaPolicy.DATA_ONLY)
        ws = _pick_worksheet(wb, module_config)
        load_excel_to_staging(ws, conn, sid, module_config)

        # --- Stage DOORS (current state = staging_doors AND staging_baseline) ---
        exporter = DoorsExporter(doors_conn)
        raw_rows = exporter.export_module(module_config.module_path, attributes, baseline=baseline)

        text_attrs = {
            m.attribute for m in module_config.column_mappings if m.attribute_type == "Text"
        }
        for row in raw_rows:
            if row["attribute"] in text_attrs and row.get("rtf_value"):
                result = rtf_to_markdown(row["rtf_value"])
                row["md_hash"] = _hash_md(result.markdown)

        StagingDoorsRepository(conn).insert_many(
            [{**row, "session_id": sid} for row in raw_rows]
        )
        StagingBaselineRepository(conn).insert_many(
            [
                {
                    "session_id": sid,
                    "object_id": row["object_id"],
                    "attribute": row["attribute"],
                    "value": row["value"],
                    "object_type": row["object_type"],
                    "level": row["level"],
                    "parent_id": row["parent_id"],
                }
                for row in raw_rows
            ]
        )

        stats = compute_diff(conn, sid)
    finally:
        mgr.close()

    return sid, stats


def execute_import(
    session_id: str,
    conn: sqlite3.Connection,
    *,
    doors_conn: object,
    conflict_policy: ConflictPolicy = "excel-wins",
    module_path: str | None = None,
) -> int:
    """Apply UPDATED and CONFLICT diff_results to DOORS. Returns count applied.

    Resolves CONFLICT rows via *conflict_policy* before querying.
    NEW and DELETED changes are skipped (handled by separate helpers).
    """
    _apply_policy(conn, session_id, conflict_policy)

    rows = conn.execute(
        """
        SELECT dr.object_id, dr.attribute,
               CASE WHEN dr.change_type = 'CONFLICT' THEN dr.resolved_value
                    ELSE dr.excel_value
               END AS apply_value,
               s.doors_module
        FROM diff_results dr
        JOIN sessions s ON s.session_id = dr.session_id
        WHERE dr.session_id = ?
          AND (
              (dr.change_type = 'UPDATED')
              OR (dr.change_type = 'CONFLICT' AND dr.resolved_value IS NOT NULL)
          )
        """,
        (session_id,),
    ).fetchall()

    if not rows:
        return 0

    mod_path = module_path or rows[0]["doors_module"]
    updates = [
        {"object_id": r["object_id"], "attribute": r["attribute"], "value": r["apply_value"]}
        for r in rows
    ]

    importer = DoorsImporter(doors_conn)
    importer.apply_updates(mod_path, updates)
    return len(updates)
