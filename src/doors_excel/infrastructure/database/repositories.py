"""Domain repository classes for the doors-excel-tool SQLite layer."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass
class SessionRepository:
    conn: sqlite3.Connection

    def create(
        self,
        *,
        session_id: str,
        excel_path: str,
        doors_module: str,
        excel_sha256: str,
        module_version: str,
    ) -> None:
        self.conn.execute(
            """INSERT INTO sessions
               (session_id, excel_path, doors_module, excel_sha256, module_version)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, excel_path, doors_module, excel_sha256, module_version),
        )
        self.conn.commit()

    def get(self, session_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()

    def update_status(self, session_id: str, status: str) -> None:
        self.conn.execute(
            "UPDATE sessions SET status = ? WHERE session_id = ?",
            (status, session_id),
        )
        self.conn.commit()


@dataclass
class StagingDoorsRepository:
    conn: sqlite3.Connection

    def insert_many(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        self.conn.executemany(
            """INSERT OR REPLACE INTO staging_doors
               (session_id, object_id, attribute, value, rtf_value, md_hash,
                object_type, level, parent_id, has_ole)
               VALUES (:session_id, :object_id, :attribute, :value, :rtf_value, :md_hash,
                       :object_type, :level, :parent_id, :has_ole)""",
            rows,
        )
        self.conn.commit()

    def get_by_session(self, session_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM staging_doors WHERE session_id = ? ORDER BY object_id, attribute",
            (session_id,),
        ).fetchall()

    def clear(self, session_id: str) -> None:
        self.conn.execute("DELETE FROM staging_doors WHERE session_id = ?", (session_id,))
        self.conn.commit()


@dataclass
class StagingBaselineRepository:
    conn: sqlite3.Connection

    def insert_many(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        self.conn.executemany(
            """INSERT OR REPLACE INTO staging_baseline
               (session_id, object_id, attribute, value, object_type, level, parent_id)
               VALUES (:session_id, :object_id, :attribute, :value,
                       :object_type, :level, :parent_id)""",
            rows,
        )
        self.conn.commit()

    def get_by_session(self, session_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM staging_baseline WHERE session_id = ? ORDER BY object_id, attribute",
            (session_id,),
        ).fetchall()

    def clear(self, session_id: str) -> None:
        self.conn.execute("DELETE FROM staging_baseline WHERE session_id = ?", (session_id,))
        self.conn.commit()


@dataclass
class StagingExcelRepository:
    conn: sqlite3.Connection

    def insert_many(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        self.conn.executemany(
            """INSERT OR REPLACE INTO staging_excel
               (session_id, row_number, object_id, attribute, value)
               VALUES (:session_id, :row_number, :object_id, :attribute, :value)""",
            rows,
        )
        self.conn.commit()

    def get_by_session(self, session_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM staging_excel WHERE session_id = ? ORDER BY row_number, attribute",
            (session_id,),
        ).fetchall()

    def clear(self, session_id: str) -> None:
        self.conn.execute("DELETE FROM staging_excel WHERE session_id = ?", (session_id,))
        self.conn.commit()


@dataclass
class DiffResultsRepository:
    conn: sqlite3.Connection

    def insert_many(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        self.conn.executemany(
            """INSERT INTO diff_results
               (session_id, object_id, attribute, change_type, excel_value,
                doors_value, baseline_value, resolved_value, row_number)
               VALUES (:session_id, :object_id, :attribute, :change_type, :excel_value,
                       :doors_value, :baseline_value, :resolved_value, :row_number)""",
            rows,
        )
        self.conn.commit()

    def get_by_session(self, session_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM diff_results WHERE session_id = ? ORDER BY object_id, attribute",
            (session_id,),
        ).fetchall()

    def get_by_change_type(self, session_id: str, change_type: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM diff_results WHERE session_id = ? AND change_type = ?",
            (session_id, change_type),
        ).fetchall()

    def get_paginated(
        self, session_id: str, *, offset: int, limit: int
    ) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM diff_results WHERE session_id = ? ORDER BY id LIMIT ? OFFSET ?",
            (session_id, limit, offset),
        ).fetchall()

    def count(self, session_id: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM diff_results WHERE session_id = ?", (session_id,)
        ).fetchone()
        return row[0] if row else 0


@dataclass
class RollbackSnapshotRepository:
    conn: sqlite3.Connection

    def insert_many(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        self.conn.executemany(
            """INSERT OR REPLACE INTO rollback_snapshots
               (session_id, object_id, attribute, original_value, original_rtf)
               VALUES (:session_id, :object_id, :attribute, :original_value, :original_rtf)""",
            rows,
        )
        self.conn.commit()

    def get_by_session(self, session_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM rollback_snapshots WHERE session_id = ? ORDER BY object_id, attribute",
            (session_id,),
        ).fetchall()


@dataclass
class ValidationErrorRepository:
    conn: sqlite3.Connection

    def insert_many(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        self.conn.executemany(
            """INSERT INTO validation_errors
               (session_id, row_number, object_id, attribute, error_code, message, severity)
               VALUES (:session_id, :row_number, :object_id, :attribute,
                       :error_code, :message, :severity)""",
            rows,
        )
        self.conn.commit()

    def get_by_session(self, session_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM validation_errors WHERE session_id = ? ORDER BY row_number",
            (session_id,),
        ).fetchall()

    def count_blocking(self, session_id: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM validation_errors "
            "WHERE session_id = ? AND severity = 'BLOCKING'",
            (session_id,),
        ).fetchone()
        return row[0] if row else 0
