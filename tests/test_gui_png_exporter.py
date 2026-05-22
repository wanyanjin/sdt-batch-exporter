from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from sdt_batch_exporter.gui.png_exporter import (
    build_preview_png_metadata,
    save_preview_png,
)
from sdt_batch_exporter.gui.preview_compositor import PreviewFigureOptions
from sdt_batch_exporter.gui.preview_options import (
    ColorBarOptions,
    PreviewDisplayOptions,
    ScaleBarOptions,
)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def _options() -> PreviewFigureOptions:
    return PreviewFigureOptions(
        display=PreviewDisplayOptions(colormap="viridis"),
        scale_bar=ScaleBarOptions(enabled=True, image_width_um=200.0, scale_length_um=50.0),
        color_bar=ColorBarOptions(enabled=True, position="right"),
    )


def test_save_preview_png_writes_png_and_sidecar(
    tmp_path: Path, qapp: QApplication
) -> None:
    del qapp
    intensity = np.arange(64, dtype=np.float64).reshape(8, 8)
    output_path = tmp_path / "preview.png"
    metadata = build_preview_png_metadata(
        source_path="sample.sdt",
        dataset_index=0,
        options=_options(),
    )
    saved = save_preview_png(intensity, output_path, _options(), metadata=metadata)
    assert saved == output_path
    assert output_path.exists()
    sidecar = tmp_path / "preview.png.meta.json"
    assert sidecar.exists()
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["preview_only"] is True


def test_save_preview_png_respects_overwrite_flag(
    tmp_path: Path, qapp: QApplication
) -> None:
    del qapp
    intensity = np.arange(64, dtype=np.float64).reshape(8, 8)
    output_path = tmp_path / "preview.png"
    save_preview_png(intensity, output_path, _options(), metadata={"preview_only": True})
    with pytest.raises(FileExistsError):
        save_preview_png(intensity, output_path, _options(), metadata={"preview_only": True})
    save_preview_png(
        intensity + 1.0,
        output_path,
        _options(),
        metadata={"preview_only": True},
        overwrite=True,
    )
    assert output_path.exists()


def test_save_preview_png_does_not_modify_input(
    tmp_path: Path, qapp: QApplication
) -> None:
    del qapp
    intensity = np.arange(36, dtype=np.float64).reshape(6, 6)
    original = intensity.copy()
    save_preview_png(
        intensity,
        tmp_path / "stable.png",
        _options(),
        metadata={"preview_only": True},
    )
    assert np.array_equal(intensity, original)


def test_save_preview_png_rejects_non_2d_input(
    tmp_path: Path, qapp: QApplication
) -> None:
    del qapp
    with pytest.raises(ValueError):
        save_preview_png(
            np.zeros((2, 3, 4), dtype=np.float64),
            tmp_path / "invalid.png",
            _options(),
            metadata={"preview_only": True},
        )


def test_build_preview_png_metadata_is_json_serializable() -> None:
    metadata = build_preview_png_metadata(
        source_path="folder/sample.sdt",
        dataset_index=2,
        options=_options(),
        preview_metadata={"array": np.arange(4, dtype=np.int32)},
    )
    payload = json.dumps(metadata, ensure_ascii=False, indent=2)
    assert '"preview_only": true' in payload
    assert '"dataset_index": 2' in payload
