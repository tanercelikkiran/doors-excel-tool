"""Tests that pyproject.toml metadata is well-formed and importable as a package."""
import importlib.metadata
import sys
from pathlib import Path


def test_package_name_importable() -> None:
    meta = importlib.metadata.metadata("doors-excel-tool")
    assert meta["Name"] == "doors-excel-tool"


def test_python_version_constraint() -> None:
    assert sys.version_info >= (3, 10), "Python 3.10+ required"


def test_main_py_exists() -> None:
    root = Path(__file__).parent.parent
    assert (root / "main.py").is_file()


def test_readme_exists() -> None:
    root = Path(__file__).parent.parent
    assert (root / "README.md").is_file()
