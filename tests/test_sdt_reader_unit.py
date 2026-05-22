from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sdt_batch_exporter.models.axis import AxisInfo
from sdt_batch_exporter.models.sdt import PreviewData, SdtDatasetData, SdtDatasetSummary
from sdt_batch_exporter.storage.sdt_reader import (
    build_preview_data,
    load_sdt_dataset,
    read_sdt_summary,
)


def test_read_sdt_summary_raises_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sdt"
    with pytest.raises(FileNotFoundError):
        read_sdt_summary(missing)


def test_read_sdt_summary_raises_for_non_sdt_suffix(tmp_path: Path) -> None:
    not_sdt = tmp_path / "sample.txt"
    not_sdt.write_text("not sdt", encoding="utf-8")
    with pytest.raises(ValueError):
        read_sdt_summary(not_sdt)


def test_read_sdt_summary_raises_for_directory_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        read_sdt_summary(tmp_path)


def test_load_sdt_dataset_rejects_negative_dataset_index(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.sdt"
    file_path.write_text("placeholder", encoding="utf-8")
    with pytest.raises(ValueError):
        load_sdt_dataset(file_path, dataset_index=-1)


def test_build_preview_data_delegates_from_dataset_data(monkeypatch: pytest.MonkeyPatch) -> None:
    axis_info = AxisInfo(
        data_shape=(2, 2),
        time_axis_index=None,
        spatial_axes=(0, 1),
        axis_order=("y", "x"),
        inference_source="source_2d_dataset",
        axis_inference_status="not_required",
        is_exportable_intensity=True,
        skipped_intensity_export=False,
        skip_reason=None,
    )
    dataset = SdtDatasetData(
        source_path=Path("/tmp/sample.sdt"),
        dataset_index=0,
        data=np.zeros((2, 2), dtype=np.uint16),
        time=None,
        summary=SdtDatasetSummary(
            dataset_index=0,
            shape=(2, 2),
            dtype="uint16",
            time_length=None,
            axis_info=axis_info,
        ),
    )
    expected = PreviewData(
        source_path=dataset.source_path,
        dataset_index=0,
        raw_shape=(2, 2),
        dtype="uint16",
        axis_info=axis_info,
        time=None,
        intensity=None,
        global_decay=None,
        intensity_stats=None,
        metadata_summary={},
    )

    monkeypatch.setattr(
        "sdt_batch_exporter.storage.sdt_reader.load_sdt_dataset",
        lambda path, dataset_index=0: dataset,
    )
    monkeypatch.setattr(
        "sdt_batch_exporter.storage.sdt_reader.build_preview_from_dataset_data",
        lambda dataset_data: expected,
    )

    result = build_preview_data(Path("/tmp/sample.sdt"), 0)
    assert result == expected
