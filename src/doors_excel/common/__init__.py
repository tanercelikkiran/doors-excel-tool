"""Common utilities -- logging, constants, type aliases, and exceptions."""
from __future__ import annotations

from doors_excel.common.constants import (
    DEFAULT_COLUMN_NAMES,
    DEFAULT_OBJECT_TYPES,
    DXL_CHUNK_SIZE,
    DXL_LARGE_CONTENT_CHUNK,
    EXCEL_MAX_CELL_CHARS,
    KEEP_ALIVE_INTERVAL_SECONDS,
    LINK_ENTRY_PATTERN,
    LOG_LEVEL_NOTICE,
    OBJECT_ID_PATTERN,
    SESSION_FILE_NAME,
    SPLIT_COLUMN_SUFFIX,
    SPLIT_COLUMN_WARNING,
)
from doors_excel.common.exceptions import (
    ConfigurationError,
    DXLExecutionError,
    DXLInjectionError,
    DiffError,
    DoorsAuthError,
    DoorsConnectionError,
    DoorsExcelError,
    ExcelReadError,
    ExcelWriteError,
    RollbackError,
    SessionError,
    TransformationError,
    ValidationError,
)
from doors_excel.common.logging import setup_logging
from doors_excel.common.types import (
    ConflictPolicy,
    ObjectId,
    ObjectType,
    Placement,
    RowData,
    StagingRow,
)

__all__ = [
    # constants
    "DEFAULT_COLUMN_NAMES",
    "DEFAULT_OBJECT_TYPES",
    "DXL_CHUNK_SIZE",
    "DXL_LARGE_CONTENT_CHUNK",
    "EXCEL_MAX_CELL_CHARS",
    "KEEP_ALIVE_INTERVAL_SECONDS",
    "LINK_ENTRY_PATTERN",
    "LOG_LEVEL_NOTICE",
    "OBJECT_ID_PATTERN",
    "SESSION_FILE_NAME",
    "SPLIT_COLUMN_SUFFIX",
    "SPLIT_COLUMN_WARNING",
    # exceptions
    "ConfigurationError",
    "DXLExecutionError",
    "DXLInjectionError",
    "DiffError",
    "DoorsAuthError",
    "DoorsConnectionError",
    "DoorsExcelError",
    "ExcelReadError",
    "ExcelWriteError",
    "RollbackError",
    "SessionError",
    "TransformationError",
    "ValidationError",
    # logging
    "setup_logging",
    # types
    "ConflictPolicy",
    "ObjectId",
    "ObjectType",
    "Placement",
    "RowData",
    "StagingRow",
]
