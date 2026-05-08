"""Smoke tests for core/validation/__init__.py re-exports."""
from __future__ import annotations


class TestValidationReExports:
    def test_model_symbols(self) -> None:
        from doors_excel.core.validation import (
            ColumnMapping,
            ModuleConfig,
            ProjectConfig,
            load_config,
        )
        assert callable(load_config)
        for cls in (ColumnMapping, ModuleConfig, ProjectConfig):
            assert isinstance(cls, type)

    def test_validator_symbols(self) -> None:
        from doors_excel.core.validation import ValidationResult, validate_session
        assert callable(validate_session)
        assert isinstance(ValidationResult, type)

    def test_attribute_type_exported(self) -> None:
        from doors_excel.core.validation import AttributeType
        # AttributeType is a Literal — not a class, but it should be accessible
        assert AttributeType is not None

    def test_dunder_all_complete(self) -> None:
        import doors_excel.core.validation as m
        if not hasattr(m, "__all__"):
            return
        expected = [
            "AttributeType", "ColumnMapping", "ModuleConfig", "ProjectConfig",
            "load_config", "ValidationResult", "validate_session",
        ]
        for name in expected:
            assert name in m.__all__, f"{name!r} missing from __all__"
