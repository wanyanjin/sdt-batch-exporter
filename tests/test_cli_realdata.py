from __future__ import annotations

import os
from pathlib import Path

import pytest

from sdt_batch_exporter.cli import main as cli_main

pytestmark = pytest.mark.realdata


def test_cli_realdata_export(tmp_path: Path) -> None:
    test_data_dir = os.environ.get("SDT_EXPORTER_TEST_DATA_DIR")
    if not test_data_dir:
        pytest.skip("SDT_EXPORTER_TEST_DATA_DIR is not set")
    data_dir = Path(test_data_dir)
    if not data_dir.exists() or not data_dir.is_dir():
        pytest.skip("SDT_EXPORTER_TEST_DATA_DIR does not point to a valid directory")
    if not any(data_dir.glob("*.sdt")):
        pytest.skip("No .sdt files found in SDT_EXPORTER_TEST_DATA_DIR")

    output_dir = tmp_path / "exports"
    summary_path = tmp_path / "summary.json"
    exit_code = cli_main(
        [
            str(data_dir),
            "-o",
            str(output_dir),
            "--zarr",
            "--csv",
            "--dataset",
            "first",
            "--summary-json",
            str(summary_path),
        ]
    )
    assert exit_code == 0
    assert summary_path.exists()
    assert any(output_dir.rglob("*.zarr"))
    assert any(output_dir.rglob("*.csv"))
    for path in output_dir.rglob("*"):
        path.resolve().relative_to(tmp_path.resolve())
