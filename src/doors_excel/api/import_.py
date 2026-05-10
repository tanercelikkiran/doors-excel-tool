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
from doors_excel.core.transformation.markdown_to_rtf import markdown_to_rtf
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
    module_config: "ModuleConfig | None" = None,
) -> int:
    """Apply UPDATED and CONFLICT diff_results to DOORS. Returns count applied.

    Text-type attributes are converted from GFM Markdown to RTF before writing.
    If the md_hash is unchanged (REQ-FUN-105.4) and DOORS value matches baseline,
    the original RTF is restored from rollback_snapshots to avoid formatting loss.
    """
    _apply_policy(conn, session_id, conflict_policy)

    rows = conn.execute(
        """
        SELECT dr.object_id, dr.attribute,
               CASE WHEN dr.change_type = 'CONFLICT' THEN dr.resolved_value
                    ELSE dr.excel_value
               END AS apply_value,
               s.doors_module,
               se.md_hash  AS excel_md_hash,
               sd.md_hash  AS doors_md_hash,
               dr.doors_value,
               dr.baseline_value,
               rs.original_rtf
        FROM diff_results dr
        JOIN sessions s ON s.session_id = dr.session_id
        LEFT JOIN (
            SELECT session_id, object_id, attribute, md_hash
            FROM staging_excel
            WHERE session_id = :sid
            GROUP BY session_id, object_id, attribute
        ) se ON se.object_id = dr.object_id AND se.attribute = dr.attribute
        LEFT JOIN staging_doors sd
            ON sd.session_id = dr.session_id
           AND sd.object_id  = dr.object_id
           AND sd.attribute  = dr.attribute
        LEFT JOIN rollback_snapshots rs
            ON rs.session_id = dr.session_id
           AND rs.object_id  = dr.object_id
           AND rs.attribute  = dr.attribute
        WHERE dr.session_id = :sid
          AND (
              (dr.change_type = 'UPDATED')
              OR (dr.change_type = 'CONFLICT' AND dr.resolved_value IS NOT NULL)
          )
        """,
        {"sid": session_id},
    ).fetchall()

    if not rows:
        return 0

    text_attrs: set[str] = set()
    if module_config is not None:
        text_attrs = {m.attribute for m in module_config.column_mappings if m.attribute_type == "Text"}

    mod_path = module_path or rows[0]["doors_module"]
    updates = []
    for r in rows:
        value = r["apply_value"] or ""
        if r["attribute"] in text_attrs:
            excel_hash = r["excel_md_hash"]
            doors_hash = r["doors_md_hash"]
            doors_val = r["doors_value"]
            base_val = r["baseline_value"]
            if (excel_hash is not None
                    and doors_hash is not None
                    and excel_hash == doors_hash
                    and doors_val == base_val
                    and r["original_rtf"] is not None):
                value = r["original_rtf"]
            else:
                value = markdown_to_rtf(value)
        updates.append({
            "object_id": r["object_id"],
            "attribute": r["attribute"],
            "value": value,
        })

    importer = DoorsImporter(doors_conn)
    importer.apply_updates(mod_path, updates)
    return len(updates)
