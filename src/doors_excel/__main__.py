"""Minimal Typer entry point for doors-excel-tool (Phase 1 stub).

Full subcommands (export, import, validate, rollback, gui, interactive)
are added in Phase 9. This stub ensures the package is executable
immediately after installation.
"""
from __future__ import annotations

import typer

from doors_excel.common.logging import setup_logging

app = typer.Typer(
    name="doors-excel",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback()
def callback() -> None:
    """Bidirectional IBM DOORS to Microsoft Excel synchronisation tool.

    Run with --help on any subcommand for detailed usage.
    """


def main() -> None:  # pragma: no cover
    setup_logging()
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
