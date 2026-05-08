"""Smoke tests for cli/output.py — Rich output helpers."""
from __future__ import annotations

from io import StringIO

from rich.console import Console

from doors_excel.cli.output import print_diff_summary, print_error, print_validation_result
from doors_excel.core.diff.summary import DiffSummary
from doors_excel.core.validation.validator import ValidationResult


def _capture(fn, *args, **kwargs) -> str:
    """Run *fn* with a captured Rich console and return text output."""
    buf = StringIO()
    cap = Console(file=buf, highlight=False, no_color=True)
    import doors_excel.cli.output as m
    orig = m.console
    m.console = cap
    try:
        fn(*args, **kwargs)
    finally:
        m.console = orig
    return buf.getvalue()


class TestPrintValidationResult:
    def test_passes_no_error_output(self) -> None:
        result = ValidationResult(blocking_count=0, warning_count=0)
        out = _capture(print_validation_result, result)
        assert "passed" in out.lower()

    def test_quiet_no_output_on_pass(self) -> None:
        result = ValidationResult(blocking_count=0, warning_count=0)
        out = _capture(print_validation_result, result, quiet=True)
        assert out.strip() == ""

    def test_failure_does_not_raise(self) -> None:
        result = ValidationResult(blocking_count=3, warning_count=1)
        # Should not raise; output goes to stderr (not captured here)
        print_validation_result(result)


class TestPrintDiffSummary:
    def test_clean_summary_prints_no_changes(self) -> None:
        s = DiffSummary(0, 0, 0, 0, 0, 0)
        out = _capture(print_diff_summary, s)
        assert "No changes" in out

    def test_summary_with_changes_shows_table(self) -> None:
        s = DiffSummary(new_count=1, deleted_count=2, updated_count=3,
                        conflict_count=0, moved_count=0, baseline_mismatch_count=0)
        out = _capture(print_diff_summary, s)
        assert "1" in out
        assert "2" in out
        assert "3" in out

    def test_baseline_mismatch_warns(self) -> None:
        s = DiffSummary(0, 0, 0, 0, 0, baseline_mismatch_count=5)
        out = _capture(print_diff_summary, s)
        assert "5" in out

    def test_quiet_clean_produces_no_output(self) -> None:
        s = DiffSummary(0, 0, 0, 0, 0, 0)
        out = _capture(print_diff_summary, s, quiet=True)
        assert out.strip() == ""


class TestPrintError:
    def test_does_not_raise(self) -> None:
        print_error("something went wrong")
