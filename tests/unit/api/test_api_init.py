"""Smoke tests for api/__init__.py re-exports."""
from __future__ import annotations


class TestApiReExports:
    def test_session_symbols(self) -> None:
        from doors_excel.api import (
            SessionInfo,
            SessionManager,
            compute_file_sha256,
            session_file_path,
        )
        assert callable(compute_file_sha256)
        assert callable(session_file_path)
        for cls in (SessionInfo, SessionManager):
            assert isinstance(cls, type)

    def test_validate_symbols(self) -> None:
        from doors_excel.api import validate_config, validate_excel
        assert callable(validate_config)
        assert callable(validate_excel)

    def test_diff_symbol(self) -> None:
        from doors_excel.api import run_diff
        assert callable(run_diff)

    def test_dunder_all_complete(self) -> None:
        import doors_excel.api as m
        if not hasattr(m, "__all__"):
            return
        expected = [
            "SessionInfo", "SessionManager", "compute_file_sha256", "session_file_path",
            "validate_config", "validate_excel",
            "run_diff",
        ]
        for name in expected:
            assert name in m.__all__, f"{name!r} missing from __all__"
