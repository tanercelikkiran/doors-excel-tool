"""Public API layer — orchestrates export, import, validate, and rollback workflows."""
from __future__ import annotations

from doors_excel.api.diff import run_diff
from doors_excel.api.export import export_module
from doors_excel.api.rollback import generate_rollback_excel
from doors_excel.api.sessions import (
    SessionInfo,
    SessionManager,
    compute_file_sha256,
    session_file_path,
)
from doors_excel.api.validate import validate_config, validate_excel

__all__ = [
    # sessions
    "SessionInfo",
    "SessionManager",
    "compute_file_sha256",
    "session_file_path",
    # validation
    "validate_config",
    "validate_excel",
    # diff
    "run_diff",
    # export
    "export_module",
    # rollback
    "generate_rollback_excel",
]
