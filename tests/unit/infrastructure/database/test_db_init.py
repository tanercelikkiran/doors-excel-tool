"""Smoke tests that database/__init__.py re-exports the public API correctly."""
from __future__ import annotations


class TestDatabasePackageReExports:
    def test_schema_symbols_importable(self) -> None:
        from doors_excel.infrastructure.database import SCHEMA_VERSION, apply_schema
        assert isinstance(SCHEMA_VERSION, int)
        assert callable(apply_schema)

    def test_connection_symbols_importable(self) -> None:
        from doors_excel.infrastructure.database import init_database, open_database
        assert callable(init_database)
        assert callable(open_database)

    def test_repository_classes_importable(self) -> None:
        from doors_excel.infrastructure.database import (
            DiffResultsRepository,
            RollbackSnapshotRepository,
            SessionRepository,
            StagingBaselineRepository,
            StagingDoorsRepository,
            StagingExcelRepository,
            ValidationErrorRepository,
        )
        for cls in (
            SessionRepository, StagingDoorsRepository, StagingBaselineRepository,
            StagingExcelRepository, DiffResultsRepository,
            RollbackSnapshotRepository, ValidationErrorRepository,
        ):
            assert isinstance(cls, type)

    def test_dunder_all_contains_key_symbols(self) -> None:
        import doors_excel.infrastructure.database as m
        if hasattr(m, "__all__"):
            for name in [
                "SCHEMA_VERSION", "apply_schema", "init_database", "open_database",
                "SessionRepository", "DiffResultsRepository", "ValidationErrorRepository",
            ]:
                assert name in m.__all__, f"{name!r} missing from __all__"
