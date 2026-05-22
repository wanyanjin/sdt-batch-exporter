from __future__ import annotations

from typing import cast

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from sdt_batch_exporter.gui.color_bar import (
    ColorBarWidget,
    compute_vertical_colorbar_layout,
    format_colorbar_value,
    render_colorbar_gradient,
)
from sdt_batch_exporter.gui.preview_options import AnnotationStyle


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def test_render_colorbar_gradient_vertical() -> None:
    lut = np.zeros((256, 3), dtype=np.uint8)
    out = render_colorbar_gradient(lut, length=50, thickness=10, orientation="vertical")
    assert out.shape == (50, 10, 4)
    assert out.dtype == np.uint8


def test_render_colorbar_gradient_horizontal() -> None:
    lut = np.zeros((256, 4), dtype=np.uint8)
    out = render_colorbar_gradient(lut, length=50, thickness=10, orientation="horizontal")
    assert out.shape == (10, 50, 4)


def test_render_colorbar_invalid_lut() -> None:
    with pytest.raises(ValueError):
        render_colorbar_gradient(np.zeros((10,), dtype=np.uint8), 20, 10, "vertical")


def test_format_colorbar_value_handles_integer_decimal_large_and_nan() -> None:
    assert format_colorbar_value(42.0) == "42"
    assert format_colorbar_value(0.012345) == "0.0123"
    assert format_colorbar_value(12345.6) == "12346"
    assert format_colorbar_value(float("nan")) == "nan"


def test_color_bar_widget_importable() -> None:
    assert ColorBarWidget is not None


def test_compute_vertical_colorbar_layout_places_ticks_at_top_and_bottom() -> None:
    gradient_rect, top_tick_rect, bottom_tick_rect, label_rect = compute_vertical_colorbar_layout(
        84, 220
    )
    assert top_tick_rect.bottom() <= gradient_rect.top()
    assert bottom_tick_rect.top() >= gradient_rect.bottom()
    assert label_rect.x() > gradient_rect.right()


def test_color_bar_accepts_separate_label_and_tick_styles(qapp: QApplication) -> None:
    del qapp
    widget = ColorBarWidget()
    lut = np.zeros((256, 3), dtype=np.uint8)
    label_style = AnnotationStyle(font_family="Arial", font_size_px=15, bold=True)
    tick_style = AnnotationStyle(font_family="Arial", font_size_px=10, italic=True)
    widget.set_colorbar(
        lut,
        1.0,
        2.0,
        label="PL intensity (a.u.)",
        orientation="vertical",
        label_style=label_style,
        tick_style=tick_style,
    )
    assert widget is not None
