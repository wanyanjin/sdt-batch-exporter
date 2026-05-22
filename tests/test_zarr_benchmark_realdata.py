from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

import pytest

from sdt_batch_exporter.storage.zarr_benchmark import benchmark_sdt_dataset_to_zarr

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


def test_benchmark_sdt_dataset_to_zarr_for_all_realdata_files(tmp_path: Path) -> None:
    files = _discover_sdt_files()
    all_results: list[dict[str, object]] = []

    for sdt_file in files:
        output_root = tmp_path / sdt_file.stem
        results = benchmark_sdt_dataset_to_zarr(
            sdt_file,
            output_root,
            dataset_index=0,
        )
        assert results
        for result in results:
            assert result.zarr_size_bytes > 0
            assert result.write_time_s >= 0
            assert result.readback_time_s >= 0
            assert result.raw_nbytes > 0
            all_results.append(asdict(result))

    report = tmp_path / "zarr_benchmark_summary.json"
    report.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(json.dumps(all_results, indent=2))
    assert all_results
