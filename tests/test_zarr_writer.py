from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import zarr

from sdt_batch_exporter.core.axis_resolver import infer_axes
from sdt_batch_exporter.core.intensity import compute_intensity, compute_intensity_stats
from sdt_batch_exporter.models.axis import AxisInfo
from sdt_batch_exporter.models.export_options import ZarrExportOptions
from sdt_batch_exporter.models.sdt import PreviewData, SdtDatasetData, SdtDatasetSummary
from sdt_batch_exporter.storage.zarr_writer import (
    build_compressor,
    choose_chunks,
    export_dataset_to_zarr,
)


def _make_synthetic_data(
    tmp_path: Path, intensity_enabled: bool = True
) -> tuple[SdtDatasetData, PreviewData]:
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
    dataset = SdtDatasetData(
        source_path=source_path,
        dataset_index=0,
        data=data,
        time=time,
        summary=summary,
    )

    intensity = compute_intensity(data, axis_info.time_axis_index) if intensity_enabled else None
    intensity_stats = compute_intensity_stats(intensity) if intensity is not None else None
    preview = PreviewData(
        source_path=source_path,
        dataset_index=0,
        raw_shape=data.shape,
        dtype=str(data.dtype),
        axis_info=axis_info,
        time=time,
        intensity=intensity,
        global_decay=data.sum(axis=(0, 1)),
        intensity_stats=intensity_stats,
        metadata_summary={"synthetic": True},
    )
    return dataset, preview


