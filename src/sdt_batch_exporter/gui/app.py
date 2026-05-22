"""GUI application launcher."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sdt_batch_exporter.gui.main_window import MainWindow


def run_gui(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    if any(token in {"-h", "--help"} for token in args[1:]):
        print("Usage: sdt-export-gui")
        print("Launch SDT Batch Exporter GUI MVP.")
        return 0
    app = QApplication(args)
    window = MainWindow()
    window.show()
    return app.exec()
