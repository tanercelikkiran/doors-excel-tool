"""Export API — orchestrates the full DOORS→Excel export pipeline."""
from __future__ import annotations

from pathlib import Path

from doors_excel.core.transformation.hashing import hash_markdown
from doors_excel.core.transformation.rtf_to_markdown import rtf_to_markdown
from doors_excel.core.validation.models import ModuleConfig
from doors_excel.infrastructure.doors.exporter import DoorsExporter
from doors_excel.infrastructure.excel.writer import add_module_sheet, create_workbook, save_workbook


def export_module(
    module_path: str,
    module_config: ModuleConfig,
    output_path: Path | str,
    *,
    doors_conn: object,
    baseline: str = "current",
) -> Path:
    """Export *module_path* from DOORS to an Excel file at *output_path*.

    1. Fetches module objects from DOORS via DoorsExporter.
    2. Converts RTF → GFM Markdown for Text-type attributes.
    3. Pivots flat (object_id, attribute, value) rows into one row per object.
    4. Writes headers + data rows; embeds the module path as workbook metadata.

    Returns the resolved path to the saved file.
    """
    output = Path(output_path)
    attributes = [m.attribute for m in module_config.column_mappings]
    text_attrs = {m.attribute for m in module_config.column_mappings if m.attribute_type == "Text"}

    exporter = DoorsExporter(doors_conn)
    raw_rows = exporter.export_module(module_path, attributes, baseline=baseline)

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

    module_name = module_path.rstrip("/").rsplit("/", 1)[-1]
    wb = create_workbook()
    ws = add_module_sheet(wb, module_name, module_path)

    headers = (
        [module_config.object_id_column, module_config.level_column, module_config.parent_id_column]
        + [m.column for m in module_config.column_mappings]
    )
    ws.append(headers)

    for oid in sorted(objects):
        ws.append([objects[oid].get(h) for h in headers])

    return save_workbook(wb, output)
