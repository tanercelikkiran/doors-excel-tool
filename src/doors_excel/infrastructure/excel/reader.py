"""Excel workbook reader and sheet→module resolver (REQ-FUN-215.1, C-7)."""
from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

import openpyxl

from doors_excel.infrastructure.excel.metadata import get_module_path
from doors_excel.infrastructure.excel.naming import crc32_hex8, make_sheet_name

if TYPE_CHECKING:
    from openpyxl import Workbook
    from openpyxl.worksheet.worksheet import Worksheet


class FormulaPolicy(Enum):
    """Controls how formula cells are read (C-7)."""

    DATA_ONLY = auto()
    """Read cached/computed values (mandatory for import — C-7)."""

    KEEP_FORMULAS = auto()
    """Read raw formula strings (useful for inspection/debugging)."""


def open_workbook(
    path: Path | str,
    *,
    formula_policy: FormulaPolicy = FormulaPolicy.DATA_ONLY,
) -> "Workbook":
    """Open an Excel workbook at *path* and return the openpyxl Workbook.

    By default ``data_only=True`` is used (C-7 requirement) so formula cells
    return their cached values rather than raw formula strings.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    data_only = formula_policy is FormulaPolicy.DATA_ONLY
    return openpyxl.load_workbook(path, data_only=data_only)


def resolve_sheet_module(
    wb: "Workbook",
    ws: "Worksheet",
    *,
    workbook_mapping: dict[str, str] | None = None,
    known_paths: list[str] | None = None,
    literal_modules: dict[str, str] | None = None,
) -> str | None:
    """Resolve the DOORS module path/URL for worksheet *ws* using a 4-tier strategy.

    Priority (REQ-FUN-215.1):
    1. Worksheet metadata — embedded ``_DOORS_Module_Path`` custom property.
    2. Workbook mapping — explicit ``{sheet_title: module_path}`` from config.
    3. CRC32 match — sheet name matches ``make_sheet_name(module_name, path)``
       for any path in *known_paths*.
    4. Literal name — case-insensitive match of ``ws.title`` against keys of
       *literal_modules* (``{module_name_lower: module_path}``).

    Returns ``None`` if no tier matches.
    """
    # Tier 1 — embedded metadata
    path = get_module_path(wb, ws)
    if path is not None:
        return path

    # Tier 2 — explicit workbook mapping
    if workbook_mapping:
        mapped = workbook_mapping.get(ws.title)
        if mapped is not None:
            return mapped

    # Tier 3 — CRC32 convention match
    if known_paths:
        for candidate_path in known_paths:
            # Derive what the sheet name would be for this path
            # The module name is the last segment of the path
            module_name = candidate_path.rstrip("/").rsplit("/", 1)[-1]
            expected = make_sheet_name(module_name, candidate_path)
            if ws.title == expected:
                return candidate_path

    # Tier 4 — case-insensitive literal name match
    if literal_modules:
        lower_title = ws.title.lower()
        for key, module_path in literal_modules.items():
            if key.lower() == lower_title:
                return module_path

    return None
