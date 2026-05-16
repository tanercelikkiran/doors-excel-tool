"""Unit tests for the SQLite database schema DDL and apply_schema()."""
from __future__ import annotations

import sqlite3

import pytest

from doors_excel.infrastructure.database.schema import (
    SCHEMA_DDL,
    SCHEMA_VERSION,
    apply_schema,
)


def _mem() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


EXPECTED_TABLES = {
    "schema_version", "sessions",
    "staging_doors", "staging_baseline", "staging_excel",
    "diff_results", "rollback_snapshots", "validation_errors",
}

EXPECTED_INDICES = {
    "idx_sd_session_obj", "idx_sb_session_obj", "idx_se_session_obj",
    "idx_dr_session_type", "idx_rb_session", "idx_ve_session_sev",
}


class TestSchemaDDLConstants:
    def test_schema_ddl_is_non_empty_string(self) -> None:
        assert isinstance(SCHEMA_DDL, str)
        assert len(SCHEMA_DDL) > 100

    def test_schema_version_is_positive_int(self) -> None:
        assert isinstance(SCHEMA_VERSION, int)
        assert SCHEMA_VERSION >= 1


class TestApplySchema:
    def test_creates_all_tables(self) -> None:
        conn = _mem()
        apply_schema(conn)
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert EXPECTED_TABLES <= tables

    def test_creates_all_indices(self) -> None:
        conn = _mem()
        apply_schema(conn)
        indices = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert EXPECTED_INDICES <= indices

    def test_idempotent_second_call_does_not_raise(self) -> None:
        conn = _mem()
        apply_schema(conn)
        apply_schema(conn)

    def test_sessions_table_has_expected_columns(self) -> None:
        conn = _mem()
        apply_schema(conn)
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
        }
        assert {
            "session_id", "excel_path", "doors_module",
            "excel_sha256", "module_version", "created_at", "status",
        } <= cols

    def test_staging_doors_has_rtf_columns(self) -> None:
        conn = _mem()
        apply_schema(conn)
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(staging_doors)").fetchall()
        }
        assert {"rtf_value", "md_hash"} <= cols

    def test_staging_baseline_has_expected_columns(self) -> None:
        conn = _mem()
        apply_schema(conn)
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(staging_baseline)").fetchall()
        }
        assert {"session_id", "object_id", "attribute", "value", "level", "parent_id"} <= cols

    def test_diff_results_rejects_invalid_change_type(self) -> None:
        conn = _mem()
        apply_schema(conn)
        conn.execute(
            "INSERT INTO sessions "
            "(session_id, excel_path, doors_module, excel_sha256, module_version) "
            "VALUES ('s1', 'a.xlsx', '/mod', 'abc', '1.0')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO diff_results (session_id, change_type) VALUES ('s1', 'INVALID')"
            )
            conn.commit()

    def test_validation_errors_rejects_invalid_severity(self) -> None:
        conn = _mem()
        apply_schema(conn)
        conn.execute(
            "INSERT INTO sessions "
            "(session_id, excel_path, doors_module, excel_sha256, module_version) "
            "VALUES ('s1', 'a.xlsx', '/mod', 'abc', '1.0')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO validation_errors "
                "(session_id, row_number, error_code, message, severity) "
                "VALUES ('s1', 1, 'E001', 'msg', 'INVALID')"
            )
            conn.commit()

    def test_sessions_rejects_invalid_status(self) -> None:
        conn = _mem()
        apply_schema(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO sessions "
                "(session_id, excel_path, doors_module, excel_sha256, module_version, status) "
                "VALUES ('s1', 'a.xlsx', '/mod', 'abc', '1.0', 'BAD_STATUS')"
            )
            conn.commit()

    def test_schema_version_row_inserted(self) -> None:
        conn = _mem()
        apply_schema(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row["version"] == SCHEMA_VERSION

    def test_staging_doors_has_rich_format_column(self) -> None:
        conn = _mem()
        apply_schema(conn)
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(staging_doors)").fetchall()
        }
        assert "has_rich_format" in cols

    def test_schema_version_is_2(self) -> None:
        conn = _mem()
        apply_schema(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row["version"] == 2

    def test_migration_v1_to_v2_adds_column(self) -> None:
        """Simulates a v1 database (no has_rich_format column) and verifies migration adds it."""
        conn = _mem()
        conn.executescript("""
            CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
            INSERT INTO schema_version VALUES (1);
            CREATE TABLE sessions (
                session_id TEXT NOT NULL PRIMARY KEY,
                excel_path TEXT NOT NULL,
                doors_module TEXT NOT NULL,
                excel_sha256 TEXT NOT NULL,
                module_version TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE TABLE staging_doors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                object_id INTEGER NOT NULL,
                attribute TEXT NOT NULL,
                value TEXT,
                rtf_value TEXT,
                md_hash TEXT,
                object_type TEXT,
                level INTEGER,
                parent_id INTEGER,
                has_ole INTEGER NOT NULL DEFAULT 0,
                UNIQUE(session_id, object_id, attribute)
            );
        """)
        apply_schema(conn)
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(staging_doors)").fetchall()
        }
        assert "has_rich_format" in cols
        vrow = conn.execute("SELECT version FROM schema_version").fetchone()
        assert vrow[0] == 2
