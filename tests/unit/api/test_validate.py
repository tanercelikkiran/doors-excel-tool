"""Tests for api/validate.py — validate_config and validate_excel."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import openpyxl
import pytest

from doors_excel.api.validate import validate_config, validate_excel
from doors_excel.common.exceptions import ConfigurationError
from doors_excel.core.validation.models import ColumnMapping, ModuleConfig

from .conftest import basic_module_config, make_xlsx


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

class TestValidateConfig:
    def _write_valid_config(self, tmp_path: Path) -> Path:
        data = {
            "modules": [
                {
                    "module_path": "/proj/mod",
                    "column_mappings": [
                        {"column": "Object Text", "attribute": "Object Text"}
                    ],
                }
            ]
        }
        p = tmp_path / "config.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_valid_config_returns_project_config(self, tmp_path: Path) -> None:
        from doors_excel.core.validation.models import ProjectConfig
        p = self._write_valid_config(tmp_path)
        result = validate_config(p)
        assert isinstance(result, ProjectConfig)

    def test_invalid_file_raises_config_error(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigurationError):
            validate_config(tmp_path / "missing.json")

    def test_bad_json_raises_config_error(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{bad json", encoding="utf-8")
        with pytest.raises(ConfigurationError):
            validate_config(p)


# ---------------------------------------------------------------------------
# validate_excel — happy path
# ---------------------------------------------------------------------------

class TestValidateExcelHappyPath:
    def test_all_valid_rows_returns_zero_errors(
        self, tmp_path: Path, basic_module_config: ModuleConfig
    ) -> None:
        xlsx = make_xlsx(
            tmp_path,
            headers=["Absolute Number", "Object Text", "Short Name", "Status"],
            rows=[
                [10, "Hello world", "short", "Open"],
                [11, "Another row", "x" * 5, "Closed"],
            ],
        )
        result = validate_excel(xlsx, basic_module_config)
        assert result.blocking_count == 0

    def test_returns_validation_result(
        self, tmp_path: Path, basic_module_config: ModuleConfig
    ) -> None:
        from doors_excel.core.validation.validator import ValidationResult
        xlsx = make_xlsx(
            tmp_path,
            headers=["Absolute Number", "Object Text", "Short Name", "Status"],
            rows=[[10, "ok", "short", "Open"]],
        )
        result = validate_excel(xlsx, basic_module_config)
        assert isinstance(result, ValidationResult)


# ---------------------------------------------------------------------------
# validate_excel — error detection
# ---------------------------------------------------------------------------

class TestValidateExcelErrors:
    def test_missing_column_detected(
        self, tmp_path: Path, basic_module_config: ModuleConfig
    ) -> None:
        # Only provide Object Text — Short Name and Status are missing
        xlsx = make_xlsx(
            tmp_path,
            headers=["Absolute Number", "Object Text"],
            rows=[[10, "hello"]],
        )
        result = validate_excel(xlsx, basic_module_config)
        assert result.blocking_count > 0

    def test_string_too_long_detected(
        self, tmp_path: Path, basic_module_config: ModuleConfig
    ) -> None:
        xlsx = make_xlsx(
            tmp_path,
            headers=["Absolute Number", "Object Text", "Short Name", "Status"],
            rows=[[10, "ok", "x" * 1025, "Open"]],
        )
        result = validate_excel(xlsx, basic_module_config)
        assert result.blocking_count > 0

    def test_invalid_enum_detected(
        self, tmp_path: Path, basic_module_config: ModuleConfig
    ) -> None:
        xlsx = make_xlsx(
            tmp_path,
            headers=["Absolute Number", "Object Text", "Short Name", "Status"],
            rows=[[10, "ok", "short", "InvalidStatus"]],
        )
        result = validate_excel(xlsx, basic_module_config)
        assert result.blocking_count > 0

    def test_new_row_with_placeholder_detected(
        self, tmp_path: Path, basic_module_config: ModuleConfig
    ) -> None:
        # row with no Absolute Number (new object) containing an IMAGE placeholder
        xlsx = make_xlsx(
            tmp_path,
            headers=["Absolute Number", "Object Text", "Short Name", "Status"],
            rows=[[None, "See [IMAGE: 1]", "new", "Open"]],
        )
        result = validate_excel(xlsx, basic_module_config)
        assert result.blocking_count > 0

    def test_empty_workbook_returns_zero_errors(
        self, tmp_path: Path, basic_module_config: ModuleConfig
    ) -> None:
        # Header row only, no data rows → nothing to validate
        xlsx = make_xlsx(
            tmp_path,
            headers=["Absolute Number", "Object Text", "Short Name", "Status"],
            rows=[],
        )
        result = validate_excel(xlsx, basic_module_config)
        assert result.blocking_count == 0


# ---------------------------------------------------------------------------
# validate_excel — connection injection
# ---------------------------------------------------------------------------

class TestValidateExcelConnInjection:
    def test_accepts_external_conn(
        self, tmp_path: Path, basic_module_config: ModuleConfig, mem_conn
    ) -> None:
        xlsx = make_xlsx(
            tmp_path,
            headers=["Absolute Number", "Object Text", "Short Name", "Status"],
            rows=[[10, "ok", "short", "Open"]],
        )
        result = validate_excel(xlsx, basic_module_config, conn=mem_conn)
        assert isinstance(result.blocking_count, int)

    def test_accepts_db_path(
        self, tmp_path: Path, basic_module_config: ModuleConfig
    ) -> None:
        xlsx = make_xlsx(
            tmp_path,
            headers=["Absolute Number", "Object Text", "Short Name", "Status"],
            rows=[[10, "ok", "short", "Open"]],
        )
        result = validate_excel(xlsx, basic_module_config, db_path=tmp_path / "v.db")
        assert isinstance(result.blocking_count, int)
