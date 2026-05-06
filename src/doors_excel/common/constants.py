"""Application-wide constants for the doors-excel-tool."""
from __future__ import annotations

import re

# DXL chunking thresholds
DXL_CHUNK_SIZE = 48 * 1024
DXL_LARGE_CONTENT_CHUNK = 32 * 1024

# Excel cell character limit (openpyxl raises on longer strings)
EXCEL_MAX_CELL_CHARS = 32_767

# Custom log level between INFO (20) and WARNING (30)
LOG_LEVEL_NOTICE = 22

# COM keep-alive ping interval
KEEP_ALIVE_INTERVAL_SECONDS = 30

# Session persistence
SESSION_FILE_NAME = ".session.json"

# Column splitting
SPLIT_COLUMN_SUFFIX = "_split"
SPLIT_COLUMN_WARNING = "Value truncated — see split column"

DEFAULT_OBJECT_TYPES: dict[str, str] = {
    "object": "OBJECT",
    "table_start": "TABLE_START",
    "table_row": "TABLE_ROW",
    "table_cell": "TABLE_CELL",
    "table_end": "TABLE_END",
    "new_table": "NEW_TABLE",
}

DEFAULT_COLUMN_NAMES: dict[str, str] = {
    "absolute_number": "Absolute Number",
    "object_text": "Object Text",
    "level": "Level",
    "parent_id": "Parent ID",
    "placement": "Placement",
    "object_type": "Object Type",
    "has_ole": "Has OLE",
    "validation_feedback": "Validation Feedback",
}

# Matches a bare integer object ID, e.g. "12345"
OBJECT_ID_PATTERN = re.compile(r"^\d+$")

# Matches any of the link entry formats written by the export DXL:
#   99
#   [42] (Type: "Satisfies", Mod: "My Module")
#   DEL: [42] (Type: "Satisfies", Mod: "My Module")
#   doors://localhost:36677/1234
LINK_ENTRY_PATTERN = re.compile(
    r"^(?:DEL:\s+)?(?:\[\d+\](?:\s+\(.*\))?|\d+|doors://\S+)"
)
