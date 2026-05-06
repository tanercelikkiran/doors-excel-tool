"""Unit tests for the custom exception hierarchy."""
from __future__ import annotations

import pytest

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

SIMPLE_SUBCLASSES = [
    DoorsConnectionError, DoorsAuthError, DXLInjectionError,
    ExcelReadError, ExcelWriteError, TransformationError,
    DiffError, RollbackError, ConfigurationError, SessionError,
]


class TestDoorsExcelError:
    def test_is_exception_subclass(self) -> None:
        assert issubclass(DoorsExcelError, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(DoorsExcelError):
            raise DoorsExcelError("base error")

    def test_str_representation(self) -> None:
        assert "test message" in str(DoorsExcelError("test message"))


class TestSimpleSubclasses:
    @pytest.mark.parametrize("exc_class", SIMPLE_SUBCLASSES)
    def test_is_subclass_of_base(self, exc_class: type) -> None:
        assert issubclass(exc_class, DoorsExcelError)

    @pytest.mark.parametrize("exc_class", SIMPLE_SUBCLASSES)
    def test_caught_by_base_type(self, exc_class: type) -> None:
        with pytest.raises(DoorsExcelError):
            raise exc_class("msg")


class TestDXLExecutionError:
    def test_is_subclass_of_base(self) -> None:
        assert issubclass(DXLExecutionError, DoorsExcelError)

    def test_dxl_output_stored(self) -> None:
        exc = DXLExecutionError("failed", dxl_output="error: undefined variable")
        assert exc.dxl_output == "error: undefined variable"

    def test_dxl_output_defaults_to_empty(self) -> None:
        assert DXLExecutionError("failed").dxl_output == ""

    def test_message_preserved(self) -> None:
        assert "failed" in str(DXLExecutionError("failed"))

    def test_repr_includes_dxl_output(self) -> None:
        exc = DXLExecutionError("x", dxl_output="oops")
        assert "oops" in repr(exc)


class TestValidationError:
    def test_is_subclass_of_base(self) -> None:
        assert issubclass(ValidationError, DoorsExcelError)

    def test_row_and_attribute_stored(self) -> None:
        exc = ValidationError("bad value", row=42, attribute="Status")
        assert exc.row == 42
        assert exc.attribute == "Status"

    def test_row_defaults_to_zero(self) -> None:
        assert ValidationError("x").row == 0

    def test_attribute_defaults_to_empty(self) -> None:
        assert ValidationError("x").attribute == ""

    def test_message_preserved(self) -> None:
        assert "bad value" in str(ValidationError("bad value", row=1, attribute="A"))
