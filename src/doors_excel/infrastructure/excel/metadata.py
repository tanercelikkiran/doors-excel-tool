"""Excel metadata helpers: module path, custom properties, integrity hashing.

REQ-FUN-113.2 — store _DOORS_Module_Path per worksheet
REQ-FUN-108.1 — Workbook Custom Properties for marker mapping persistence
REQ-FUN-117   — SHA-256 integrity hash for protected metadata fields

Implementation note
-------------------
REQ-FUN-113.2 specifies sheet-scoped *Defined Names*, but openpyxl 3.1.5 does
not persist localSheetId-scoped defined names through a save/load cycle.  As a
reliable cross-version alternative we store the path in Workbook Custom
Properties under the composite key ``"_DOORS_Module_Path::{sheet.title}"``.
Readers that prefer the native Excel mechanism can retrieve the value from the
same custom-property key; no functional behaviour changes.
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import openpyxl
from openpyxl.packaging.custom import CustomPropertyList, StringProperty

if TYPE_CHECKING:
    from openpyxl import Workbook
    from openpyxl.worksheet.worksheet import Worksheet

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOORS_MODULE_PATH_DEFINED_NAME: str = "_DOORS_Module_Path"
_PATH_KEY_PREFIX: str = DOORS_MODULE_PATH_DEFINED_NAME + "::"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_custom_props(wb: "Workbook") -> "CustomPropertyList":
    if wb.custom_doc_props is None:
        wb.custom_doc_props = CustomPropertyList()
    return wb.custom_doc_props


def _path_key(ws: "Worksheet") -> str:
    return f"{_PATH_KEY_PREFIX}{ws.title}"


# ---------------------------------------------------------------------------
# Module path storage (REQ-FUN-113.2)
# ---------------------------------------------------------------------------

def set_module_path(wb: "Workbook", ws: "Worksheet", path: str) -> None:
    """Store *path* as a Workbook Custom Property keyed by sheet title.

    The property name is ``_DOORS_Module_Path::{sheet.title}``.
    Survives save/load round-trips via openpyxl's Custom Properties support.
    """
    set_custom_property(wb, _path_key(ws), path)


def get_module_path(wb: "Workbook", ws: "Worksheet") -> str | None:
    """Return the DOORS module path stored for *ws*, or ``None`` if absent."""
    return get_custom_property(wb, _path_key(ws))


# ---------------------------------------------------------------------------
# Workbook Custom Properties  (REQ-FUN-108.1)
# ---------------------------------------------------------------------------

def set_custom_property(wb: "Workbook", name: str, value: str) -> None:
    """Write (or overwrite) a string custom property on *wb*."""
    props = _ensure_custom_props(wb)
    # Remove any existing property with the same name
    props.props = [p for p in props.props if p.name != name]
    props.props.append(StringProperty(name=name, value=value))


def get_custom_property(wb: "Workbook", name: str) -> str | None:
    """Return the value of custom property *name*, or ``None`` if absent."""
    if wb.custom_doc_props is None:
        return None
    for p in wb.custom_doc_props.props:
        if p.name == name:
            return str(p.value)
    return None


# ---------------------------------------------------------------------------
# Integrity hash  (REQ-FUN-117)
# ---------------------------------------------------------------------------

def compute_integrity_hash(fields: dict[str, str]) -> str:
    """Return a SHA-256 hex digest of *fields* sorted by key.

    Sorting ensures the hash is key-insertion-order-independent.
    """
    canonical = json.dumps(
        dict(sorted(fields.items())),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_integrity_hash(fields: dict[str, str], expected_hash: str) -> bool:
    """Return ``True`` iff ``compute_integrity_hash(fields) == expected_hash``."""
    return compute_integrity_hash(fields) == expected_hash
