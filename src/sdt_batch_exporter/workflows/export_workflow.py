"""Workflow orchestration for SDT export pipeline."""

from __future__ import annotations

import contextlib
from pathlib import Path
from time import perf_counter
from typing import cast

from sdt_batch_exporter.gui.png_exporter import export_preview_png_for_preview
from sdt_batch_exporter.gui.preview_compositor import PreviewFigureOptions
from sdt_batch_exporter.models.workflow import (
    BatchExportRequest,
    BatchExportResult,
    DatasetExportRequest,
    DatasetExportResult,
    ExportStatus,
    FileExportRequest,
    FileExportResult,
)
from sdt_batch_exporter.storage.sdt_reader import (
    build_preview_from_dataset_data,
    load_sdt_dataset,
    read_sdt_summary,
)
from sdt_batch_exporter.storage.text_exporter import export_intensity_csv, export_intensity_txt
from sdt_batch_exporter.storage.zarr_writer import export_dataset_to_zarr


def export_dataset(request: DatasetExportRequest) -> DatasetExportResult:
    started = perf_counter()
    try:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        dataset_data = load_sdt_dataset(request.source_path, request.dataset_index)
        preview_data = build_preview_from_dataset_data(dataset_data)
        prefix = _dataset_output_prefix(request.source_path, request.dataset_index)

        output_paths: list[Path] = []
        if request.outputs.zarr:
            zarr_path = request.output_dir / f"{prefix}.zarr"
            output_paths.append(
                export_dataset_to_zarr(dataset_data, preview_data, zarr_path, request.zarr_options)
            )
        if request.outputs.csv:
            csv_path = request.output_dir / f"{prefix}_intensity.csv"
            output_paths.append(
                export_intensity_csv(preview_data, csv_path, options=request.text_options)
            )
        if request.outputs.txt:
            txt_path = request.output_dir / f"{prefix}_intensity.txt"
            output_paths.append(
                export_intensity_txt(preview_data, txt_path, options=request.text_options)
            )
        if request.outputs.preview_png:
            if request.preview_figure_options is None:
                raise ValueError("Preview PNG export requires preview figure options.")
            png_path = request.output_dir / f"{prefix}_preview.png"
            output_paths.append(
                export_preview_png_for_preview(
                    preview_data,
                    png_path,
                    options=cast(PreviewFigureOptions, request.preview_figure_options),
                    overwrite=request.zarr_options.overwrite,
                )
            )

        return DatasetExportResult(
            source_path=request.source_path,
            dataset_index=request.dataset_index,
            status="success",
            output_paths=tuple(output_paths),
            duration_s=perf_counter() - started,
        )
    except Exception as exc:
        return DatasetExportResult(
            source_path=request.source_path,
            dataset_index=request.dataset_index,
            status="failed",
            error_type=type(exc).__name__,
            error_message=_format_export_error_message(exc),
            duration_s=perf_counter() - started,
        )


def export_file(request: FileExportRequest) -> FileExportResult:
    started = perf_counter()
    try:
        summary = read_sdt_summary(request.source_path)
    except Exception as exc:
        return FileExportResult(
            source_path=request.source_path,
            status="failed",
            dataset_results=(),
            error_type=type(exc).__name__,
            error_message=_format_export_error_message(exc),
            duration_s=perf_counter() - started,
        )

    dataset_indices = _resolve_dataset_indices(
        request.dataset_selection,
        request.dataset_indices,
        summary.dataset_count,
    )
    dataset_results = tuple(
        export_dataset(
            DatasetExportRequest(
                source_path=request.source_path,
                output_dir=request.output_dir,
                dataset_index=dataset_index,
                outputs=request.outputs,
                zarr_options=request.zarr_options,
                text_options=request.text_options,
                preview_figure_options=request.preview_figure_options,
            )
        )
        for dataset_index in dataset_indices
    )
    file_status: ExportStatus = (
        "success"
        if dataset_results and all(result.status == "success" for result in dataset_results)
        else "failed"
    )
    if not dataset_results:
        file_status = "skipped"
    result = FileExportResult(
        source_path=request.source_path,
        status=file_status,
        dataset_results=dataset_results,
        error_type=_collapse_file_error_type(dataset_results),
        error_message=_collapse_file_error_message(dataset_results),
        duration_s=perf_counter() - started,
    )
    if result.status == "failed":
        _cleanup_empty_output_dir(request.output_dir)
    return result


