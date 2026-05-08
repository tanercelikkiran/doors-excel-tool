"""Headless PySide6 MainWindow smoke tests (QT_QPA_PLATFORM=offscreen)."""
from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_main_window_importable() -> None:
    from doors_excel.gui.main import MainWindow

    assert MainWindow is not None


def test_main_window_instantiable(qt_app) -> None:
    from doors_excel.gui.main import MainWindow

    win = MainWindow()
    assert win.windowTitle() != ""
    win.close()


def test_run_gui_callable() -> None:
    from doors_excel.gui.main import run_gui

    assert callable(run_gui)
