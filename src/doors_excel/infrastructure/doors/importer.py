"""DoorsImporter — applies Excel diff results back to DOORS via DXL."""
from __future__ import annotations

from doors_excel.infrastructure.doors.chunker import chunk_dxl
from doors_excel.infrastructure.doors.connection import DoorsConnection
from doors_excel.infrastructure.doors.templates import render_template


class DoorsImporter:
    """Sends attribute updates to DOORS by rendering and executing DXL."""

    def __init__(self, conn: DoorsConnection) -> None:
        self._conn = conn

    def apply_updates(self, module_path: str, updates: list[dict]) -> None:
        """Render the update template for *updates* and execute via DOORS COM.

        *updates* is a list of ``{object_id, attribute, value}`` dicts.
        No-op when *updates* is empty.
        """
        if not updates:
            return
        script = render_template(
            "update_module.dxl.j2",
            module_path=module_path,
            updates=updates,
        )
        for chunk in chunk_dxl(script):
            self._conn.run_dxl(chunk)

    def create_objects(self, module_path: str, objects: list[dict]) -> None:
        """Create new objects in *module_path*.

        Each dict in *objects* must have:
            ``parent_id``: int | None  — DOORS Absolute Number of parent (None = root)
            ``attributes``: dict[str, str]  — attribute name → value string
        """
        if not objects:
            return
        script = render_template("create_objects.dxl.j2", module_path=module_path, objects=objects)
        for chunk in chunk_dxl(script):
            self._conn.run_dxl(chunk)

    def delete_objects(self, module_path: str, object_ids: list[int]) -> None:
        """Permanently delete *object_ids* from *module_path* in DOORS.

        Purge is irreversible — callers must obtain user confirmation first.
        """
        if not object_ids:
            return
        script = render_template("delete_objects.dxl.j2", module_path=module_path, object_ids=object_ids)
        for chunk in chunk_dxl(script):
            self._conn.run_dxl(chunk)

    def move_objects(self, module_path: str, moves: list[dict]) -> None:
        """Relocate objects within *module_path*.

        Each dict in *moves* must have:
            ``object_id``: int — Absolute Number of the object to move
            ``new_parent_id``: int | None — new parent (None = module root)
            ``placement``: str — "below" (first child) or "after" (sibling)
        """
        if not moves:
            return
        script = render_template("move_objects.dxl.j2", module_path=module_path, moves=moves)
        for chunk in chunk_dxl(script):
            self._conn.run_dxl(chunk)
