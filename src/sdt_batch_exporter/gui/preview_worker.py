"""Background worker for generating SDT preview data."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from sdt_batch_exporter.models.sdt import PreviewData


class PreviewWorker(QObject):
    """Run build_preview_data in a background thread."""

    preview_ready = Signal(object)  # emits PreviewData
    preview_failed = Signal(str)

    def __init__(self, source_path: Path, dataset_index: int = 0) -> None:
        super().__init__()
        self._source_path = source_path
        self._dataset_index = dataset_index

    @property
    def source_path(self) -> Path:
        return self._source_path

    @property
    def dataset_index(self) -> int:
        return self._dataset_index

    def run(self) -> None:
        """Called by QThread.started signal."""
        try:
            from sdt_batch_exporter.storage.sdt_reader import build_preview_data

            preview: PreviewData = build_preview_data(self._source_path, self._dataset_index)
            self.preview_ready.emit(preview)
        except Exception as exc:
            self.preview_failed.emit(f"{type(exc).__name__}: {exc}")
