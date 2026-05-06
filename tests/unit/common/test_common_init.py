"""Tests that common/__init__.py correctly re-exports its submodule symbols."""
from __future__ import annotations

from typing import get_args


class TestCommonReExports:
    def test_exceptions_accessible_from_common(self) -> None:
        from doors_excel.common import DoorsExcelError, ValidationError, DXLExecutionError
        assert issubclass(ValidationError, DoorsExcelError)
        assert issubclass(DXLExecutionError, DoorsExcelError)

    def test_constants_accessible_from_common(self) -> None:
        from doors_excel.common import DXL_CHUNK_SIZE, LOG_LEVEL_NOTICE, EXCEL_MAX_CELL_CHARS
        assert DXL_CHUNK_SIZE == 48 * 1024
        assert LOG_LEVEL_NOTICE == 22
        assert EXCEL_MAX_CELL_CHARS == 32_767

    def test_types_accessible_from_common(self) -> None:
        from doors_excel.common import ConflictPolicy, ObjectType, Placement
        assert "excel-wins" in get_args(ConflictPolicy)
        assert "OBJECT" in get_args(ObjectType)
        assert "after" in get_args(Placement)

    def test_setup_logging_accessible_from_common(self) -> None:
        from doors_excel.common import setup_logging
        assert callable(setup_logging)

    def test_dunder_all_contains_key_symbols(self) -> None:
        import doors_excel.common as m
        if hasattr(m, "__all__"):
            for name in ["DoorsExcelError", "DXL_CHUNK_SIZE", "setup_logging",
                         "ConflictPolicy", "ObjectType", "Placement"]:
                assert name in m.__all__, f"{name!r} missing from __all__"
