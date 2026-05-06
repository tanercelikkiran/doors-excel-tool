"""Shared type aliases and Literal types used across the doors-excel-tool."""
from __future__ import annotations

from typing import Any, Literal

# Integer primary key from DOORS
ObjectId = int

# How to resolve conflicts during a 3-way merge
ConflictPolicy = Literal["excel-wins", "doors-wins", "content-based"]

# DOORS object structural roles
ObjectType = Literal[
    "OBJECT",
    "TABLE_START",
    "TABLE_ROW",
    "TABLE_CELL",
    "TABLE_END",
    "NEW_TABLE",
]

# Where to insert an object relative to its anchor
Placement = Literal["after", "as_child"]

# One row from the Excel sheet: column header -> cell value
RowData = dict[str, Any]

# One row in the staging SQLite table
StagingRow = dict[str, Any]
