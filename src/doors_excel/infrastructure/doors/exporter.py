"""DoorsExporter — reads DOORS module objects via DXL and returns staging rows."""
from __future__ import annotations

from doors_excel.common.exceptions import DXLExecutionError
from doors_excel.infrastructure.doors.connection import DoorsConnection
from doors_excel.infrastructure.doors.templates import render_template

_FS = "\x1f"
_RS = "\x1e"

_TABLE_SUB_TYPES = frozenset({"TABLE_ROW", "TABLE_CELL"})


class DoorsExporter:
    """Exports object data from a DOORS module as staging-row dicts."""

    def __init__(self, conn: DoorsConnection) -> None:
        self._conn = conn

    def export_module(
        self,
        module_path: str,
        attributes: list[str],
        *,
        baseline: str = "current",
    ) -> list[dict]:
        if not attributes:
            return []
        script = render_template(
            "export_module.dxl.j2",
            module_path=module_path,
            attributes=attributes,
            baseline=baseline,
        )
        output = self._conn.run_dxl(script) or ""
        return _parse_output(output, attributes)


def _int_or_none(s: str) -> int | None:
    """Parse int; return None for empty string or zero."""
    v = s.strip()
    if not v:
        return None
    n = int(v)
    return n if n != 0 else None


def _parse_output(output: str, attributes: list[str]) -> list[dict]:
    rows: list[dict] = []
    synthetic_id = -1

    for record in output.split(_RS):
        record = record.strip()
        if not record:
            continue
        if record.startswith("DOORS_EXPORT_ERROR"):
            raise DXLExecutionError(record, dxl_output=record)
        fields = record.split(_FS)
        if len(fields) < 4:
            continue

        try:
            abs_no = int(fields[0].strip())
        except ValueError:
            continue

        obj_type = fields[4].strip() if len(fields) > 4 else "OBJECT"
        if not obj_type:
            obj_type = "OBJECT"

        if abs_no == 0 and obj_type not in _TABLE_SUB_TYPES:
            continue

        object_id = abs_no if abs_no != 0 else synthetic_id
        if abs_no == 0:
            synthetic_id -= 1

        try:
            level = int(fields[1].strip()) if fields[1].strip() else 0
            parent_id = int(fields[2].strip()) if fields[2].strip() else None
            has_ole = int(fields[3].strip()) if fields[3].strip() else 0
        except ValueError:
            level, parent_id, has_ole = 0, None, 0

        try:
            parent_absno = _int_or_none(fields[5]) if len(fields) > 5 else None
            row_position = _int_or_none(fields[6]) if len(fields) > 6 else None
            col_position = _int_or_none(fields[7]) if len(fields) > 7 else None
        except ValueError:
            parent_absno, row_position, col_position = None, None, None

        for i, attr in enumerate(attributes):
            base = 8 + i * 2
            value = fields[base].strip() if base < len(fields) else ""
            rtf_val = fields[base + 1].strip() if base + 1 < len(fields) else ""
            rows.append({
                "object_id": object_id,
                "level": level,
                "parent_id": parent_id,
                "has_ole": has_ole,
                "object_type": obj_type,
                "attribute": attr,
                "value": value,
                "rtf_value": rtf_val,
                "md_hash": None,
                "parent_absno": parent_absno,
                "row_position": row_position,
                "col_position": col_position,
            })

    return _inject_table_ends(rows, attributes, start_end_id=synthetic_id)


def _inject_table_ends(
    rows: list[dict],
    attributes: list[str],
    *,
    start_end_id: int,
) -> list[dict]:
    if not rows:
        return rows

    groups: dict[int, list[dict]] = {}
    for row in rows:
        oid = row["object_id"]
        if oid not in groups:
            groups[oid] = []
        groups[oid].append(row)

    result: list[dict] = []
    cur_table_id: int | None = None
    end_id = start_end_id

    def _make_table_end(table_absno: int, eid: int) -> list[dict]:
        return [
            {
                "object_id": eid,
                "object_type": "TABLE_END",
                "level": 0,
                "parent_id": None,
                "has_ole": 0,
                "attribute": attr,
                "value": "",
                "rtf_value": "",
                "md_hash": None,
                "parent_absno": table_absno,
                "row_position": None,
                "col_position": None,
            }
            for attr in attributes
        ]

    for oid, obj_rows in groups.items():
        obj_type = obj_rows[0]["object_type"]

        # Inject TABLE_END when leaving a table block:
        # - A non-table object follows table objects, OR
        # - A new TABLE starts while already inside a table block
        if cur_table_id is not None and obj_type not in ("TABLE_ROW", "TABLE_CELL"):
            result.extend(_make_table_end(cur_table_id, end_id))
            end_id -= 1
            cur_table_id = None

        if obj_type == "TABLE":
            cur_table_id = oid

        result.extend(obj_rows)

    if cur_table_id is not None:
        result.extend(_make_table_end(cur_table_id, end_id))

    return result
