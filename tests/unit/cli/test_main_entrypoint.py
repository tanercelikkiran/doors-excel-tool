"""Tests that all subcommands are reachable via the CLI app."""
from __future__ import annotations

from typer.testing import CliRunner

from doors_excel.cli.app import app

runner = CliRunner()


def test_validate_subcommand_reachable() -> None:
    result = runner.invoke(app, ["validate", "--help"])
    assert result.exit_code == 0
    assert "--config" in result.output


def test_import_subcommand_reachable() -> None:
    result = runner.invoke(app, ["import", "--help"])
    assert result.exit_code == 0


def test_export_subcommand_reachable() -> None:
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0


def test_rollback_subcommand_reachable() -> None:
    result = runner.invoke(app, ["rollback", "--help"])
    assert result.exit_code == 0
