"""File table widget for displaying loaded SDT files with status."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class FileTable(QWidget):
    """QTableWidget showing Name / Path / Status / Outputs for loaded SDT files."""

    file_selected = Signal(Path, int)  # (source_path, dataset_index=0)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paths: list[Path] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels(["Name", "Path", "Status", "Outputs"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(0, 360)
        self._table.setColumnWidth(2, 100)
        self._table.setColumnWidth(3, 180)
        self._table.verticalHeader().setVisible(False)
        self._table.currentCellChanged.connect(self._on_current_cell_changed)
        layout.addWidget(self._table)

    def add_path(self, path: Path) -> bool:
        """Add a path if not already present. Returns True if added."""
        resolved = path.resolve()
        if resolved in self._paths:
            return False
        self._paths.append(resolved)
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(resolved.name))
        self._table.setItem(row, 1, QTableWidgetItem(str(resolved)))
        self._table.setItem(row, 2, QTableWidgetItem("pending"))
        self._table.setItem(row, 3, QTableWidgetItem("-"))
        return True

    def clear_paths(self) -> None:
        """Remove all rows."""
        self._paths.clear()
        self._table.setRowCount(0)

    def set_status(self, path: Path, status: str) -> None:
        """Update the Status cell for a given path."""
        resolved = path.resolve()
        try:
            row = self._paths.index(resolved)
        except ValueError:
            return
        item = self._table.item(row, 2)
        if item is not None:
            item.setText(status)

    def get_paths(self) -> tuple[Path, ...]:
        """Return all loaded paths in order."""
        return tuple(self._paths)

    def set_outputs(self, path: Path, outputs: str) -> None:
        """Update the Outputs cell for a given path."""
        resolved = path.resolve()
        try:
            row = self._paths.index(resolved)
        except ValueError:
            return
        item = self._table.item(row, 3)
        if item is not None:
            item.setText(outputs or "-")

    def get_outputs(self, path: Path) -> tuple[str, ...]:
        """Return parsed output labels for a given path."""
        resolved = path.resolve()
        try:
            row = self._paths.index(resolved)
        except ValueError:
            return ()
        item = self._table.item(row, 3)
        if item is None:
            return ()
        text = item.text().strip()
        if not text or text == "-":
            return ()
        return tuple(part.strip() for part in text.split(",") if part.strip())

    def _on_current_cell_changed(self, current_row: int, _cc: int, _pr: int, _pc: int) -> None:
        if 0 <= current_row < len(self._paths):
            self.file_selected.emit(self._paths[current_row], 0)
