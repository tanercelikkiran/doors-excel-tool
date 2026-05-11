"""Typer CLI application for doors-excel-tool (REQ-INF-001, REQ-INF-002).

Commands
--------
validate    Validate a config file and/or an Excel file (fully implemented).
export      Export a DOORS module to Excel (fully implemented).
import-mod  Import an Excel file into DOORS (stub — not yet implemented).
rollback    Generate a rollback Excel from a session snapshot (fully implemented).
"""
from __future__ import annotations

from __future__ import annotations

import sqlite3 as _sqlite3
from pathlib import Path
from typing import Annotated, Optional

import typer

from doors_excel.api.diff import run_diff as _run_diff_api
from doors_excel.api.export import export_module as export_module_api
from doors_excel.api.import_ import execute_import as execute_import_api
from doors_excel.api.import_ import stage_import as stage_import_api
from doors_excel.api.rollback import generate_rollback_excel as generate_rollback_excel_api
from doors_excel.api.sessions import SessionManager as _SessionMgr, session_file_path
from doors_excel.cli.output import console, print_error, print_validation_result, print_diff_summary
from doors_excel.common.exceptions import ConfigurationError, DoorsExcelError, SessionError
from doors_excel.infrastructure.database.schema import apply_schema as _apply_schema
from doors_excel.infrastructure.doors.connection import DoorsConnection
from doors_excel.infrastructure.doors.keepalive import KeepAliveWatchdog

app = typer.Typer(
    name="doors-excel",
    help="Bidirectional synchronization between IBM DOORS and Microsoft Excel.",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_children_in_doors(
    conn: object, module_path: str, db_conn: _sqlite3.Connection, session_id: str
) -> int:
    """Estimate cascading deletes by counting staging_doors rows whose parent_id is being deleted.

    Returns 0 on any failure (non-fatal — warning is best-effort).
    """
    try:
        deleted_rows = db_conn.execute(
            "SELECT DISTINCT object_id FROM diff_results WHERE session_id = ? AND change_type = 'DELETED'",
            (session_id,),
        ).fetchall()
        object_ids = [r["object_id"] for r in deleted_rows if r["object_id"] is not None]
        if not object_ids:
            return 0

        placeholders = ",".join("?" * len(object_ids))
        child_rows = db_conn.execute(
            f"SELECT COUNT(DISTINCT object_id) as cnt FROM staging_doors "
            f"WHERE session_id = ? AND parent_id IN ({placeholders})",
            [session_id] + object_ids,
        ).fetchone()
        return child_rows["cnt"] if child_rows else 0
    except Exception:
        return 0


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
# export
# ---------------------------------------------------------------------------

@app.command()
def export(
    config: Annotated[Path, typer.Option("--config", "-c", help="Config file.")],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output Excel path."),
    ] = None,
    module: Annotated[
        Optional[str],
        typer.Option("--module", "-m", help="DOORS module path (overrides config)."),
    ] = None,
    baseline: Annotated[
        str,
        typer.Option("--baseline", help="DOORS baseline to export (default: current)."),
    ] = "current",
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-error output."),
    ] = False,
) -> None:
    """Export a DOORS module to Excel."""
    from doors_excel.api.validate import validate_config

    try:
        project_cfg = validate_config(config)
    except ConfigurationError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc

    mod_cfg = next(
        (m for m in project_cfg.modules if module is None or m.module_path == module),
        project_cfg.modules[0] if project_cfg.modules else None,
    )
    if mod_cfg is None:
        print_error("No module configuration found.")
        raise typer.Exit(1)

    out_path = output or Path(mod_cfg.module_path.rstrip("/").rsplit("/", 1)[-1] + ".xlsx")

    try:
        conn = DoorsConnection.open()
    except Exception as exc:
        print_error(f"Cannot connect to DOORS: {exc}")
        raise typer.Exit(1) from exc

    db_path = out_path.with_suffix(".db")
    session_mgr = _SessionMgr(db_path)
    watchdog = KeepAliveWatchdog(conn.run_dxl)
    watchdog.start()
    try:
        result_path = export_module_api(
            mod_cfg.module_path,
            mod_cfg,
            out_path,
            doors_conn=conn,
            baseline=baseline,
            session_manager=session_mgr,
        )
    except DoorsExcelError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    finally:
        watchdog.stop()
        session_mgr.close()
        conn.close()

    if not quiet:
        console.print(f"[bold green]Exported[/] → {result_path}")


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
    include_new: Annotated[
        bool,
        typer.Option("--include-new", help="Create NEW objects (rows with no Absolute Number) in DOORS."),
    ] = False,
    deletion_policy: Annotated[
        str,
        typer.Option("--deletion-policy", help="How to handle deleted rows: ignore|soft-delete|purge."),
    ] = "ignore",
    accept_ole_overwrites: Annotated[
        bool,
        typer.Option("--accept-ole-overwrites", help="Allow updates to objects that contain embedded OLE objects (images, files)."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-error output."),
    ] = False,
    resume: Annotated[
        bool,
        typer.Option("--resume", help="Resume an interrupted import using the existing session file."),
    ] = False,
    discard_session: Annotated[
        bool,
        typer.Option("--discard-session", help="Discard any leftover session file and start fresh."),
    ] = False,
) -> None:
    """Import an Excel file into DOORS."""
    if config is None:
        print_error("--config is required for import.")
        raise typer.Exit(1)

    from doors_excel.api.validate import validate_config

    try:
        project_cfg = validate_config(config)
    except ConfigurationError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc

    mod_cfg = next(iter(project_cfg.modules), None)
    if mod_cfg is None:
        print_error("No module configuration found.")
        raise typer.Exit(1)

    sf = session_file_path(file)

    if resume and discard_session:
        print_error("--resume and --discard-session are mutually exclusive.")
        raise typer.Exit(1)

    if resume and not sf.exists():
        print_error(f"No session file found at {sf}. Cannot resume.")
        raise typer.Exit(1)

    if sf.exists():
        if discard_session:
            sf.unlink(missing_ok=True)
            # Also remove the companion DB to start truly fresh
            _db_for_discard = file.parent / (file.stem + ".db")
            _db_for_discard.unlink(missing_ok=True)
        elif resume:
            # Validate the existing session (checks SHA-256 of Excel file)
            _mgr = _SessionMgr(file.parent / (file.stem + ".db"))
            try:
                _resume_info = _mgr.resume(sf)
            except SessionError as exc:
                print_error(f"Cannot resume session: {exc}")
                raise typer.Exit(1) from exc
            finally:
                _mgr.close()
            # Fast path: skip staging, use existing diff in the DB
            _resume_db_path = _resume_info.db_path
            _resume_session_id = _resume_info.session_id
            # Re-open DB and compute stats from existing diff

            _rconn = _sqlite3.connect(str(_resume_db_path))
            _rconn.row_factory = _sqlite3.Row
            _apply_schema(_rconn)
            try:
                _rstats = _run_diff_api(_rconn, _resume_session_id)
            finally:
                _rconn.close()

            print_diff_summary(_rstats, quiet=quiet)
            if not quiet:
                console.print("[dim]Resuming session validated. Re-run without --resume to apply changes.[/]")

            # For now resume exits here (full execute-on-resume is a future task)
            raise typer.Exit(0)
        else:
            print_error(
                f"A previous session file exists at {sf}. "
                "Use --resume to continue it or --discard-session to start fresh."
            )
            raise typer.Exit(1)

    try:
        conn = DoorsConnection.open()
    except Exception as exc:
        print_error(f"Cannot connect to DOORS: {exc}")
        raise typer.Exit(1) from exc

    db_path = file.parent / (file.stem + ".db")

    try:
        session_id, stats = stage_import_api(
            file,
            mod_cfg,
            db_path=db_path,
            doors_conn=conn,
            trim_whitespace=project_cfg.trim_whitespace,
        )
    except DoorsExcelError as exc:
        print_error(str(exc))
        conn.close()
        raise typer.Exit(1) from exc

    print_diff_summary(stats, quiet=quiet)

    if deletion_policy == "purge" and not force:
        print_error("--deletion-policy purge requires --force flag.")
        conn.close()
        raise typer.Exit(1)

    if stats.conflict_count > 0 and policy != "excel-wins":
        print_error(
            f"{stats.conflict_count} conflict(s) found. "
            "Use --policy excel-wins to apply Excel values, or resolve manually."
        )
        conn.close()
        raise typer.Exit(1)

    db_conn = _sqlite3.connect(str(db_path))
    db_conn.row_factory = _sqlite3.Row
    _apply_schema(db_conn)

    # Show cascading delete warning before purge
    if deletion_policy == "purge" and stats.deleted_count > 0 and not quiet:
        _child_count = _count_children_in_doors(conn, mod_cfg.module_path, db_conn, session_id)
        if _child_count > 0:
            console.print(
                f"[bold yellow]Warning:[/] Purging {stats.deleted_count} object(s) will cascade-delete "
                f"[bold]{_child_count}[/] children."
            )

    watchdog = KeepAliveWatchdog(conn.run_dxl)
    watchdog.start()
    try:
        applied = execute_import_api(
            session_id, db_conn,
            doors_conn=conn,
            conflict_policy=policy,
            module_config=mod_cfg,
            include_new=include_new,
            deletion_policy=deletion_policy,
            accept_ole_overwrites=accept_ole_overwrites,
        )
    except DoorsExcelError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    finally:
        watchdog.stop()
        db_conn.close()
        conn.close()

    if not quiet:
        console.print(f"[bold green]Applied[/] {applied} change(s) → {mod_cfg.module_path}")