def test_export_dataset_to_zarr_roundtrip_with_3d_synthetic_data(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "synthetic.zarr"

    exported = export_dataset_to_zarr(dataset, preview, output)

    assert exported == output
    root = zarr.open_group(str(output), mode="r")
    raw = root["dataset_000/raw_counts"][:]
    assert preview.intensity is not None
    assert preview.time is not None
    assert raw.shape == dataset.data.shape
    assert str(raw.dtype) == str(dataset.data.dtype)
    assert np.array_equal(raw, dataset.data)
    assert np.array_equal(root["dataset_000/intensity"][:], preview.intensity)
    assert np.array_equal(root["dataset_000/time"][:], preview.time)
    assert "metadata" in root
    assert root.attrs["schema_version"] == "0.2.0"
    assert root.attrs["source_file"] == dataset.source_path.name
    assert root.attrs["software_version"] == "0.2.0"
    assert root.attrs["compression_profile"] == "balanced"
    assert root.attrs["chunk_strategy"] == "auto"
    dataset_attrs = root["dataset_000"].attrs
    assert dataset_attrs["axis_inference_status"] == preview.axis_info.axis_inference_status
    assert dataset_attrs["chunk_strategy"] == "auto"
    assert dataset_attrs["raw_counts_chunks"] == list(root["dataset_000/raw_counts"].chunks)


def test_export_dataset_to_zarr_rejects_existing_output_when_overwrite_false(
    tmp_path: Path,
) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "existing.zarr"
    output.mkdir()
    with pytest.raises(FileExistsError):
        export_dataset_to_zarr(dataset, preview, output)


def test_export_dataset_to_zarr_allows_overwrite_when_enabled(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "overwrite.zarr"
    output.mkdir()
    export_dataset_to_zarr(dataset, preview, output, ZarrExportOptions(overwrite=True))
    root = zarr.open_group(str(output), mode="r")
    assert "dataset_000" in root


def test_export_dataset_to_zarr_skips_intensity_when_missing(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path, intensity_enabled=False)
    output = tmp_path / "no_intensity.zarr"
    export_dataset_to_zarr(dataset, preview, output)
    root = zarr.open_group(str(output), mode="r")
    assert "intensity" not in root["dataset_000"]


@pytest.mark.parametrize("profile", ["fast", "balanced", "max"])
def test_export_dataset_to_zarr_supports_compression_profiles(
    tmp_path: Path, profile: str
) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / f"{profile}.zarr"
    options = ZarrExportOptions(compression_profile=profile)  # type: ignore[arg-type]
    export_dataset_to_zarr(dataset, preview, output, options)
    root = zarr.open_group(str(output), mode="r")
    assert root.attrs["compression_profile"] == profile
    assert np.array_equal(root["dataset_000/raw_counts"][:], dataset.data)


def test_build_compressor_raises_for_invalid_profile() -> None:
    with pytest.raises(ValueError):
        build_compressor("invalid")  # type: ignore[arg-type]


def test_choose_chunks_returns_expected_shapes() -> None:
    auto_2d = choose_chunks((1024, 1024), "auto", itemsize=2)
    assert isinstance(auto_2d, tuple)
    assert auto_2d[0] > 0
    assert auto_2d[1] > 0
    auto_3d = choose_chunks((256, 256, 200), "auto", itemsize=2)
    assert isinstance(auto_3d, tuple)
    assert auto_3d[2] == 200
    assert choose_chunks((256, 256, 200), "legacy_auto") == (64, 64, 200)
    assert choose_chunks((256, 256, 200), "spatial_32") == (32, 32, 200)
    assert choose_chunks((256, 256, 200), "spatial_64") == (64, 64, 200)
    assert choose_chunks((256, 256, 200), "spatial_128") == (128, 128, 200)
    assert choose_chunks((256, 256, 200), "whole_if_possible") == (256, 256, 200)
    assert choose_chunks((256, 256, 200), "zarr_auto") is True
    with pytest.raises(ValueError):
        choose_chunks((64, 64), "invalid")  # type: ignore[arg-type]


def test_export_dataset_to_zarr_rejects_mismatched_dataset_index(
    tmp_path: Path,
) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    mismatched = PreviewData(
        source_path=preview.source_path,
        dataset_index=1,
        raw_shape=preview.raw_shape,
        dtype=preview.dtype,
        axis_info=preview.axis_info,
        time=preview.time,
        intensity=preview.intensity,
        global_decay=preview.global_decay,
        intensity_stats=preview.intensity_stats,
        metadata_summary=preview.metadata_summary,
    )
    with pytest.raises(ValueError):
        export_dataset_to_zarr(dataset, mismatched, tmp_path / "mismatch.zarr")


def test_export_dataset_to_zarr_writes_2d_intensity_source_attr(tmp_path: Path) -> None:
    source_path = tmp_path / "2d.sdt"
    source_path.write_text("placeholder", encoding="utf-8")
    data = np.arange(12, dtype=np.uint16).reshape(3, 4)
    axis_info: AxisInfo = infer_axes(data.shape)
    summary = SdtDatasetSummary(
        dataset_index=0,
        shape=data.shape,
        dtype=str(data.dtype),
        time_length=None,
        axis_info=axis_info,
    )
    dataset = SdtDatasetData(
        source_path=source_path,
        dataset_index=0,
        data=data,
        time=None,
        summary=summary,
    )
    intensity = compute_intensity(data, None)
    preview = PreviewData(
        source_path=source_path,
        dataset_index=0,
        raw_shape=data.shape,
        dtype=str(data.dtype),
        axis_info=axis_info,
        time=None,
        intensity=intensity,
        global_decay=None,
        intensity_stats=compute_intensity_stats(intensity),
        metadata_summary={"intensity_source": "source_2d_dataset"},
    )
    output = tmp_path / "2d.zarr"
    export_dataset_to_zarr(dataset, preview, output)
    root = zarr.open_group(str(output), mode="r")
    assert root["dataset_000"].attrs["intensity_source"] == "source_2d_dataset"


# --- staged write tests ---


def test_staged_write_new_file_no_tmp_residue(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "new.zarr"
    export_dataset_to_zarr(dataset, preview, output)
    assert output.exists()
    tmp_files = list(tmp_path.glob(".new.zarr.tmp-*"))
    assert tmp_files == [], f"Unexpected tmp residue: {tmp_files}"


def test_staged_write_overwrite_true_replaces_content(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "replace.zarr"
    # first write with a sentinel file inside
    output.mkdir()
    (output / "old_sentinel.txt").write_text("old", encoding="utf-8")
    # overwrite
    export_dataset_to_zarr(dataset, preview, output, ZarrExportOptions(overwrite=True))
    root = zarr.open_group(str(output), mode="r")
    assert "dataset_000" in root
    assert not (output / "old_sentinel.txt").exists()
    bak_files = list(tmp_path.glob(".replace.zarr.bak-*"))
    assert bak_files == [], f"Unexpected bak residue: {bak_files}"


def test_staged_write_overwrite_false_preserves_existing(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "existing.zarr"
    output.mkdir()
    (output / "sentinel.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        export_dataset_to_zarr(dataset, preview, output)
    assert (output / "sentinel.txt").read_text(encoding="utf-8") == "keep"


def test_staged_write_no_bak_residue_on_success(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "clean.zarr"
    output.mkdir()
    export_dataset_to_zarr(dataset, preview, output, ZarrExportOptions(overwrite=True))
    bak_files = list(tmp_path.glob(".clean.zarr.bak-*"))
    assert bak_files == [], f"Unexpected bak residue: {bak_files}"


def test_staged_write_failure_preserves_old_output(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "safe.zarr"
    output.mkdir()
    (output / "sentinel.txt").write_text("original", encoding="utf-8")

    # Patch os.replace so the second call (tmp→output) raises OSError
    original_replace = __import__("os").replace
    call_count = 0

    def patched_replace(src: str, dst: str) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise OSError("simulated lock")
        original_replace(src, dst)

    with (
        patch("sdt_batch_exporter.storage.zarr_writer.os.replace", side_effect=patched_replace),
        pytest.raises((OSError, RuntimeError)),
    ):
        export_dataset_to_zarr(dataset, preview, output, ZarrExportOptions(overwrite=True))

    # old output must still exist (restored from bak)
    assert output.exists()
    assert (output / "sentinel.txt").read_text(encoding="utf-8") == "original"
    # no tmp residue
    tmp_files = list(tmp_path.glob(".safe.zarr.tmp-*"))
    assert tmp_files == [], f"Unexpected tmp residue: {tmp_files}"


def test_staged_write_retries_transient_commit_lock(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "retry.zarr"
    output.mkdir()
    (output / "sentinel.txt").write_text("original", encoding="utf-8")

    original_replace = __import__("os").replace
    call_count = 0

    def patched_replace(src: str, dst: str) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise PermissionError("temporary lock")
        original_replace(src, dst)

    with patch("sdt_batch_exporter.storage.zarr_writer.os.replace", side_effect=patched_replace):
        export_dataset_to_zarr(dataset, preview, output, ZarrExportOptions(overwrite=True))

    root = zarr.open_group(str(output), mode="r")
    assert "dataset_000" in root
    assert call_count >= 3


def test_staged_write_failure_mentions_sync_lock_context(tmp_path: Path) -> None:
    dataset, preview = _make_synthetic_data(tmp_path)
    output = tmp_path / "locked.zarr"
    output.mkdir()
    (output / "sentinel.txt").write_text("original", encoding="utf-8")

    with (
        patch(
            "sdt_batch_exporter.storage.zarr_writer.os.replace",
            side_effect=PermissionError("still locked"),
        ),
        pytest.raises(RuntimeError, match="OneDrive|sync/preview process|locked"),
    ):
        export_dataset_to_zarr(dataset, preview, output, ZarrExportOptions(overwrite=True))

    assert output.exists()
