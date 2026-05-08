"""Typer CLI application for doors-excel-tool (REQ-INF-001, REQ-INF-002).

Commands
--------
validate    Validate a config file and/or an Excel file (fully implemented).
export      Export a DOORS module to Excel (stub — not yet implemented).
import-mod  Import an Excel file into DOORS (stub — not yet implemented).
rollback    Generate a rollback Excel from a session snapshot (stub).
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from doors_excel.cli.output import print_error, print_validation_result
from doors_excel.common.exceptions import ConfigurationError, DoorsExcelError

app = typer.Typer(
    name="doors-excel",
    help="Bidirectional synchronization between IBM DOORS and Microsoft Excel.",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@app.command()
def validate(
    config: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Path to the JSON config file."),
    ] = None,
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Excel file to validate (.xlsx/.xlsm)."),
    ] = None,
    module: Annotated[
        Optional[str],
        typer.Option("--module", "-m", help="DOORS module path (selects config section)."),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-error output."),
    ] = False,
) -> None:
    """Validate a config file and/or an Excel file against DOORS schema rules."""
    if config is None and file is None:
        print_error("Provide --config, --file, or both.")
        raise typer.Exit(1)

    from doors_excel.api.validate import validate_config, validate_excel

    project_cfg = None

    # -- Config validation --
    if config is not None:
        try:
            project_cfg = validate_config(config)
        except ConfigurationError as exc:
            print_error(str(exc))
            raise typer.Exit(1) from exc
        if not quiet:
            from doors_excel.cli.output import console
            console.print(f"[bold green]Config OK[/] — {len(project_cfg.modules)} module(s) defined.")

    # -- Excel validation --
    if file is not None:
        if project_cfg is None:
            print_error("--config is required when --file is provided.")
            raise typer.Exit(1)

        # Find the matching module config
        target_module = module or (project_cfg.modules[0].module_path if project_cfg.modules else None)
        mod_cfg = next(
            (m for m in project_cfg.modules if m.module_path == target_module),
            project_cfg.modules[0] if project_cfg.modules else None,
        )
        if mod_cfg is None:
            print_error("No module configuration found.")
            raise typer.Exit(1)

        try:
            result = validate_excel(file, mod_cfg)
        except DoorsExcelError as exc:
            print_error(str(exc))
            raise typer.Exit(1) from exc

        print_validation_result(result, quiet=quiet)
        if result.has_errors:
            raise typer.Exit(1)


# ---------------------------------------------------------------------------
# export (stub)
# ---------------------------------------------------------------------------

@app.command()
def export(
    config: Annotated[Path, typer.Option("--config", "-c", help="Config file.")],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output Excel path."),
    ] = None,
) -> None:
    """Export a DOORS module to Excel. [Not yet implemented]"""
    print_error("export command is not yet implemented.")
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# import (stub) — named import-mod to avoid shadowing Python built-in
# ---------------------------------------------------------------------------

@app.command(name="import")
def import_mod(
    file: Annotated[Path, typer.Option("--file", "-f", help="Excel file to import.")],
    config: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Config file."),
    ] = None,
    policy: Annotated[
        str,
        typer.Option("--policy", help="Conflict policy: excel-wins|doors-wins|content-based."),
    ] = "excel-wins",
    force: Annotated[
        bool,
        typer.Option("--force", help="Allow purge operations without secondary confirmation."),
    ] = False,
) -> None:
    """Import an Excel file into DOORS. [Not yet implemented]"""
    print_error("import command is not yet implemented.")
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# rollback (stub)
# ---------------------------------------------------------------------------

@app.command()
def rollback(
    session: Annotated[
        Optional[Path],
        typer.Option("--session", help="Path to .session.json file."),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output recovery Excel path."),
    ] = None,
) -> None:
    """Generate a rollback Excel from a session snapshot. [Not yet implemented]"""
    print_error("rollback command is not yet implemented.")
    raise typer.Exit(1)
