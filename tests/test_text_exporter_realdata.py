from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from sdt_batch_exporter.storage.sdt_reader import build_preview_data
from sdt_batch_exporter.storage.text_exporter import export_intensity_csv, export_intensity_txt

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


def test_export_intensity_csv_txt_for_realdata(tmp_path: Path) -> None:
    files = _discover_sdt_files()
    first = files[0]
    preview = build_preview_data(first, dataset_index=0)

    if preview.intensity is None:
        pytest.skip("Preview data has no intensity; skip text export")
    if preview.intensity.ndim != 2:
        pytest.skip("Preview intensity is not 2D; skip text export")

    csv_path = tmp_path / "intensity.csv"
    txt_path = tmp_path / "intensity.txt"
    export_intensity_csv(preview, csv_path)
    export_intensity_txt(preview, txt_path)

    csv_loaded = np.loadtxt(csv_path, delimiter=",")
    txt_loaded = np.loadtxt(txt_path, delimiter="\t")

    assert csv_loaded.shape == preview.intensity.shape
    assert txt_loaded.shape == preview.intensity.shape
    assert np.array_equal(csv_loaded, preview.intensity)
    assert np.array_equal(txt_loaded, preview.intensity)
    assert (tmp_path / "intensity.csv.meta.json").exists()
    assert (tmp_path / "intensity.txt.meta.json").exists()
