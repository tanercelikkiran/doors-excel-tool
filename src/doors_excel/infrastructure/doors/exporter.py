"""DoorsExporter — reads DOORS module objects via DXL and returns staging rows."""
from __future__ import annotations

from doors_excel.common.exceptions import DXLExecutionError
from doors_excel.infrastructure.doors.connection import DoorsConnection
from doors_excel.infrastructure.doors.templates import render_template

_FS = "\x1f"   # field separator (ASCII 31 — Unit Separator)
_RS = "\x1e"   # record separator (ASCII 30 — Record Separator)


class DoorsExporter:
    """Exports object data from a DOORS module as staging-row dicts.

    Each returned dict has:
        object_id, level, parent_id, has_ole, object_type,
        attribute, value, rtf_value, md_hash (always None — computed later).
    """

    def __init__(self, conn: DoorsConnection) -> None:
        self._conn = conn

    def export_module(
        self,
        module_path: str,
        attributes: list[str],
        *,
        baseline: str = "current",
    ) -> list[dict]:
        """Render the export DXL template, run it, and parse the output.

        Returns one dict per (object_id, attribute) pair — zero rows when
        *attributes* is empty.  Raises :class:`DXLExecutionError` if DOORS
        reports an error in the DXL output.
        """
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


def _parse_output(output: str, attributes: list[str]) -> list[dict]:
    """Parse the \\x1e-separated record output from the export DXL script."""
    rows: list[dict] = []
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
            object_id = int(fields[0].strip())
        except ValueError:
            continue
        if object_id == 0:
            continue
        try:
            level = int(fields[1].strip()) if fields[1].strip() else 0
            parent_id_str = fields[2].strip()
            parent_id = int(parent_id_str) if parent_id_str else None
            has_ole = int(fields[3].strip()) if fields[3].strip() else 0
        except ValueError:
            level, parent_id, has_ole = 0, None, 0

        for i, attr in enumerate(attributes):
            base = 4 + i * 2
            value = fields[base].strip() if base < len(fields) else ""
            rtf_val = fields[base + 1].strip() if base + 1 < len(fields) else ""
            rows.append({
                "object_id": object_id,
                "level": level,
                "parent_id": parent_id,
                "has_ole": has_ole,
                "object_type": "OBJECT",
                "attribute": attr,
                "value": value,
                "rtf_value": rtf_val,
                "md_hash": None,
            })
    return rows
