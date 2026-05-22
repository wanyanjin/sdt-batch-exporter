from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
import zarr

from sdt_batch_exporter.models.export_options import ZarrExportOptions
from sdt_batch_exporter.storage.zarr_writer import export_sdt_dataset_to_zarr

pytestmark = pytest.mark.realdata


def _discover_sdt_files() -> list[Path]:
    test_data_dir = os.environ.get("SDT_EXPORTER_TEST_DATA_DIR")
    if not test_data_dir:
        pytest.skip("SDT_EXPORTER_TEST_DATA_DIR is not set")
    root = Path(test_data_dir)
    if not root.exists() or not root.is_dir():
        pytest.skip("SDT_EXPORTER_TEST_DATA_DIR does not point to a valid directory")
    files = sorted(root.glob("*.sdt"))
    if not files:
        pytest.skip("No .sdt files found in SDT_EXPORTER_TEST_DATA_DIR")
    return files


def _directory_size_bytes(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def test_export_sdt_dataset_to_zarr_realdata_readback(tmp_path: Path) -> None:
    source = _discover_sdt_files()[0]
    output = tmp_path / "sample.zarr"

    export_sdt_dataset_to_zarr(source, output, dataset_index=0)

    root = zarr.open_group(str(output), mode="r")
    assert root.attrs["schema_version"] == "0.1.0"
    assert "metadata" in root
    assert "raw_counts" in root["dataset_000"]
    if "intensity" in root["dataset_000"]:
        assert root["dataset_000/intensity"].shape


def test_export_sdt_dataset_to_zarr_realdata_benchmark_profiles(tmp_path: Path) -> None:
    source = _discover_sdt_files()[0]
    profiles = ("fast", "balanced", "max")
    benchmark: list[dict[str, float | str]] = []

    for profile in profiles:
        output = tmp_path / f"{profile}.zarr"
        start_write = time.perf_counter()
        export_sdt_dataset_to_zarr(
            source,
            output,
            dataset_index=0,
            options=ZarrExportOptions(compression_profile=profile),  # type: ignore[arg-type]
        )
        write_time_s = time.perf_counter() - start_write

        start_read = time.perf_counter()
        root = zarr.open_group(str(output), mode="r")
        raw = root["dataset_000/raw_counts"][:]
        readback_time_s = time.perf_counter() - start_read

        zarr_size = _directory_size_bytes(output)
        raw_nbytes = float(raw.nbytes)
        sdt_size = float(source.stat().st_size)
        benchmark.append(
            {
                "profile": profile,
                "write_time_s": write_time_s,
                "readback_time_s": readback_time_s,
                "zarr_size_bytes": float(zarr_size),
                "raw_nbytes": raw_nbytes,
                "source_sdt_size_bytes": sdt_size,
                "zarr_to_sdt_ratio": float(zarr_size) / sdt_size if sdt_size else 0.0,
                "zarr_to_raw_ratio": float(zarr_size) / raw_nbytes if raw_nbytes else 0.0,
            }
        )

    report = tmp_path / "compression_benchmark.json"
    report.write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
    print(json.dumps(benchmark, indent=2))

    assert len(benchmark) == 3
    for item in benchmark:
        value = item["zarr_size_bytes"]
        assert isinstance(value, float)
        assert value > 0
