"""Unit tests for shared type aliases and Literal types."""
from __future__ import annotations

from typing import get_args

import pytest

from doors_excel.common.types import (
    ConflictPolicy,
    ObjectId,
    ObjectType,
    Placement,
    RowData,
    StagingRow,
)


class TestObjectId:
    def test_is_int_alias(self) -> None:
        val: ObjectId = 42
        assert isinstance(val, int)

    def test_zero_is_valid(self) -> None:
        val: ObjectId = 0
        assert val == 0


class TestConflictPolicy:
    def test_allowed_values(self) -> None:
        assert set(get_args(ConflictPolicy)) == {"excel-wins", "doors-wins", "content-based"}

    @pytest.mark.parametrize("value", ["excel-wins", "doors-wins", "content-based"])
    def test_each_value_in_literal(self, value: str) -> None:
        assert value in get_args(ConflictPolicy)


class TestObjectType:
    EXPECTED = {"OBJECT", "TABLE_START", "TABLE_ROW", "TABLE_CELL", "TABLE_END", "NEW_TABLE"}

    def test_all_expected_values_present(self) -> None:
        assert set(get_args(ObjectType)) == self.EXPECTED

    @pytest.mark.parametrize("value", ["OBJECT", "TABLE_START", "TABLE_ROW",
                                        "TABLE_CELL", "TABLE_END", "NEW_TABLE"])
    def test_each_value_in_literal(self, value: str) -> None:
        assert value in get_args(ObjectType)


class TestPlacement:
    def test_allowed_values(self) -> None:
        assert set(get_args(Placement)) == {"after", "as_child"}


class TestRowData:
    def test_accepts_mixed_values(self) -> None:
        row: RowData = {"Absolute Number": 42, "Object Text": "hello", "Status": None}
        assert row["Absolute Number"] == 42
        assert row["Status"] is None


class TestStagingRow:
    def test_accepts_string_keys(self) -> None:
        row: StagingRow = {"object_id": 1, "attribute": "Status", "value": "Open"}
        assert row["object_id"] == 1
