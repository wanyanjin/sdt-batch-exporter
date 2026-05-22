from __future__ import annotations

from pathlib import Path
from typing import cast

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from sdt_batch_exporter.core.axis_resolver import infer_axes
from sdt_batch_exporter.gui.preview_panel import PreviewPanel
from sdt_batch_exporter.models.sdt import PreviewData


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def _preview_data() -> PreviewData:
    intensity = np.arange(64, dtype=np.float64).reshape(8, 8)
    axis_info = infer_axes((8, 8), time_length=None)
    return PreviewData(
        source_path=Path("sample.sdt"),
        dataset_index=0,
        raw_shape=(8, 8),
        dtype="float64",
        axis_info=axis_info,
        time=None,
        intensity=intensity,
        global_decay=None,
        intensity_stats={"min": 0.0, "max": 63.0},
        metadata_summary={"dataset_index": 0},
    )


def test_export_preview_upsamples_small_images_for_display(qapp: QApplication) -> None:
    del qapp
    panel = PreviewPanel()
    panel.resize(900, 600)
    panel.show()
    panel.set_preview(_preview_data())
    scaled = panel._scaled_export_preview_image()
    assert scaled.shape[0] > 8
    assert scaled.shape[1] > 8
