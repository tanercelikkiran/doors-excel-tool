"""Tests for the __main__.py Typer stub entry point."""
from __future__ import annotations

import typer
from typer.testing import CliRunner

from doors_excel.__main__ import app

runner = CliRunner()


class TestMainEntryPoint:
    def test_app_is_typer_instance(self) -> None:
        assert isinstance(app, typer.Typer)

    def test_help_exits_cleanly(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_mentions_doors_or_excel(self) -> None:
        result = runner.invoke(app, ["--help"])
        output = result.output.lower()
        assert "doors" in output or "excel" in output

    def test_invoke_without_args_no_unhandled_exception(self) -> None:
        result = runner.invoke(app, [])
        assert result.exception is None or result.exit_code in (0, 2)
