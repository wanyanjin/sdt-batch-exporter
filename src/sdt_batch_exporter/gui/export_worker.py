"""Background worker for running export workflow."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from sdt_batch_exporter.models.workflow import BatchExportRequest, BatchExportResult
from sdt_batch_exporter.workflows.export_workflow import export_batch


class ExportWorker(QObject):
    """Run batch export in a background thread."""

    finished = Signal(object)
    failed = Signal(str)
    log_message = Signal(str)
    progress_changed = Signal(int, int)

    def __init__(self, request: BatchExportRequest) -> None:
        super().__init__()
        self._request = request

    def run(self) -> None:
        try:
            total = len(self._request.source_paths)
            self.log_message.emit(f"Started export for {total} file(s).")
            self.progress_changed.emit(0, max(1, total))
            result: BatchExportResult = export_batch(self._request)
            self.log_message.emit(
                "Export finished. "
                f"Success: {result.success_count}, Failed: {result.failed_count}, "
                f"Skipped: {result.skipped_count}."
            )
            self.progress_changed.emit(total, max(1, total))
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
