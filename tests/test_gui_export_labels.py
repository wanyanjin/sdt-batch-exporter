from __future__ import annotations

from pathlib import Path

from sdt_batch_exporter.gui.export_labels import describe_output_path


def test_describe_output_path_zarr() -> None:
    assert describe_output_path(Path("sample_dataset000.zarr")) == "Full cube"


def test_describe_output_path_csv() -> None:
    assert describe_output_path(Path("sample_dataset000_intensity.csv")) == "Intensity CSV"


def test_describe_output_path_txt() -> None:
    assert describe_output_path(Path("sample_dataset000_intensity.txt")) == "Intensity TXT"


def test_describe_output_path_meta_json() -> None:
    assert (
        describe_output_path(Path("sample_dataset000_intensity.csv.meta.json"))
        == "Metadata JSON"
    )


def test_describe_output_path_preview_png() -> None:
    assert describe_output_path(Path("sample_dataset000_preview.png")) == "Preview PNG"


def test_describe_output_path_fallback() -> None:
    assert describe_output_path(Path("unknown.bin")) == "Output"
