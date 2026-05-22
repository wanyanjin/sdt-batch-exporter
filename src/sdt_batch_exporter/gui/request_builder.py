"""Build workflow requests from GUI state."""

from __future__ import annotations

from pathlib import Path

from sdt_batch_exporter.gui.preview_compositor import PreviewFigureOptions
from sdt_batch_exporter.models.export_options import (
    ChunkStrategy,
    CompressionProfile,
    TextExportOptions,
    ZarrExportOptions,
)
from sdt_batch_exporter.models.workflow import (
    BatchExportRequest,
    DatasetSelectionMode,
    ExportOutputs,
)


def parse_dataset_indices(indices_text: str) -> tuple[int, ...]:
    if not indices_text.strip():
        return ()
    values: list[int] = []
    for token in indices_text.split(","):
        part = token.strip()
        if not part:
            raise ValueError("Invalid indices format")
        try:
            value = int(part)
        except ValueError as exc:
            raise ValueError("Invalid indices format") from exc
        if value < 0:
            raise ValueError("Dataset indices must be non-negative integers")
        values.append(value)
    return tuple(values)


def build_batch_request(
    source_paths: tuple[Path, ...],
    output_root: Path,
    *,
    export_zarr: bool,
    export_csv: bool,
    export_txt: bool,
    export_preview_png: bool,
    dataset_selection: DatasetSelectionMode,
    dataset_indices: tuple[int, ...],
    compression_profile: CompressionProfile,
    chunk_strategy: ChunkStrategy,
    overwrite: bool,
    preview_figure_options: PreviewFigureOptions | None,
) -> BatchExportRequest:
    if not source_paths:
        raise ValueError("No source files selected")
    if not (export_zarr or export_csv or export_txt or export_preview_png):
        raise ValueError("At least one output format must be enabled.")
    if dataset_selection == "indices" and not dataset_indices:
        raise ValueError("Dataset selection 'indices' requires at least one index")
    if dataset_selection != "indices" and dataset_indices:
        raise ValueError("Dataset indices are only valid when selection is 'indices'")

    return BatchExportRequest(
        source_paths=source_paths,
        output_root=output_root,
        dataset_selection=dataset_selection,
        dataset_indices=dataset_indices,
        outputs=ExportOutputs(
            zarr=export_zarr,
            csv=export_csv,
            txt=export_txt,
            preview_png=export_preview_png,
        ),
        zarr_options=ZarrExportOptions(
            compression_profile=compression_profile,
            chunk_strategy=chunk_strategy,
            overwrite=overwrite,
        ),
        text_options=TextExportOptions(overwrite=overwrite),
        preview_figure_options=preview_figure_options,
    )
