"""Unit tests for the SQLite connection manager."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from doors_excel.infrastructure.database.connection import init_database, open_database

EXPECTED_TABLES = {
    "schema_version", "sessions",
    "staging_doors", "staging_baseline", "staging_excel",
    "diff_results", "rollback_snapshots", "validation_errors",
}


class TestOpenDatabase:
    def test_creates_file_if_not_exists(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        assert not db_path.exists()
        with open_database(db_path) as conn:
            assert db_path.exists()
            assert conn is not None

    def test_returns_sqlite_connection(self, tmp_path: Path) -> None:
        with open_database(tmp_path / "test.db") as conn:
            assert isinstance(conn, sqlite3.Connection)

    def test_wal_mode_enabled(self, tmp_path: Path) -> None:
        with open_database(tmp_path / "test.db") as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"

    def test_foreign_keys_enabled(self, tmp_path: Path) -> None:
        with open_database(tmp_path / "test.db") as conn:
            fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            assert fk == 1

    def test_row_factory_is_sqlite_row(self, tmp_path: Path) -> None:
        with open_database(tmp_path / "test.db") as conn:
            assert conn.row_factory is sqlite3.Row

    def test_connection_closed_after_context_exit(self, tmp_path: Path) -> None:
        with open_database(tmp_path / "test.db") as conn:
            captured = conn
        with pytest.raises(Exception):
            captured.execute("SELECT 1")

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c" / "test.db"
        with open_database(nested) as conn:
            assert nested.exists()

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        with open_database(str(tmp_path / "str_path.db")) as conn:
            assert conn is not None


class TestInitDatabase:
    def test_returns_open_connection(self, tmp_path: Path) -> None:
        conn = init_database(tmp_path / "init.db")
        try:
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1
        finally:
            conn.close()

    def test_schema_applied_all_tables_present(self, tmp_path: Path) -> None:
        conn = init_database(tmp_path / "init.db")
        try:
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert EXPECTED_TABLES <= tables
        finally:
            conn.close()

    def test_wal_mode_enabled(self, tmp_path: Path) -> None:
        conn = init_database(tmp_path / "init.db")
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"
        finally:
            conn.close()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "dir" / "init.db"
        conn = init_database(nested)
        try:
            assert nested.exists()
        finally:
            conn.close()

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        conn = init_database(str(tmp_path / "str_init.db"))
        try:
            assert conn is not None
        finally:
            conn.close()
