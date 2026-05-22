"""Request/response models for export workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from sdt_batch_exporter.models.export_options import TextExportOptions, ZarrExportOptions

DatasetSelectionMode = Literal["first", "all", "indices"]
ExportStatus = Literal["success", "failed", "skipped"]


@dataclass(frozen=True)
class ExportOutputs:
    zarr: bool = True
    csv: bool = False
    txt: bool = False
    preview_png: bool = False


@dataclass(frozen=True)
class DatasetExportRequest:
    source_path: Path
    output_dir: Path
    dataset_index: int = 0
    outputs: ExportOutputs = field(default_factory=ExportOutputs)
    zarr_options: ZarrExportOptions = field(default_factory=ZarrExportOptions)
    text_options: TextExportOptions = field(default_factory=TextExportOptions)
    preview_figure_options: object | None = None


@dataclass(frozen=True)
class FileExportRequest:
    source_path: Path
    output_dir: Path
    dataset_selection: DatasetSelectionMode = "first"
    dataset_indices: tuple[int, ...] = ()
    outputs: ExportOutputs = field(default_factory=ExportOutputs)
    zarr_options: ZarrExportOptions = field(default_factory=ZarrExportOptions)
    text_options: TextExportOptions = field(default_factory=TextExportOptions)
    preview_figure_options: object | None = None


@dataclass(frozen=True)
class BatchExportRequest:
    source_paths: tuple[Path, ...]
    output_root: Path
    dataset_selection: DatasetSelectionMode = "first"
    dataset_indices: tuple[int, ...] = ()
    outputs: ExportOutputs = field(default_factory=ExportOutputs)
    zarr_options: ZarrExportOptions = field(default_factory=ZarrExportOptions)
    text_options: TextExportOptions = field(default_factory=TextExportOptions)
    preview_figure_options: object | None = None


@dataclass(frozen=True)
class DatasetExportResult:
    source_path: Path
    dataset_index: int
    status: ExportStatus
    output_paths: tuple[Path, ...] = ()
    error_type: str | None = None
    error_message: str | None = None
    duration_s: float = 0.0


@dataclass(frozen=True)
class FileExportResult:
    source_path: Path
    status: ExportStatus
    dataset_results: tuple[DatasetExportResult, ...]
    error_type: str | None = None
    error_message: str | None = None
    duration_s: float = 0.0


@dataclass(frozen=True)
class BatchExportResult:
    status: ExportStatus
    file_results: tuple[FileExportResult, ...]
    success_count: int
    failed_count: int
    skipped_count: int
    duration_s: float = 0.0
