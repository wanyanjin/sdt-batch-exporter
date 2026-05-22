from __future__ import annotations

import os
from pathlib import Path

import pytest

from sdt_batch_exporter.storage.sdt_reader import (
    build_preview_data,
    load_sdt_dataset,
    read_sdt_summary,
)

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


def test_read_sdt_summary_for_realdata_files() -> None:
    sdt_files = _discover_sdt_files()
    for path in sdt_files:
        summary = read_sdt_summary(path)
        assert summary.dataset_count > 0
        assert summary.datasets
        assert summary.sdt_summary_text
        for dataset in summary.datasets:
            assert dataset.shape
            assert dataset.dtype
            assert dataset.axis_info is not None


def test_build_preview_data_for_first_realdata_dataset() -> None:
    sdt_files = _discover_sdt_files()
    first = sdt_files[0]

    dataset = load_sdt_dataset(first, dataset_index=0)
    preview = build_preview_data(first, dataset_index=0)

    assert dataset.data.size > 0
    assert preview.raw_shape == dataset.summary.shape
    assert preview.metadata_summary["dataset_index"] == 0
    if preview.intensity is not None:
        assert preview.intensity_stats is not None
        assert preview.intensity.shape
