"""Tests for core/validation/models.py — Pydantic models and load_config."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from doors_excel.common.exceptions import ConfigurationError
from doors_excel.core.validation.models import (
    ColumnMapping,
    ModuleConfig,
    ProjectConfig,
    load_config,
)


class TestColumnMapping:
    def test_minimal_valid(self) -> None:
        m = ColumnMapping(column="Object Text", attribute="Object Text")
        assert m.attribute_type == "Text"
        assert m.read_only is False
        assert m.enum_values == []

    def test_all_attribute_types_accepted(self) -> None:
        for t in ("String", "Text", "Integer", "Real", "Date", "Boolean", "Enum", "MultiEnum"):
            m = ColumnMapping(column="X", attribute="X", attribute_type=t)
            assert m.attribute_type == t

    def test_invalid_attribute_type_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ColumnMapping(column="X", attribute="X", attribute_type="Unknown")

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ColumnMapping(column="X", attribute="X", typo_field="oops")

    def test_empty_column_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ColumnMapping(column="", attribute="X")

    def test_enum_values_stored(self) -> None:
        m = ColumnMapping(column="Status", attribute="Status",
                          attribute_type="Enum", enum_values=["Open", "Closed"])
        assert "Open" in m.enum_values


class TestModuleConfig:
    def _make(self, **kwargs) -> ModuleConfig:
        base = {
            "module_path": "/proj/mod",
            "column_mappings": [
                {"column": "Object Text", "attribute": "Object Text"}
            ],
        }
        base.update(kwargs)
        return ModuleConfig.model_validate(base)

    def test_defaults(self) -> None:
        m = self._make()
        assert m.object_id_column == "Absolute Number"
        assert m.parent_id_column == "Parent Absolute Number"
        assert m.level_column == "Level"
        assert m.object_type_column == "Object Type"

    def test_custom_metadata_columns(self) -> None:
        m = self._make(object_id_column="AbsNum", parent_id_column="ParentID")
        assert m.object_id_column == "AbsNum"
        assert m.parent_id_column == "ParentID"

    def test_empty_column_mappings_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ModuleConfig.model_validate({"module_path": "/x", "column_mappings": []})

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            self._make(unknown_key="oops")


class TestProjectConfig:
    def _make_module(self) -> dict:
        return {
            "module_path": "/proj/mod",
            "column_mappings": [{"column": "Object Text", "attribute": "Object Text"}],
        }

    def test_defaults(self) -> None:
        pc = ProjectConfig.model_validate({"modules": [self._make_module()]})
        assert pc.default_conflict_policy == "excel-wins"
        assert pc.trim_whitespace is True
        assert pc.sheet_protection is False

    def test_invalid_conflict_policy_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ProjectConfig.model_validate({
                "modules": [self._make_module()],
                "default_conflict_policy": "bad-policy",
            })

    def test_all_valid_conflict_policies(self) -> None:
        for policy in ("excel-wins", "doors-wins", "content-based"):
            pc = ProjectConfig.model_validate({
                "modules": [self._make_module()],
                "default_conflict_policy": policy,
            })
            assert pc.default_conflict_policy == policy

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ProjectConfig.model_validate({
                "modules": [self._make_module()],
                "unknown_key": 42,
            })

    def test_empty_modules_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ProjectConfig.model_validate({"modules": []})


class TestLoadConfig:
    def _write_json(self, data: dict) -> Path:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8")
        json.dump(data, tmp)
        tmp.close()
        return Path(tmp.name)

    def _valid_data(self) -> dict:
        return {
            "modules": [
                {
                    "module_path": "/proj/mod",
                    "column_mappings": [{"column": "Object Text", "attribute": "Object Text"}],
                }
            ]
        }

    def test_valid_file_returns_project_config(self) -> None:
        p = self._write_json(self._valid_data())
        config = load_config(p)
        assert isinstance(config, ProjectConfig)
        assert len(config.modules) == 1

    def test_missing_file_raises_config_error(self) -> None:
        with pytest.raises(ConfigurationError, match="Cannot read"):
            load_config("/nonexistent/path/config.json")

    def test_invalid_json_raises_config_error(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8")
        tmp.write("{not valid json")
        tmp.close()
        with pytest.raises(ConfigurationError, match="not valid JSON"):
            load_config(tmp.name)

    def test_schema_violation_raises_config_error(self) -> None:
        data = self._valid_data()
        data["unknown_field"] = "should fail"
        p = self._write_json(data)
        with pytest.raises(ConfigurationError, match="failed validation"):
            load_config(p)

    def test_string_path_accepted(self) -> None:
        p = self._write_json(self._valid_data())
        config = load_config(str(p))
        assert isinstance(config, ProjectConfig)
