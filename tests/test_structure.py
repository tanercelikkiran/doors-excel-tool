"""Verify every required package directory and __init__.py exists."""
from pathlib import Path

SRC = Path(__file__).parent.parent / "src" / "doors_excel"

REQUIRED_PACKAGES = [
    SRC,
    SRC / "api",
    SRC / "cli",
    SRC / "gui",
    SRC / "core",
    SRC / "core" / "diff",
    SRC / "core" / "transformation",
    SRC / "core" / "validation",
    SRC / "infrastructure",
    SRC / "infrastructure" / "doors",
    SRC / "infrastructure" / "excel",
    SRC / "infrastructure" / "database",
    SRC / "common",
    SRC / "resources",
]

REQUIRED_TEST_DIRS = [
    Path(__file__).parent / "unit",
    Path(__file__).parent / "integration",
]


def test_all_package_inits_exist() -> None:
    missing = [str(p) for p in REQUIRED_PACKAGES if not (p / "__init__.py").is_file()]
    assert not missing, f"Missing __init__.py in: {missing}"


def test_test_directories_exist() -> None:
    missing = [str(p) for p in REQUIRED_TEST_DIRS if not p.is_dir()]
    assert not missing, f"Missing test directories: {missing}"


def test_conftest_exists() -> None:
    assert (Path(__file__).parent / "conftest.py").is_file()
