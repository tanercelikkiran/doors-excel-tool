"""Custom exception hierarchy for the doors-excel-tool.

All application exceptions inherit from ``DoorsExcelError`` so callers can
catch the entire hierarchy with a single ``except DoorsExcelError`` clause.
"""
from __future__ import annotations


class DoorsExcelError(Exception):
    """Base exception for all doors-excel-tool errors."""


class DoorsConnectionError(DoorsExcelError):
    """Cannot establish or maintain the IBM DOORS COM connection."""


class DoorsAuthError(DoorsExcelError):
    """DOORS session is invalid, expired, or lacks required permissions."""


class DXLExecutionError(DoorsExcelError):
    """A DXL script returned an error or produced unexpected output.

    Attributes
    ----------
    dxl_output:
        Raw output string returned by DOORS after executing the script.
    """

    def __init__(self, message: str, *, dxl_output: str = "") -> None:
        super().__init__(message)
        self.dxl_output = dxl_output

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({str(self)!r},"
            f" dxl_output={self.dxl_output!r})"
        )


class DXLInjectionError(DoorsExcelError):
    """Unsanitized data would produce a DXL injection — blocked before execution."""


class ExcelReadError(DoorsExcelError):
    """Reading from an Excel workbook failed."""


class ExcelWriteError(DoorsExcelError):
    """Writing to an Excel workbook failed."""


class TransformationError(DoorsExcelError):
    """RTF↔Markdown conversion or table structural mapping failed unrecoverably."""


class ValidationError(DoorsExcelError):
    """A data validation rule was violated during the import pipeline.

    Attributes
    ----------
    row:
        1-based Excel row number where the violation was found (0 = unknown).
    attribute:
        DOORS attribute name (column header) associated with the violation.
    """

    def __init__(self, message: str, *, row: int = 0, attribute: str = "") -> None:
        super().__init__(message)
        self.row = row
        self.attribute = attribute


class DiffError(DoorsExcelError):
    """SQL-based 3-way merge or change-detection engine hit an unrecoverable error."""


class RollbackError(DoorsExcelError):
    """Rollback operation cannot complete (missing snapshot, expired session, etc.)."""


class ConfigurationError(DoorsExcelError):
    """Configuration file is missing, malformed, or fails JSON-schema validation."""


class SessionError(DoorsExcelError):
    """Session-integrity violation (e.g. hash mismatch in .session.json)."""
