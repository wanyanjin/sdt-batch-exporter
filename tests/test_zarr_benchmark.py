from __future__ import annotations

from pathlib import Path

import numpy as np
import zarr

from sdt_batch_exporter.core.axis_resolver import infer_axes
from sdt_batch_exporter.core.intensity import compute_intensity, compute_intensity_stats
from sdt_batch_exporter.models.export_options import ZarrExportOptions
from sdt_batch_exporter.models.sdt import PreviewData, SdtDatasetData, SdtDatasetSummary
from sdt_batch_exporter.storage.zarr_benchmark import default_benchmark_cases
from sdt_batch_exporter.storage.zarr_writer import export_dataset_to_zarr


def test_default_benchmark_cases_contains_expected_profiles_and_variants() -> None:
    cases = default_benchmark_cases()
    assert len(cases) == 9
    assert ("fast", "auto") in {(item.compression_profile, item.chunk_strategy) for item in cases}
    assert ("balanced", "legacy_auto") in {
        (item.compression_profile, item.chunk_strategy) for item in cases
    }
    assert ("balanced", "zarr_auto") in {
        (item.compression_profile, item.chunk_strategy) for item in cases
    }
    assert any(
        item.compression_profile == "balanced" and not item.store_intensity
        for item in cases
    )


def test_export_dataset_to_zarr_writes_selected_chunk_strategy(tmp_path: Path) -> None:
    source_path = tmp_path / "synthetic.sdt"
    source_path.write_text("placeholder", encoding="utf-8")
    data = np.arange(2 * 3 * 4, dtype=np.uint16).reshape(2, 3, 4)
    time = np.linspace(0.0, 3.0, num=4, dtype=np.float64)
    axis_info = infer_axes(data.shape, time_length=4)

    summary = SdtDatasetSummary(
        dataset_index=0,
        shape=data.shape,
        dtype=str(data.dtype),
        time_length=4,
        axis_info=axis_info,
    )
    dataset_data = SdtDatasetData(
        source_path=source_path,
        dataset_index=0,
        data=data,
        time=time,
        summary=summary,
    )
    intensity = compute_intensity(data, axis_info.time_axis_index)
    preview_data = PreviewData(
        source_path=source_path,
        dataset_index=0,
        raw_shape=data.shape,
        dtype=str(data.dtype),
        axis_info=axis_info,
        time=time,
        intensity=intensity,
        global_decay=data.sum(axis=(0, 1)),
        intensity_stats=compute_intensity_stats(intensity),
        metadata_summary={"synthetic": True},
    )

    output = tmp_path / "chunk_32.zarr"
    options = ZarrExportOptions(chunk_strategy="spatial_32")
    export_dataset_to_zarr(dataset_data, preview_data, output, options)
    root = zarr.open_group(str(output), mode="r")

    assert root.attrs["chunk_strategy"] == "spatial_32"
    assert root["dataset_000"].attrs["chunk_strategy"] == "spatial_32"
    assert root["dataset_000"].attrs["raw_counts_chunks"] == [2, 3, 4]


def test_export_dataset_to_zarr_records_actual_chunks_for_zarr_auto(tmp_path: Path) -> None:
    source_path = tmp_path / "synthetic_auto.sdt"
    source_path.write_text("placeholder", encoding="utf-8")
    data = np.arange(2 * 3 * 4, dtype=np.uint16).reshape(2, 3, 4)
    time = np.linspace(0.0, 3.0, num=4, dtype=np.float64)
    axis_info = infer_axes(data.shape, time_length=4)
    summary = SdtDatasetSummary(
        dataset_index=0,
        shape=data.shape,
        dtype=str(data.dtype),
        time_length=4,
        axis_info=axis_info,
    )
    dataset_data = SdtDatasetData(
        source_path=source_path,
        dataset_index=0,
        data=data,
        time=time,
        summary=summary,
    )
    intensity = compute_intensity(data, axis_info.time_axis_index)
    preview_data = PreviewData(
        source_path=source_path,
        dataset_index=0,
        raw_shape=data.shape,
        dtype=str(data.dtype),
        axis_info=axis_info,
        time=time,
        intensity=intensity,
        global_decay=data.sum(axis=(0, 1)),
        intensity_stats=compute_intensity_stats(intensity),
        metadata_summary={"synthetic": True},
    )
    output = tmp_path / "zarr_auto.zarr"
    options = ZarrExportOptions(chunk_strategy="zarr_auto")
    export_dataset_to_zarr(dataset_data, preview_data, output, options)
    root = zarr.open_group(str(output), mode="r")
    assert root.attrs["chunk_strategy"] == "zarr_auto"
    expected_chunks = list(root["dataset_000/raw_counts"].chunks)
    assert root["dataset_000"].attrs["raw_counts_chunks"] == expected_chunks
