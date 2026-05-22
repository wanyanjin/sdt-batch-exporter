from __future__ import annotations

import os
from pathlib import Path

import pytest

from sdt_batch_exporter.models.workflow import BatchExportRequest, ExportOutputs
from sdt_batch_exporter.workflows.export_workflow import export_batch

pytestmark = pytest.mark.realdata


def _discover_sdt_files(limit: int = 2) -> list[Path]:
    test_data_dir = os.environ.get("SDT_EXPORTER_TEST_DATA_DIR")
    if not test_data_dir:
        pytest.skip("SDT_EXPORTER_TEST_DATA_DIR is not set")
    root = Path(test_data_dir)
    if not root.exists() or not root.is_dir():
        pytest.skip("SDT_EXPORTER_TEST_DATA_DIR does not point to a valid directory")
    files = sorted(root.glob("*.sdt"))
    if not files:
        pytest.skip("No .sdt files found in SDT_EXPORTER_TEST_DATA_DIR")
    return files[:limit]


def test_export_batch_realdata_first_dataset(tmp_path: Path) -> None:
    sources = _discover_sdt_files(limit=2)
    result = export_batch(
        BatchExportRequest(
            source_paths=tuple(sources),
            output_root=tmp_path,
            dataset_selection="first",
            outputs=ExportOutputs(zarr=True, csv=True, txt=True),
        )
    )

    assert result.file_results
    assert result.success_count >= 1
    for file_result in result.file_results:
        for dataset_result in file_result.dataset_results:
            for output_path in dataset_result.output_paths:
                output_path.resolve().relative_to(tmp_path.resolve())
        if file_result.status == "success":
            dataset = file_result.dataset_results[0]
            assert any(path.suffix == ".zarr" for path in dataset.output_paths)
            assert any(path.suffix == ".csv" for path in dataset.output_paths)
            assert any(path.suffix == ".txt" for path in dataset.output_paths)
