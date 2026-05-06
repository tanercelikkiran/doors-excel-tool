"""Sheet-naming helpers for Excel workbooks (REQ-FUN-113.1).

Convention:  Sanitize(ModuleName)[:22] + "_" + CRC32(FullModulePath)
Total length: 22 + 1 + 8 = 31 characters — exactly at the Excel limit.
"""
from __future__ import annotations

import re
import zlib

# Excel worksheet name hard limit
MAX_SHEET_NAME_LEN: int = 31
_NAME_PREFIX_MAX: int = 22
_FORBIDDEN: re.Pattern[str] = re.compile(r'[\\/?*\[\]:]')


def sanitize_module_name(name: str) -> str:
    """Trim whitespace, then replace Excel-forbidden characters with ``_``.

    Order is significant per REQ-FUN-113.1: trim *first*, replace *second*.
    """
    trimmed = name.strip()
    return _FORBIDDEN.sub("_", trimmed)


def crc32_hex8(path: str) -> str:
    """Return the unsigned CRC32 of *path* as an 8-character zero-padded lowercase hex string."""
    unsigned = zlib.crc32(path.encode()) & 0xFFFFFFFF
    return format(unsigned, "08x")


def make_sheet_name(module_name: str, module_path: str) -> str:
    """Build a unique, Excel-safe worksheet name from *module_name* and *module_path*.

    Result: ``Sanitize(module_name)[:22] + "_" + crc32_hex8(module_path)``
    Total length is at most 31 characters (Excel limit).
    """
    prefix = sanitize_module_name(module_name)[:_NAME_PREFIX_MAX]
    suffix = crc32_hex8(module_path)
    return f"{prefix}_{suffix}"
