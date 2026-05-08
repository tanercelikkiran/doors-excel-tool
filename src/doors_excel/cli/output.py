"""Rich-based output helpers for the CLI."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from doors_excel.core.diff.summary import DiffSummary
from doors_excel.core.validation.validator import ValidationResult

console = Console()
error_console = Console(stderr=True, style="bold red")


def print_validation_result(result: ValidationResult, *, quiet: bool = False) -> None:
    """Print a summary of validation results to stdout."""
    if result.has_errors:
        error_console.print(
            f"[bold red]Validation failed:[/] "
            f"{result.blocking_count} blocking error(s), "
            f"{result.warning_count} warning(s)"
        )
        return
    if not quiet:
        console.print(
            f"[bold green]Validation passed[/] "
            f"({result.warning_count} warning(s))"
        )


def print_diff_summary(summary: DiffSummary, *, quiet: bool = False) -> None:
    """Print a change-count table to stdout."""
    if quiet and summary.is_clean:
        return

    t = Table(title="Diff Summary", show_header=True, header_style="bold cyan")
    t.add_column("Change Type", style="dim")
    t.add_column("Count", justify="right")

    t.add_row("New", str(summary.new_count))
    t.add_row("Deleted", str(summary.deleted_count))
    t.add_row("Updated", str(summary.updated_count))
    t.add_row("Conflict", str(summary.conflict_count),
              style="bold red" if summary.has_conflicts else "")
    t.add_row("Moved", str(summary.moved_count))

    console.print(t)

    if summary.has_baseline_mismatch:
        console.print(
            f"[yellow]Warning:[/] {summary.baseline_mismatch_count} object(s) "
            "added to DOORS since export (baseline mismatch)."
        )
    if summary.is_clean:
        console.print("[bold green]No changes detected.[/]")


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    error_console.print(f"Error: {message}")
