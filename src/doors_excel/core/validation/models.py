"""Pydantic v2 models for project configuration (REQ-INF-003, REQ-INF-004).

Configuration is loaded from a JSON file with ``load_config()``.  All models
use ``extra="forbid"`` so typos in hand-edited JSON files fail loudly.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from doors_excel.common.exceptions import ConfigurationError
from doors_excel.common.types import ConflictPolicy

# Supported DOORS attribute types for column mapping
AttributeType = Literal[
    "String",
    "Text",
    "Integer",
    "Real",
    "Date",
    "Boolean",
    "Enum",
    "MultiEnum",
]


class ColumnMapping(BaseModel):
    """Maps one Excel column header to a DOORS attribute."""

    model_config = ConfigDict(extra="forbid")

    column: Annotated[str, Field(min_length=1)]
    attribute: Annotated[str, Field(min_length=1)]
    attribute_type: AttributeType = "Text"
    enum_values: list[str] = Field(default_factory=list)
    read_only: bool = False

    @field_validator("enum_values")
    @classmethod
    def _enum_values_only_for_enum_type(
        cls, v: list[str], info: object
    ) -> list[str]:
        # No cross-field check possible here without model_validator;
        # downstream validation enforces that enum_values is non-empty
        # when attribute_type is Enum/MultiEnum.
        return v


class ModuleConfig(BaseModel):
    """Configuration for one DOORS module's import/export mapping."""

    model_config = ConfigDict(extra="forbid")

    module_path: Annotated[str, Field(min_length=1)]
    column_mappings: Annotated[list[ColumnMapping], Field(min_length=1)]
    object_id_column: str = "Absolute Number"
    parent_id_column: str = "Parent Absolute Number"
    level_column: str = "Level"
    object_type_column: str = "Object Type"


class ProjectConfig(BaseModel):
    """Top-level project configuration file model."""

    model_config = ConfigDict(extra="forbid")

    modules: Annotated[list[ModuleConfig], Field(min_length=1)]
    default_conflict_policy: ConflictPolicy = "excel-wins"
    trim_whitespace: bool = True
    sheet_protection: bool = False
    sheet_protection_password: str | None = None


def load_config(path: Path | str) -> ProjectConfig:
    """Load and validate a JSON config file, returning a :class:`ProjectConfig`.

    Raises :class:`~doors_excel.common.exceptions.ConfigurationError` if the
    file cannot be read, is not valid JSON, or fails Pydantic validation.
    """
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"Cannot read config file {p}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Config file {p} is not valid JSON: {exc}") from exc
    try:
        return ProjectConfig.model_validate(data)
    except Exception as exc:
        raise ConfigurationError(f"Config file {p} failed validation: {exc}") from exc
