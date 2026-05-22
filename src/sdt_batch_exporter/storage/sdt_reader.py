"""Read-only SDT file adapter and preview data builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from sdtfile import SdtFile

from sdt_batch_exporter.core.axis_resolver import infer_axes
from sdt_batch_exporter.core.intensity import (
    compute_global_decay,
    compute_intensity,
    compute_intensity_stats,
)
from sdt_batch_exporter.core.metadata_extractor import to_jsonable
from sdt_batch_exporter.models.sdt import (
    PreviewData,
    SdtDatasetData,
    SdtDatasetSummary,
    SdtFileSummary,
)


def read_sdt_summary(path: Path | str) -> SdtFileSummary:
    source_path = _validate_sdt_path(path)
    with SdtFile(str(source_path)) as sdt:
        data_items = tuple(cast(Any, sdt.data))
        time_items = tuple(cast(Any, sdt.times))
        datasets = tuple(
            _build_dataset_summary(
                dataset_index,
                data_item,
                _extract_time_length(time_items, dataset_index),
            )
            for dataset_index, data_item in enumerate(data_items)
        )
        return SdtFileSummary(
            source_path=source_path,
            source_file=source_path.name,
            file_size_bytes=source_path.stat().st_size,
            dataset_count=len(datasets),
            datasets=datasets,
            sdt_summary_text=str(sdt),
        )


def load_sdt_dataset(path: Path | str, dataset_index: int = 0) -> SdtDatasetData:
    source_path = _validate_sdt_path(path)
    _validate_dataset_index(dataset_index)

    with SdtFile(str(source_path)) as sdt:
        data_items = tuple(cast(Any, sdt.data))
        time_items = tuple(cast(Any, sdt.times))
        if dataset_index >= len(data_items):
            raise IndexError("dataset_index is out of range")

        data = np.asarray(data_items[dataset_index])
        time_length = _extract_time_length(time_items, dataset_index)
        summary = _build_dataset_summary(dataset_index, data, time_length)
        time = _extract_time_array(time_items, dataset_index, time_length)

        return SdtDatasetData(
            source_path=source_path,
            dataset_index=dataset_index,
            data=data,
            time=time,
            summary=summary,
        )


def build_preview_data(path: Path | str, dataset_index: int = 0) -> PreviewData:
    dataset_data = load_sdt_dataset(path, dataset_index)
    return build_preview_from_dataset_data(dataset_data)


def build_preview_from_dataset_data(dataset_data: SdtDatasetData) -> PreviewData:
    summary = dataset_data.summary
    axis_info = summary.axis_info

    intensity: NDArray[np.generic] | None = None
    global_decay: NDArray[np.generic] | None = None
    intensity_stats: dict[str, object] | None = None

    if axis_info.is_exportable_intensity:
        intensity = compute_intensity(dataset_data.data, axis_info.time_axis_index)
        intensity_stats = compute_intensity_stats(intensity)

    if axis_info.time_axis_index is not None and axis_info.spatial_axes:
        global_decay = compute_global_decay(dataset_data.data, axis_info.spatial_axes)

    metadata_summary_obj = to_jsonable(
        {
            "source_file": dataset_data.source_path.name,
            "file_size_bytes": dataset_data.source_path.stat().st_size,
            "dataset_index": dataset_data.dataset_index,
            "shape": summary.shape,
            "dtype": summary.dtype,
            "time_length": summary.time_length,
            "axis_inference_status": axis_info.axis_inference_status,
            "inference_source": axis_info.inference_source,
            "is_exportable_intensity": axis_info.is_exportable_intensity,
            "skipped_intensity_export": axis_info.skipped_intensity_export,
            "skip_reason": axis_info.skip_reason,
            "intensity_source": "source_2d_dataset" if len(summary.shape) == 2 else None,
        }
    )
    if not isinstance(metadata_summary_obj, dict):
        raise TypeError("metadata_summary must be a dictionary")
    metadata_summary = cast(dict[str, object], metadata_summary_obj)

    return PreviewData(
        source_path=dataset_data.source_path,
        dataset_index=dataset_data.dataset_index,
        raw_shape=summary.shape,
        dtype=summary.dtype,
        axis_info=axis_info,
        time=dataset_data.time,
        intensity=intensity,
        global_decay=global_decay,
        intensity_stats=intensity_stats,
        metadata_summary=metadata_summary,
    )


def _validate_sdt_path(path: Path | str) -> Path:
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"SDT file does not exist: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Expected a file path: {source_path}")
    if source_path.suffix.lower() != ".sdt":
        raise ValueError(f"Expected an .sdt file: {source_path}")
    return source_path


def _validate_dataset_index(dataset_index: int) -> None:
    if dataset_index < 0:
        raise ValueError("dataset_index must be >= 0")


def _build_dataset_summary(
    dataset_index: int, data: Any, time_length: int | None
) -> SdtDatasetSummary:
    array = np.asarray(data)
    shape = tuple(int(dimension) for dimension in array.shape)
    axis_info = infer_axes(shape, time_length=time_length)
    return SdtDatasetSummary(
        dataset_index=dataset_index,
        shape=shape,
        dtype=str(array.dtype),
        time_length=time_length,
        axis_info=axis_info,
    )


def _extract_time_length(time_items: tuple[Any, ...], dataset_index: int) -> int | None:
    if dataset_index >= len(time_items):
        return None
    time_data = np.asarray(time_items[dataset_index])
    if time_data.ndim == 0 or time_data.size == 0:
        return None
    return int(time_data.shape[0])


def _extract_time_array(
    time_items: tuple[Any, ...], dataset_index: int, time_length: int | None
) -> NDArray[np.generic] | None:
    if time_length is None or dataset_index >= len(time_items):
        return None
    time_data = np.asarray(time_items[dataset_index])
    if time_data.ndim == 0 or time_data.size == 0:
        return None
    return time_data
