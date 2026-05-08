"""Tests for cli/app.py — Typer commands via CliRunner."""
from __future__ import annotations

import json
from pathlib import Path

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
# Stub commands
# ---------------------------------------------------------------------------

class TestStubCommands:
    def test_export_exits_one(self, tmp_path: Path) -> None:
        cfg = _write_valid_config(tmp_path)
        result = runner.invoke(app, ["export", "--config", str(cfg)])
        assert result.exit_code == 1

    def test_import_exits_one(self, tmp_path: Path) -> None:
        xlsx = _write_valid_xlsx(tmp_path)
        result = runner.invoke(app, ["import", "--file", str(xlsx)])
        assert result.exit_code == 1

    def test_rollback_exits_one(self) -> None:
        result = runner.invoke(app, ["rollback"])
        assert result.exit_code == 1