# ---------------------------------------------------------------------------
# rollback
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
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-error output."),
    ] = False,
) -> None:
    """Generate a rollback Excel from a session snapshot."""
    if session is None or not session.exists():
        print_error(
            "Provide --session pointing to a valid .session.json file."
            if session is None
            else f"Session file not found: {session}"
        )
        raise typer.Exit(1)

    import json
    import sqlite3

    try:
        data = json.loads(session.read_text(encoding="utf-8"))
        session_id = data["session_id"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print_error(f"Cannot read session file: {exc}")
        raise typer.Exit(1) from exc

    db_path_str = data.get("db_path")
    if db_path_str is None:
        print_error("Session file does not contain a db_path field.")
        raise typer.Exit(1)

    out_path = output or (session.parent / "rollback.xlsx")

    from doors_excel.infrastructure.database.schema import apply_schema

    conn = sqlite3.connect(db_path_str)
    conn.row_factory = sqlite3.Row
    apply_schema(conn)

    try:
        result_path = generate_rollback_excel_api(session_id, conn, out_path)
    except DoorsExcelError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from exc
    finally:
        conn.close()

    if not quiet:
        console.print(f"[bold green]Rollback Excel[/] → {result_path}")


# ---------------------------------------------------------------------------
# gui
# ---------------------------------------------------------------------------

@app.command()
def gui() -> None:
    """Launch the PySide6 graphical user interface."""
    try:
        from doors_excel.gui.main import run_gui

        run_gui()
    except ImportError as exc:
        print_error(f"PySide6 is not installed: {exc}")
        raise typer.Exit(1) from exc
