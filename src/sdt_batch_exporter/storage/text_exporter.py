"""Text exporters for 2D intensity matrices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import numpy as np

from sdt_batch_exporter.core.metadata_extractor import to_jsonable
from sdt_batch_exporter.models.export_options import TextExportFormat, TextExportOptions
from sdt_batch_exporter.models.sdt import PreviewData


def export_intensity_matrix(
    preview_data: PreviewData,
    output_path: Path | str,
    *,
    export_format: TextExportFormat,
    options: TextExportOptions | None = None,
) -> Path:
    export_options = options or TextExportOptions()
    output = Path(output_path)
    _validate_intensity_exportable(preview_data)
    _validate_format(export_format)
    _validate_suffix(output, export_format)
    output.parent.mkdir(parents=True, exist_ok=True)
    _validate_overwrite(output, export_options.overwrite)

    intensity = cast(np.ndarray, preview_data.intensity)
    delimiter = "," if export_format == "csv" else "\t"
    np.savetxt(output, intensity, delimiter=delimiter, fmt=export_options.fmt)

    if export_options.include_metadata_json:
        metadata = _build_export_metadata(preview_data, export_format)
        metadata_path = output.with_suffix(f"{output.suffix}.meta.json")
        _validate_overwrite(metadata_path, export_options.overwrite)
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return output


def export_intensity_csv(
    preview_data: PreviewData,
    output_path: Path | str,
    *,
    options: TextExportOptions | None = None,
) -> Path:
    return export_intensity_matrix(
        preview_data,
        output_path,
        export_format="csv",
        options=options,
    )


def export_intensity_txt(
    preview_data: PreviewData,
    output_path: Path | str,
    *,
    options: TextExportOptions | None = None,
) -> Path:
    return export_intensity_matrix(
        preview_data,
        output_path,
        export_format="txt",
        options=options,
    )


def _validate_intensity_exportable(preview_data: PreviewData) -> None:
    if preview_data.intensity is None:
        raise ValueError("PreviewData does not contain intensity; cannot export CSV/TXT")
    if preview_data.intensity.ndim != 2:
        raise ValueError("Only 2D intensity matrices can be exported to CSV/TXT")


def _validate_format(export_format: TextExportFormat) -> None:
    if export_format not in {"csv", "txt"}:
        raise ValueError(f"Unsupported text export format: {export_format}")


def _validate_suffix(output: Path, export_format: TextExportFormat) -> None:
    suffix = output.suffix.lower()
    expected = ".csv" if export_format == "csv" else ".txt"
    if suffix != expected:
        raise ValueError(f"Expected {expected} suffix for {export_format} export: {output}")


def _validate_overwrite(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output path already exists: {path}")


def _build_export_metadata(
    preview_data: PreviewData, export_format: TextExportFormat
) -> dict[str, object]:
    intensity = cast(np.ndarray, preview_data.intensity)
    axis_info = preview_data.axis_info
    metadata = {
        "source_file": preview_data.source_path.name,
        "source_path": str(preview_data.source_path.resolve()),
        "dataset_index": preview_data.dataset_index,
        "raw_shape": list(preview_data.raw_shape),
        "intensity_shape": list(intensity.shape),
        "intensity_dtype": str(intensity.dtype),
        "axis_inference_status": axis_info.axis_inference_status,
        "inference_source": axis_info.inference_source,
        "time_axis_index": axis_info.time_axis_index,
        "spatial_axes": list(axis_info.spatial_axes),
        "is_exportable_intensity": axis_info.is_exportable_intensity,
        "skipped_intensity_export": axis_info.skipped_intensity_export,
        "skip_reason": axis_info.skip_reason,
        "export_format": export_format,
        "exporter": "SDT Batch Exporter",
        "preview_summary": preview_data.metadata_summary,
    }
    converted = to_jsonable(metadata)
    if not isinstance(converted, dict):
        raise TypeError("Export metadata conversion failed to produce a dictionary")
    return cast(dict[str, object], converted)
