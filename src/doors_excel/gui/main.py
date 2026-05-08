"""PySide6 MainWindow stub — full implementation in a future task."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    """Top-level application window (stub)."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DOORS ↔ Excel")
        self.resize(900, 600)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("DOORS ↔ Excel synchronisation tool\n(GUI not yet implemented)"))
        self.setCentralWidget(central)


def run_gui() -> None:
    """Launch the PySide6 application. Blocks until the window is closed."""
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