def export_batch(request: BatchExportRequest) -> BatchExportResult:
    started = perf_counter()
    file_results: list[FileExportResult] = []
    for source_path in request.source_paths:
        file_output_dir = request.output_root / source_path.stem
        try:
            result = export_file(
                FileExportRequest(
                    source_path=source_path,
                    output_dir=file_output_dir,
                    dataset_selection=request.dataset_selection,
                    dataset_indices=request.dataset_indices,
                outputs=request.outputs,
                zarr_options=request.zarr_options,
                text_options=request.text_options,
                preview_figure_options=request.preview_figure_options,
            )
        )
        except Exception as exc:
            result = FileExportResult(
                source_path=source_path,
                status="failed",
                dataset_results=(),
                error_type=type(exc).__name__,
                error_message=_format_export_error_message(exc),
                duration_s=0.0,
            )
        file_results.append(result)

    success_count = sum(1 for result in file_results if result.status == "success")
    failed_count = sum(1 for result in file_results if result.status == "failed")
    skipped_count = sum(1 for result in file_results if result.status == "skipped")
    batch_status: ExportStatus = "success" if failed_count == 0 and file_results else "failed"
    if file_results and skipped_count == len(file_results):
        batch_status = "skipped"

    return BatchExportResult(
        status=batch_status,
        file_results=tuple(file_results),
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        duration_s=perf_counter() - started,
    )


def _dataset_output_prefix(source_path: Path, dataset_index: int) -> str:
    return f"{source_path.stem}_dataset{dataset_index:03d}"


def _resolve_dataset_indices(
    selection: str, indices: tuple[int, ...], dataset_count: int
) -> tuple[int, ...]:
    if selection == "first":
        return (0,)
    if selection == "all":
        return tuple(range(dataset_count))
    if selection == "indices":
        return indices
    raise ValueError(f"Unsupported dataset selection mode: {selection}")


def _collapse_file_error_type(
    dataset_results: tuple[DatasetExportResult, ...],
) -> str | None:
    failed_results = [result for result in dataset_results if result.status == "failed"]
    if not failed_results:
        return None
    error_types = {result.error_type for result in failed_results if result.error_type}
    if len(error_types) == 1:
        return next(iter(error_types))
    return "DatasetExportFailed"


def _collapse_file_error_message(
    dataset_results: tuple[DatasetExportResult, ...],
) -> str | None:
    failed_results = [result for result in dataset_results if result.status == "failed"]
    if not failed_results:
        return None
    if len(failed_results) == 1:
        return failed_results[0].error_message
    summaries = [
        f"dataset {result.dataset_index}: {result.error_type}: {result.error_message}"
        for result in failed_results
    ]
    return "; ".join(summaries)


def _format_export_error_message(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    if isinstance(exc, (PermissionError, FileExistsError, OSError, RuntimeError)):
        lowered = message.casefold()
        if any(token in lowered for token in ("lock", "onedrive", "file explorer", "permission")):
            return (
                f"{message} "
                "This usually indicates that the output directory is locked by OneDrive, "
                "File Explorer preview, or another application. Try a local non-synced "
                "output directory and retry."
            )
    return message


def _cleanup_empty_output_dir(output_dir: Path) -> None:
    if not output_dir.exists() or not output_dir.is_dir():
        return
    try:
        next(output_dir.iterdir())
        return
    except StopIteration:
        pass
    except OSError:
        return
    with contextlib.suppress(OSError):
        output_dir.rmdir()
