"""Unit tests for all seven database repository classes."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from doors_excel.infrastructure.database.connection import init_database
from doors_excel.infrastructure.database.repositories import (
    DiffResultsRepository,
    RollbackSnapshotRepository,
    SessionRepository,
    StagingBaselineRepository,
    StagingDoorsRepository,
    StagingExcelRepository,
    ValidationErrorRepository,
)

SESSION_ID = "sess-001"
SESSION_DEFAULTS: dict[str, Any] = {
    "session_id": SESSION_ID,
    "excel_path": "work.xlsx",
    "doors_module": "/MyProject/MyModule",
    "excel_sha256": "abc123",
    "module_version": "2.0",
}


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = init_database(tmp_path / "test.db")
    yield c
    c.close()


@pytest.fixture()
def seeded_conn(conn: sqlite3.Connection) -> sqlite3.Connection:
    SessionRepository(conn).create(**SESSION_DEFAULTS)
    return conn


class TestSessionRepository:
    def test_create_and_get(self, conn: sqlite3.Connection) -> None:
        repo = SessionRepository(conn)
        repo.create(**SESSION_DEFAULTS)
        row = repo.get(SESSION_ID)
        assert row is not None
        assert row["excel_path"] == "work.xlsx"
        assert row["status"] == "active"

    def test_update_status(self, conn: sqlite3.Connection) -> None:
        repo = SessionRepository(conn)
        repo.create(**SESSION_DEFAULTS)
        repo.update_status(SESSION_ID, "completed")
        assert repo.get(SESSION_ID)["status"] == "completed"

    def test_get_nonexistent_returns_none(self, conn: sqlite3.Connection) -> None:
        assert SessionRepository(conn).get("no-such-id") is None

    def test_duplicate_session_id_raises(self, conn: sqlite3.Connection) -> None:
        repo = SessionRepository(conn)
        repo.create(**SESSION_DEFAULTS)
        with pytest.raises(sqlite3.IntegrityError):
            repo.create(**SESSION_DEFAULTS)


class TestStagingDoorsRepository:
    def _rows(self) -> list[dict[str, Any]]:
        return [
            {
                "session_id": SESSION_ID, "object_id": 10, "attribute": "Object Text",
                "value": "Hello", "rtf_value": r"{\rtf1 Hello}", "md_hash": "d3ad",
                "object_type": "OBJECT", "level": 1, "parent_id": None, "has_ole": 0,
            },
            {
                "session_id": SESSION_ID, "object_id": 11, "attribute": "Status",
                "value": "Open", "rtf_value": None, "md_hash": None,
                "object_type": "OBJECT", "level": 1, "parent_id": None, "has_ole": 0,
            },
        ]

    def test_insert_many_and_get_by_session(self, seeded_conn: sqlite3.Connection) -> None:
        repo = StagingDoorsRepository(seeded_conn)
        repo.insert_many(self._rows())
        rows = repo.get_by_session(SESSION_ID)
        assert len(rows) == 2

    def test_rtf_value_persisted(self, seeded_conn: sqlite3.Connection) -> None:
        repo = StagingDoorsRepository(seeded_conn)
        repo.insert_many(self._rows())
        row = next(r for r in repo.get_by_session(SESSION_ID) if r["object_id"] == 10)
        assert row["rtf_value"] == r"{\rtf1 Hello}"
        assert row["md_hash"] == "d3ad"

    def test_clear_removes_session_rows(self, seeded_conn: sqlite3.Connection) -> None:
        repo = StagingDoorsRepository(seeded_conn)
        repo.insert_many(self._rows())
        repo.clear(SESSION_ID)
        assert repo.get_by_session(SESSION_ID) == []

    def test_insert_many_empty_list_is_noop(self, seeded_conn: sqlite3.Connection) -> None:
        StagingDoorsRepository(seeded_conn).insert_many([])


class TestStagingBaselineRepository:
    def _rows(self) -> list[dict[str, Any]]:
        return [
            {
                "session_id": SESSION_ID, "object_id": 10, "attribute": "Object Text",
                "value": "Hello", "object_type": "OBJECT", "level": 1, "parent_id": None,
            },
        ]

    def test_insert_many_and_get_by_session(self, seeded_conn: sqlite3.Connection) -> None:
        repo = StagingBaselineRepository(seeded_conn)
        repo.insert_many(self._rows())
        rows = repo.get_by_session(SESSION_ID)
        assert len(rows) == 1
        assert rows[0]["value"] == "Hello"

    def test_clear_removes_session_rows(self, seeded_conn: sqlite3.Connection) -> None:
        repo = StagingBaselineRepository(seeded_conn)
        repo.insert_many(self._rows())
        repo.clear(SESSION_ID)
        assert repo.get_by_session(SESSION_ID) == []


class TestStagingExcelRepository:
    def _rows(self) -> list[dict[str, Any]]:
        return [
            {"session_id": SESSION_ID, "row_number": 2, "object_id": 10,
             "attribute": "Object Text", "value": "Updated Hello"},
            {"session_id": SESSION_ID, "row_number": 3, "object_id": None,
             "attribute": "Object Text", "value": "Brand new"},
        ]

    def test_insert_many_and_get_by_session(self, seeded_conn: sqlite3.Connection) -> None:
        repo = StagingExcelRepository(seeded_conn)
        repo.insert_many(self._rows())
        rows = repo.get_by_session(SESSION_ID)
        assert len(rows) == 2

    def test_null_object_id_allowed(self, seeded_conn: sqlite3.Connection) -> None:
        repo = StagingExcelRepository(seeded_conn)
        repo.insert_many(self._rows())
        new_row = next(r for r in repo.get_by_session(SESSION_ID) if r["row_number"] == 3)
        assert new_row["object_id"] is None

    def test_clear_removes_session_rows(self, seeded_conn: sqlite3.Connection) -> None:
        repo = StagingExcelRepository(seeded_conn)
        repo.insert_many(self._rows())
        repo.clear(SESSION_ID)
        assert repo.get_by_session(SESSION_ID) == []


class TestDiffResultsRepository:
    def _rows(self) -> list[dict[str, Any]]:
        return [
            {
                "session_id": SESSION_ID, "object_id": 10, "attribute": "Object Text",
                "change_type": "UPDATED", "excel_value": "New", "doors_value": "Old",
                "baseline_value": "Old", "resolved_value": None, "row_number": 2,
            },
            {
                "session_id": SESSION_ID, "object_id": None, "attribute": "Object Text",
                "change_type": "NEW", "excel_value": "Brand new", "doors_value": None,
                "baseline_value": None, "resolved_value": None, "row_number": 3,
            },
            {
                "session_id": SESSION_ID, "object_id": 99, "attribute": "Status",
                "change_type": "CONFLICT", "excel_value": "Open", "doors_value": "Closed",
                "baseline_value": "Open", "resolved_value": None, "row_number": 4,
            },
        ]

    def test_insert_many_and_get_by_session(self, seeded_conn: sqlite3.Connection) -> None:
        repo = DiffResultsRepository(seeded_conn)
        repo.insert_many(self._rows())
        rows = repo.get_by_session(SESSION_ID)
        assert len(rows) == 3

    def test_count(self, seeded_conn: sqlite3.Connection) -> None:
        repo = DiffResultsRepository(seeded_conn)
        repo.insert_many(self._rows())
        assert repo.count(SESSION_ID) == 3

    def test_get_by_change_type(self, seeded_conn: sqlite3.Connection) -> None:
        repo = DiffResultsRepository(seeded_conn)
        repo.insert_many(self._rows())
        conflicts = repo.get_by_change_type(SESSION_ID, "CONFLICT")
        assert len(conflicts) == 1
        assert conflicts[0]["object_id"] == 99

    def test_get_paginated(self, seeded_conn: sqlite3.Connection) -> None:
        repo = DiffResultsRepository(seeded_conn)
        repo.insert_many(self._rows())
        page = repo.get_paginated(SESSION_ID, offset=0, limit=2)
        assert len(page) == 2
        page2 = repo.get_paginated(SESSION_ID, offset=2, limit=2)
        assert len(page2) == 1

    def test_count_empty_session_returns_zero(self, seeded_conn: sqlite3.Connection) -> None:
        assert DiffResultsRepository(seeded_conn).count(SESSION_ID) == 0


class TestRollbackSnapshotRepository:
    def _rows(self) -> list[dict[str, Any]]:
        return [
            {
                "session_id": SESSION_ID, "object_id": 10, "attribute": "Object Text",
                "original_value": "Old Text", "original_rtf": r"{\rtf1 Old Text}",
            },
            {
                "session_id": SESSION_ID, "object_id": 10, "attribute": "Status",
                "original_value": "Open", "original_rtf": None,
            },
        ]

    def test_insert_many_and_get_by_session(self, seeded_conn: sqlite3.Connection) -> None:
        repo = RollbackSnapshotRepository(seeded_conn)
        repo.insert_many(self._rows())
        rows = repo.get_by_session(SESSION_ID)
        assert len(rows) == 2

    def test_original_rtf_persisted(self, seeded_conn: sqlite3.Connection) -> None:
        repo = RollbackSnapshotRepository(seeded_conn)
        repo.insert_many(self._rows())
        row = next(
            r for r in repo.get_by_session(SESSION_ID)
            if r["attribute"] == "Object Text"
        )
        assert row["original_rtf"] == r"{\rtf1 Old Text}"


class TestValidationErrorRepository:
    def _rows(self) -> list[dict[str, Any]]:
        return [
            {
                "session_id": SESSION_ID, "row_number": 5, "object_id": 10,
                "attribute": "Status", "error_code": "E_ENUM",
                "message": "Invalid enum value 'Draft'", "severity": "BLOCKING",
            },
            {
                "session_id": SESSION_ID, "row_number": 6, "object_id": None,
                "attribute": "Object Text", "error_code": "W_TRUNCATE",
                "message": "Value exceeds 1024 chars", "severity": "WARNING",
            },
        ]

    def test_insert_many_and_get_by_session(self, seeded_conn: sqlite3.Connection) -> None:
        repo = ValidationErrorRepository(seeded_conn)
        repo.insert_many(self._rows())
        rows = repo.get_by_session(SESSION_ID)
        assert len(rows) == 2

    def test_count_blocking_excludes_warnings(self, seeded_conn: sqlite3.Connection) -> None:
        repo = ValidationErrorRepository(seeded_conn)
        repo.insert_many(self._rows())
        assert repo.count_blocking(SESSION_ID) == 1

    def test_count_blocking_empty_returns_zero(self, seeded_conn: sqlite3.Connection) -> None:
        assert ValidationErrorRepository(seeded_conn).count_blocking(SESSION_ID) == 0
