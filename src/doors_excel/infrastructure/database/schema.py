"""SQLite DDL constants and schema bootstrap for doors-excel-tool."""
from __future__ import annotations

import sqlite3

SCHEMA_VERSION: int = 1

SCHEMA_DDL: str = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id     TEXT NOT NULL PRIMARY KEY,
    excel_path     TEXT NOT NULL,
    doors_module   TEXT NOT NULL,
    excel_sha256   TEXT NOT NULL,
    module_version TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    status         TEXT NOT NULL DEFAULT 'active'
                   CHECK(status IN ('active', 'completed', 'failed', 'rolled_back'))
);

CREATE TABLE IF NOT EXISTS staging_doors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    object_id   INTEGER NOT NULL,
    attribute   TEXT    NOT NULL,
    value       TEXT,
    rtf_value   TEXT,
    md_hash     TEXT,
    object_type TEXT,
    level       INTEGER,
    parent_id   INTEGER,
    has_ole     INTEGER NOT NULL DEFAULT 0,
    UNIQUE(session_id, object_id, attribute)
);

CREATE TABLE IF NOT EXISTS staging_baseline (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    object_id   INTEGER NOT NULL,
    attribute   TEXT    NOT NULL,
    value       TEXT,
    object_type TEXT,
    level       INTEGER,
    parent_id   INTEGER,
    UNIQUE(session_id, object_id, attribute)
);

CREATE TABLE IF NOT EXISTS staging_excel (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    row_number  INTEGER NOT NULL,
    object_id   INTEGER,
    attribute   TEXT    NOT NULL,
    value       TEXT,
    md_hash     TEXT,
    UNIQUE(session_id, row_number, attribute)
);

CREATE TABLE IF NOT EXISTS diff_results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT    NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    object_id      INTEGER,
    attribute      TEXT,
    change_type    TEXT    NOT NULL
                   CHECK(change_type IN ('NEW','UPDATED','DELETED','MOVED','CONFLICT','UNCHANGED')),
    excel_value    TEXT,
    doors_value    TEXT,
    baseline_value TEXT,
    resolved_value TEXT,
    row_number     INTEGER
);

CREATE TABLE IF NOT EXISTS rollback_snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT    NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    object_id      INTEGER NOT NULL,
    attribute      TEXT    NOT NULL,
    original_value TEXT,
    original_rtf   TEXT,
    UNIQUE(session_id, object_id, attribute)
);

CREATE TABLE IF NOT EXISTS validation_errors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    row_number  INTEGER NOT NULL DEFAULT 0,
    object_id   INTEGER,
    attribute   TEXT,
    error_code  TEXT    NOT NULL,
    message     TEXT    NOT NULL,
    severity    TEXT    NOT NULL DEFAULT 'BLOCKING'
                CHECK(severity IN ('BLOCKING', 'WARNING'))
);

CREATE INDEX IF NOT EXISTS idx_sd_session_obj  ON staging_doors(session_id, object_id);
CREATE INDEX IF NOT EXISTS idx_sb_session_obj  ON staging_baseline(session_id, object_id);
CREATE INDEX IF NOT EXISTS idx_se_session_obj  ON staging_excel(session_id, object_id);
CREATE INDEX IF NOT EXISTS idx_dr_session_type ON diff_results(session_id, change_type);
CREATE INDEX IF NOT EXISTS idx_rb_session      ON rollback_snapshots(session_id, object_id);
CREATE INDEX IF NOT EXISTS idx_ve_session_sev  ON validation_errors(session_id, severity);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    """Execute all DDL statements and seed the schema_version row.

    Safe to call multiple times — all statements use IF NOT EXISTS.
    """
    conn.executescript(SCHEMA_DDL)
    conn.execute(
        "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
        (SCHEMA_VERSION,),
    )
    conn.commit()
