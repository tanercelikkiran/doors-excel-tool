"""Export API — orchestrates the full DOORS→Excel export pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from doors_excel.core.validation.models import ModuleConfig
from doors_excel.infrastructure.doors.exporter import DoorsExporter
from doors_excel.infrastructure.excel.writer import add_module_sheet, create_workbook, save_workbook

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

    from doors_excel.api.sessions import SessionManager


def _apply_worksheet_protection(
    ws: Worksheet,
    headers: list[str],
    module_config: ModuleConfig,
    *,
    password: str | None = None,
) -> None:
    """Lock all cells then unlock data cells for editable columns."""
    from openpyxl.styles import Protection

    from doors_excel.infrastructure.excel.protection import apply_sheet_protection

    editable_cols: set[int] = set()
    for idx, header in enumerate(headers, start=1):
        col_cfg = next(
            (m for m in module_config.column_mappings if m.column == header),
            None,
        )
        if col_cfg is not None and not col_cfg.read_only:
            editable_cols.add(idx)

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if cell.column in editable_cols:
                cell.protection = Protection(locked=False)
            else:
                cell.protection = Protection(locked=True)

    apply_sheet_protection(ws, password=password, enabled=True)


def _expand_long_values(
    objects: dict[int, dict],
    module_config: ModuleConfig,
    headers: list[str],
) -> list[str]:
    """Split Text-column values exceeding EXCEL_CELL_LIMIT; returns expanded headers."""
    from loguru import logger

    from doors_excel.core.transformation.smart_split import (
        EXCEL_CELL_LIMIT,
        smart_split,
        split_column_headers,
    )

    text_cols = [m.column for m in module_config.column_mappings if m.attribute_type == "Text"]
    expanded = list(headers)

    for col in text_cols:
        if col not in expanded:
            continue
        max_chunks = max(
            (len(smart_split(str(obj.get(col) or ""))) for obj in objects.values()),
            default=1,
        )
        if max_chunks <= 1:
            continue

        logger.warning(
            "Column '{}' exceeds {} chars; splitting into {} columns.",
            col, EXCEL_CELL_LIMIT, max_chunks,
        )
        all_headers = split_column_headers(col, max_chunks)
        overflow_headers = all_headers[1:]

        for obj in objects.values():
            val = str(obj.get(col) or "")
            chunks = smart_split(val)
            while len(chunks) < max_chunks:
                chunks.append("")
            obj[col] = chunks[0]
            for overflow_col, chunk in zip(overflow_headers, chunks[1:], strict=True):
                obj[overflow_col] = chunk

        # Insert overflow headers immediately after base col, skip if collision with real column
        col_idx = expanded.index(col)
        inserted = 0
        for overflow_col in overflow_headers:
            if overflow_col not in expanded:
                expanded.insert(col_idx + 1 + inserted, overflow_col)
                inserted += 1

    return expanded


def _build_objects_from_rows(
    raw_rows: list[dict],
    module_config: ModuleConfig,
) -> dict[int, dict]:
    """Build the objects dict from flat raw_rows (applies RTF→Markdown for Text attrs)."""
    from doors_excel.core.transformation.hashing import hash_markdown
    from doors_excel.core.transformation.rtf_to_markdown import rtf_to_markdown

    text_attrs = {m.attribute for m in module_config.column_mappings if m.attribute_type == "Text"}
    for row in raw_rows:
        if row["attribute"] in text_attrs and row["rtf_value"]:
            result = rtf_to_markdown(row["rtf_value"])
            row["value"] = result.markdown
            row["md_hash"] = hash_markdown(result.markdown)

    objects: dict[int, dict] = {}
    attr_to_col = {m.attribute: m.column for m in module_config.column_mappings}
    for row in raw_rows:
        oid = row["object_id"]
        if oid not in objects:
            objects[oid] = {
                module_config.object_id_column: oid,
                module_config.level_column: row["level"],
                module_config.parent_id_column: row["parent_id"],
            }
        col = attr_to_col.get(row["attribute"])
        if col:
            objects[oid][col] = row["value"]
    return objects


def _write_module_sheet(
    wb: object,
    module_name: str,
    module_path: str,
    objects: dict[int, dict],
    module_config: ModuleConfig,
    *,
    sheet_protection: bool = False,
    sheet_protection_password: str | None = None,
    include_source_baseline: bool = False,
    baseline: str = "current",
) -> Worksheet:
    """Add a sheet for one module to *wb*, write headers and data rows, apply protection."""
    ws = add_module_sheet(wb, module_name, module_path)
    headers = (
        [module_config.object_id_column, module_config.level_column, module_config.parent_id_column]
        + [m.column for m in module_config.column_mappings]
    )
    if include_source_baseline:
        headers = headers + ["Source Baseline"]
        for obj in objects.values():
            obj["Source Baseline"] = baseline
    headers = _expand_long_values(objects, module_config, headers)
    ws.append(headers)
    for oid in sorted(objects):
        ws.append([objects[oid].get(h) for h in headers])
    if sheet_protection:
        _apply_worksheet_protection(ws, headers, module_config, password=sheet_protection_password)
    return ws


def export_module(
    module_path: str,
    module_config: ModuleConfig,
    output_path: Path | str,
    *,
    doors_conn: object,
    baseline: str = "current",
    session_manager: SessionManager | None = None,
    sheet_protection: bool = False,
    sheet_protection_password: str | None = None,
    include_source_baseline: bool = False,
) -> Path:
    """Export *module_path* from DOORS to an Excel file at *output_path*.

    When *session_manager* is provided a session is created after saving the
    workbook and all three staging tables are populated so the 3-way diff
    engine can run later during import.
    """
    output = Path(output_path)
    attributes = [m.attribute for m in module_config.column_mappings]

    exporter = DoorsExporter(doors_conn)
    raw_rows = exporter.export_module(module_path, attributes, baseline=baseline)

    objects = _build_objects_from_rows(raw_rows, module_config)
    module_name = module_path.rstrip("/").rsplit("/", 1)[-1]
    wb = create_workbook()
    _write_module_sheet(
        wb, module_name, module_path, objects, module_config,
        sheet_protection=sheet_protection,
        sheet_protection_password=sheet_protection_password,
        include_source_baseline=include_source_baseline,
        baseline=baseline,
    )

    saved_path = save_workbook(wb, output)

    if session_manager is not None:
        _populate_session(session_manager, saved_path, module_path, raw_rows)

    return saved_path


def bulk_export(
    module_configs: list[ModuleConfig],
    output_path: Path | str,
    *,
    doors_conn: object,
    baseline: str = "current",
    session_manager: SessionManager | None = None,
    sheet_protection: bool = False,
    sheet_protection_password: str | None = None,
    include_source_baseline: bool = False,
) -> Path:
    """Export multiple DOORS modules into a single multi-sheet workbook.

    Each module becomes one sheet. The workbook is saved once after all
    sheets are written.

    Note: *session_manager* is accepted for API compatibility but is never
    used. The session sidecar mechanism is designed for single-module sessions
    and does not support multi-module bulk exports yet.
    """
    output = Path(output_path)
    exporter = DoorsExporter(doors_conn)
    wb = create_workbook()

    for module_config in module_configs:
        attributes = [m.attribute for m in module_config.column_mappings]
        raw_rows = exporter.export_module(module_config.module_path, attributes, baseline=baseline)
        objects = _build_objects_from_rows(raw_rows, module_config)
        module_name = module_config.module_path.rstrip("/").rsplit("/", 1)[-1]
        _write_module_sheet(
            wb, module_name, module_config.module_path, objects, module_config,
            sheet_protection=sheet_protection,
            sheet_protection_password=sheet_protection_password,
            include_source_baseline=include_source_baseline,
            baseline=baseline,
        )

    return save_workbook(wb, output)


def _populate_session(
    mgr: SessionManager,
    excel_path: Path,
    module_path: str,
    raw_rows: list[dict],
) -> None:
    """Create a session and populate staging_doors, staging_baseline, rollback_snapshots."""
    from doors_excel.infrastructure.database.repositories import (
        RollbackSnapshotRepository,
        StagingBaselineRepository,
        StagingDoorsRepository,
    )

    info = mgr.create(excel_path, module_path)
    sid = info.session_id
    conn = mgr.conn

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
    RollbackSnapshotRepository(conn).insert_many(
        [
            {
                "session_id": sid,
                "object_id": row["object_id"],
                "attribute": row["attribute"],
                "original_value": row["value"],
                "original_rtf": row["rtf_value"],
            }
            for row in raw_rows
        ]
    )
