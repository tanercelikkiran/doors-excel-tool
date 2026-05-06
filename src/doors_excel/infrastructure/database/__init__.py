"""SQLite persistence layer -- schema, connections, and repositories."""
from __future__ import annotations

from doors_excel.infrastructure.database.connection import init_database, open_database
from doors_excel.infrastructure.database.repositories import (
    DiffResultsRepository,
    RollbackSnapshotRepository,
    SessionRepository,
    StagingBaselineRepository,
    StagingDoorsRepository,
    StagingExcelRepository,
    ValidationErrorRepository,
)
from doors_excel.infrastructure.database.schema import SCHEMA_VERSION, apply_schema

__all__ = [
    # schema
    "SCHEMA_VERSION",
    "apply_schema",
    # connection
    "init_database",
    "open_database",
    # repositories
    "SessionRepository",
    "StagingDoorsRepository",
    "StagingBaselineRepository",
    "StagingExcelRepository",
    "DiffResultsRepository",
    "RollbackSnapshotRepository",
    "ValidationErrorRepository",
]
