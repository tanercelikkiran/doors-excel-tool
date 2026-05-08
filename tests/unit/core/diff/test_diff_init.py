"""Smoke tests for core/diff/__init__.py re-exports."""
from __future__ import annotations


class TestDiffReExports:
    def test_engine_symbols(self) -> None:
        from doors_excel.core.diff import DiffStats, baseline_mismatch_check, compute_diff
        assert callable(compute_diff)
        assert callable(baseline_mismatch_check)
        assert isinstance(DiffStats, type)

    def test_conflict_symbol(self) -> None:
        from doors_excel.core.diff import apply_conflict_policy
        assert callable(apply_conflict_policy)

    def test_summary_symbols(self) -> None:
        from doors_excel.core.diff import DiffSummary, get_diff_summary
        assert callable(get_diff_summary)
        assert isinstance(DiffSummary, type)

    def test_dunder_all_complete(self) -> None:
        import doors_excel.core.diff as m
        if not hasattr(m, "__all__"):
            return
        expected = [
            "DiffStats", "compute_diff", "baseline_mismatch_check",
            "apply_conflict_policy",
            "DiffSummary", "get_diff_summary",
        ]
        for name in expected:
            assert name in m.__all__, f"{name!r} missing from __all__"
