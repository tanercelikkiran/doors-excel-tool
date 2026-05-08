"""Tests for cli/app.py — Typer commands via CliRunner."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
from typer.testing import CliRunner

from doors_excel.cli.app import app

runner = CliRunner()


def _write_valid_config(tmp_path: Path) -> Path:
    data = {
        "modules": [
            {
                "module_path": "/proj/mod",
                "column_mappings": [
                    {"column": "Object Text", "attribute": "Object Text",
                     "attribute_type": "Text"},
                    {"column": "Short Name", "attribute": "Short Name",
                     "attribute_type": "String"},
                ],
            }
        ]
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _write_valid_xlsx(tmp_path: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "mod"
    ws.append(["Absolute Number", "Object Text", "Short Name"])
    ws.append([10, "Hello", "hi"])
    p = tmp_path / "data.xlsx"
    wb.save(p)
    return p


# ---------------------------------------------------------------------------
# validate — config only
# ---------------------------------------------------------------------------

class TestValidateConfigOnly:
    def test_valid_config_exits_zero(self, tmp_path: Path) -> None:
        cfg = _write_valid_config(tmp_path)
        result = runner.invoke(app, ["validate", "--config", str(cfg)])
        assert result.exit_code == 0

    def test_missing_config_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["validate", "--config", str(tmp_path / "missing.json")])
        assert result.exit_code == 1

    def test_bad_json_config_exits_one(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{broken", encoding="utf-8")
        result = runner.invoke(app, ["validate", "--config", str(p)])
        assert result.exit_code == 1

    def test_no_args_exits_nonzero(self) -> None:
        result = runner.invoke(app, ["validate"])
        assert result.exit_code != 0

    def test_quiet_suppresses_ok_message(self, tmp_path: Path) -> None:
        cfg = _write_valid_config(tmp_path)
        result = runner.invoke(app, ["validate", "--config", str(cfg), "--quiet"])
        assert result.exit_code == 0
        assert "Config OK" not in result.output


# ---------------------------------------------------------------------------
# validate — config + file
# ---------------------------------------------------------------------------

class TestValidateWithFile:
    def test_valid_xlsx_exits_zero(self, tmp_path: Path) -> None:
        cfg = _write_valid_config(tmp_path)
        xlsx = _write_valid_xlsx(tmp_path)
        result = runner.invoke(app, ["validate", "--config", str(cfg), "--file", str(xlsx)])
        assert result.exit_code == 0

    def test_file_without_config_exits_one(self, tmp_path: Path) -> None:
        xlsx = _write_valid_xlsx(tmp_path)
        result = runner.invoke(app, ["validate", "--file", str(xlsx)])
        assert result.exit_code == 1

    def test_xlsx_with_invalid_string_exits_one(self, tmp_path: Path) -> None:
        cfg = _write_valid_config(tmp_path)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "mod"
        ws.append(["Absolute Number", "Object Text", "Short Name"])
        ws.append([10, "ok", "x" * 1025])  # too long for String
        p = tmp_path / "bad.xlsx"
        wb.save(p)
        result = runner.invoke(app, ["validate", "--config", str(cfg), "--file", str(p)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Stub commands (import is still a stub; export + rollback are real)
# ---------------------------------------------------------------------------

class TestStubCommands:
    def test_import_exits_one(self, tmp_path: Path) -> None:
        xlsx = _write_valid_xlsx(tmp_path)
        result = runner.invoke(app, ["import", "--file", str(xlsx)])
        assert result.exit_code == 1

    def test_gui_command_exists(self) -> None:
        result = runner.invoke(app, ["gui", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# export (real implementation)
# ---------------------------------------------------------------------------

class TestExportCommand:
    def test_export_succeeds_with_mocked_api(self, tmp_path: Path) -> None:
        cfg = _write_valid_config(tmp_path)
        out = tmp_path / "out.xlsx"
        with patch("doors_excel.cli.app.DoorsConnection") as MockConn, \
             patch("doors_excel.cli.app.export_module_api", return_value=out):
            MockConn.open.return_value = MagicMock()
            result = runner.invoke(app, ["export", "--config", str(cfg), "--output", str(out)])
        assert result.exit_code == 0

    def test_export_missing_config_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["export", "--config", str(tmp_path / "missing.json"), "--output", str(tmp_path / "out.xlsx")],
        )
        assert result.exit_code == 1

    def test_export_doors_unavailable_exits_one(self, tmp_path: Path) -> None:
        cfg = _write_valid_config(tmp_path)
        out = tmp_path / "out.xlsx"
        with patch("doors_excel.cli.app.DoorsConnection") as MockConn:
            MockConn.open.side_effect = Exception("COM unavailable")
            result = runner.invoke(app, ["export", "--config", str(cfg), "--output", str(out)])
        assert result.exit_code == 1

    def test_export_quiet_suppresses_success_message(self, tmp_path: Path) -> None:
        cfg = _write_valid_config(tmp_path)
        out = tmp_path / "out.xlsx"
        with patch("doors_excel.cli.app.DoorsConnection") as MockConn, \
             patch("doors_excel.cli.app.export_module_api", return_value=out):
            MockConn.open.return_value = MagicMock()
            result = runner.invoke(
                app,
                ["export", "--config", str(cfg), "--output", str(out), "--quiet"],
            )
        assert result.exit_code == 0
        assert "Exported" not in result.output


# ---------------------------------------------------------------------------
# rollback (real implementation)
# ---------------------------------------------------------------------------

class TestRollbackCommand:
    def test_rollback_succeeds_with_mocked_api(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test.db")
        session_file = tmp_path / ".doors_session.json"
        session_file.write_text(
            json.dumps({"session_id": "s1", "db_path": db_path}), encoding="utf-8"
        )
        out = tmp_path / "rollback.xlsx"
        with patch("doors_excel.cli.app.generate_rollback_excel_api", return_value=out):
            result = runner.invoke(
                app,
                ["rollback", "--session", str(session_file), "--output", str(out)],
            )
        assert result.exit_code == 0

    def test_rollback_missing_session_file_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["rollback", "--session", str(tmp_path / "no.json")],
        )
        assert result.exit_code == 1
