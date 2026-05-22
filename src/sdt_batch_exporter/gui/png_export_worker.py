"""Sequential background worker for preview PNG export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, Signal

from sdt_batch_exporter.gui.png_exporter import export_preview_png_for_sdt
from sdt_batch_exporter.gui.preview_compositor import PreviewFigureOptions


@dataclass(frozen=True)
class PreviewPngExportJob:
    source_path: Path
    output_path: Path
    dataset_index: int
    options: PreviewFigureOptions
    overwrite: bool = False


@dataclass(frozen=True)
class PreviewPngExportResult:
    source_path: Path
    output_path: Path | None
    status: Literal["success", "failed"]
    error_message: str | None = None


class PngExportWorker(QObject):
    """Run preview PNG export jobs sequentially in a worker thread."""

    finished = Signal(object)
    failed = Signal(str)
    log_message = Signal(str)
    progress_changed = Signal(int, int)

    def __init__(self, jobs: tuple[PreviewPngExportJob, ...]) -> None:
        super().__init__()
        self._jobs = jobs

    def run(self) -> None:
        try:
            total = len(self._jobs)
            results: list[PreviewPngExportResult] = []
            self.log_message.emit(f"Started preview PNG export for {total} file(s).")
            self.progress_changed.emit(0, max(1, total))
            for index, job in enumerate(self._jobs, start=1):
                try:
                    output_path = export_preview_png_for_sdt(
                        job.source_path,
                        job.output_path,
                        dataset_index=job.dataset_index,
                        options=job.options,
                        overwrite=job.overwrite,
                    )
                    self.log_message.emit(
                        f"Preview PNG saved: {job.source_path.name} -> {output_path}"
                    )
                    results.append(
                        PreviewPngExportResult(
                            source_path=job.source_path,
                            output_path=output_path,
                            status="success",
                        )
                    )
                except Exception as exc:
                    message = f"{type(exc).__name__}: {exc}"
                    self.log_message.emit(
                        f"Preview PNG failed: {job.source_path.name} -> {message}"
                    )
                    results.append(
                        PreviewPngExportResult(
                            source_path=job.source_path,
                            output_path=None,
                            status="failed",
                            error_message=message,
                        )
                    )
                self.progress_changed.emit(index, max(1, total))
            self.finished.emit(tuple(results))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
