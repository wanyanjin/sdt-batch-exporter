from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sdt_batch_exporter.core.axis_resolver import infer_axes
from sdt_batch_exporter.core.intensity import compute_intensity_stats
from sdt_batch_exporter.models.export_options import TextExportOptions
from sdt_batch_exporter.models.sdt import PreviewData
from sdt_batch_exporter.storage.text_exporter import (
    export_intensity_csv,
    export_intensity_matrix,
    export_intensity_txt,
)


def _build_preview_data(
    tmp_path: Path,
    *,
    intensity: np.ndarray | None = None,
) -> PreviewData:
    source = tmp_path / "sample.sdt"
    source.write_text("placeholder", encoding="utf-8")
    matrix = intensity if intensity is not None else np.arange(12, dtype=np.uint16).reshape(3, 4)
    axis_info = infer_axes((3, 4))
    stats = compute_intensity_stats(matrix) if intensity is not None or matrix.ndim == 2 else None
    return PreviewData(
        source_path=source,
        dataset_index=0,
        raw_shape=(3, 4),
        dtype="uint16",
        axis_info=axis_info,
        time=None,
        intensity=matrix if intensity is not None else matrix,
        global_decay=None,
        intensity_stats=stats,
        metadata_summary={"synthetic": True},
    )


def test_export_intensity_csv_roundtrip_with_metadata(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path)
    output = tmp_path / "exports" / "intensity.csv"

    export_intensity_csv(preview, output)

    loaded = np.loadtxt(output, delimiter=",")
    assert preview.intensity is not None
    assert np.array_equal(loaded, preview.intensity)
    assert (tmp_path / "exports" / "intensity.csv.meta.json").exists()


def test_export_intensity_txt_roundtrip_with_metadata(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path)
    output = tmp_path / "exports" / "intensity.txt"

    export_intensity_txt(preview, output)

    loaded = np.loadtxt(output, delimiter="\t")
    assert preview.intensity is not None
    assert np.array_equal(loaded, preview.intensity)
    assert (tmp_path / "exports" / "intensity.txt.meta.json").exists()


def test_export_without_metadata_json(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path)
    output = tmp_path / "intensity.csv"

    export_intensity_csv(
        preview,
        output,
        options=TextExportOptions(include_metadata_json=False),
    )

    assert output.exists()
    assert not (tmp_path / "intensity.csv.meta.json").exists()


def test_export_rejects_existing_file_without_overwrite(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path)
    output = tmp_path / "intensity.csv"
    output.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        export_intensity_csv(preview, output)


def test_export_overwrites_existing_file_when_enabled(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path)
    output = tmp_path / "intensity.csv"
    output.write_text("existing", encoding="utf-8")

    export_intensity_csv(preview, output, options=TextExportOptions(overwrite=True))

    loaded = np.loadtxt(output, delimiter=",")
    assert preview.intensity is not None
    assert np.array_equal(loaded, preview.intensity)


def test_export_raises_for_missing_intensity(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path)
    preview_none = PreviewData(
        source_path=preview.source_path,
        dataset_index=preview.dataset_index,
        raw_shape=preview.raw_shape,
        dtype=preview.dtype,
        axis_info=preview.axis_info,
        time=preview.time,
        intensity=None,
        global_decay=preview.global_decay,
        intensity_stats=None,
        metadata_summary=preview.metadata_summary,
    )
    with pytest.raises(ValueError, match="does not contain intensity"):
        export_intensity_csv(preview_none, tmp_path / "intensity.csv")


def test_export_raises_for_non_2d_intensity(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path, intensity=np.arange(24).reshape(2, 3, 4))
    with pytest.raises(ValueError, match="Only 2D intensity matrices"):
        export_intensity_csv(preview, tmp_path / "intensity.csv")


def test_export_raises_for_invalid_format(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path)
    with pytest.raises(ValueError, match="Unsupported text export format"):
        export_intensity_matrix(
            preview,
            tmp_path / "intensity.csv",
            export_format="bad",  # type: ignore[arg-type]
        )


def test_export_raises_for_suffix_mismatch(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path)
    with pytest.raises(ValueError, match="Expected .csv suffix"):
        export_intensity_csv(preview, tmp_path / "intensity.txt")


def test_export_creates_parent_directory(tmp_path: Path) -> None:
    preview = _build_preview_data(tmp_path)
    output = tmp_path / "nested" / "dir" / "intensity.csv"

    export_intensity_csv(preview, output)

    assert output.exists()
