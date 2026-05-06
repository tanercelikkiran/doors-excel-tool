"""openpyxl / pandas Excel I/O with metadata preservation and sheet protection."""
from __future__ import annotations

from doors_excel.infrastructure.excel.metadata import (
    DOORS_MODULE_PATH_DEFINED_NAME,
    compute_integrity_hash,
    get_custom_property,
    get_module_path,
    set_custom_property,
    set_module_path,
    verify_integrity_hash,
)
from doors_excel.infrastructure.excel.naming import (
    MAX_SHEET_NAME_LEN,
    crc32_hex8,
    make_sheet_name,
    sanitize_module_name,
)
from doors_excel.infrastructure.excel.protection import (
    apply_sheet_protection,
    lock_cell,
    lock_range,
    unlock_cell,
)
from doors_excel.infrastructure.excel.reader import (
    FormulaPolicy,
    open_workbook,
    resolve_sheet_module,
)
from doors_excel.infrastructure.excel.writer import (
    add_module_sheet,
    create_workbook,
    save_workbook,
)

__all__ = [
    # naming
    "MAX_SHEET_NAME_LEN",
    "sanitize_module_name",
    "crc32_hex8",
    "make_sheet_name",
    # metadata
    "DOORS_MODULE_PATH_DEFINED_NAME",
    "set_module_path",
    "get_module_path",
    "set_custom_property",
    "get_custom_property",
    "compute_integrity_hash",
    "verify_integrity_hash",
    # reader
    "FormulaPolicy",
    "open_workbook",
    "resolve_sheet_module",
    # writer
    "create_workbook",
    "add_module_sheet",
    "save_workbook",
    # protection
    "lock_cell",
    "unlock_cell",
    "lock_range",
    "apply_sheet_protection",
]
