"""Smoke tests that infrastructure/excel/__init__.py re-exports the public API."""
from __future__ import annotations


class TestExcelPackageReExports:
    def test_naming_symbols(self) -> None:
        from doors_excel.infrastructure.excel import (
            MAX_SHEET_NAME_LEN,
            crc32_hex8,
            make_sheet_name,
            sanitize_module_name,
        )
        assert callable(sanitize_module_name)
        assert callable(crc32_hex8)
        assert callable(make_sheet_name)
        assert isinstance(MAX_SHEET_NAME_LEN, int)

    def test_metadata_symbols(self) -> None:
        from doors_excel.infrastructure.excel import (
            DOORS_MODULE_PATH_DEFINED_NAME,
            compute_integrity_hash,
            get_custom_property,
            get_module_path,
            set_custom_property,
            set_module_path,
            verify_integrity_hash,
        )
        assert isinstance(DOORS_MODULE_PATH_DEFINED_NAME, str)
        for fn in (
            compute_integrity_hash, get_custom_property, get_module_path,
            set_custom_property, set_module_path, verify_integrity_hash,
        ):
            assert callable(fn)

    def test_reader_symbols(self) -> None:
        from doors_excel.infrastructure.excel import (
            FormulaPolicy,
            open_workbook,
            resolve_sheet_module,
        )
        assert callable(open_workbook)
        assert callable(resolve_sheet_module)
        assert isinstance(FormulaPolicy, type) or hasattr(FormulaPolicy, "__mro__")

    def test_writer_symbols(self) -> None:
        from doors_excel.infrastructure.excel import (
            add_module_sheet,
            create_workbook,
            save_workbook,
        )
        for fn in (create_workbook, add_module_sheet, save_workbook):
            assert callable(fn)

    def test_protection_symbols(self) -> None:
        from doors_excel.infrastructure.excel import (
            apply_sheet_protection,
            lock_cell,
            lock_range,
            unlock_cell,
        )
        for fn in (lock_cell, unlock_cell, lock_range, apply_sheet_protection):
            assert callable(fn)

    def test_dunder_all_complete(self) -> None:
        import doors_excel.infrastructure.excel as m
        if not hasattr(m, "__all__"):
            return
        expected = [
            "MAX_SHEET_NAME_LEN", "sanitize_module_name", "crc32_hex8", "make_sheet_name",
            "DOORS_MODULE_PATH_DEFINED_NAME",
            "set_module_path", "get_module_path",
            "set_custom_property", "get_custom_property",
            "compute_integrity_hash", "verify_integrity_hash",
            "FormulaPolicy", "open_workbook", "resolve_sheet_module",
            "create_workbook", "add_module_sheet", "save_workbook",
            "lock_cell", "unlock_cell", "lock_range", "apply_sheet_protection",
        ]
        for name in expected:
            assert name in m.__all__, f"{name!r} missing from __all__"
