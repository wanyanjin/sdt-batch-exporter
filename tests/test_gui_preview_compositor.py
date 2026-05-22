from __future__ import annotations

from typing import cast

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from sdt_batch_exporter.gui.preview_compositor import (
    PreviewFigureOptions,
    compute_preview_figure_layout,
    render_preview_figure,
)
from sdt_batch_exporter.gui.preview_options import (
    ColorBarOptions,
    PreviewDisplayOptions,
    ScaleBarOptions,
)


def _options(**kwargs: object) -> PreviewFigureOptions:
    display = kwargs.pop("display", PreviewDisplayOptions())
    scale_bar = kwargs.pop("scale_bar", ScaleBarOptions())
    color_bar = kwargs.pop("color_bar", ColorBarOptions())
    background = kwargs.pop("background", "black")
    canvas_margin_px = kwargs.pop("canvas_margin_px", 24)
    assert isinstance(display, PreviewDisplayOptions)
    assert isinstance(scale_bar, ScaleBarOptions)
    assert isinstance(color_bar, ColorBarOptions)
    assert background in ("black", "white")
    assert isinstance(canvas_margin_px, int)
    return PreviewFigureOptions(
        display=display,
        scale_bar=scale_bar,
        color_bar=color_bar,
        background=background,
        canvas_margin_px=canvas_margin_px,
    )


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def test_render_preview_figure_returns_rgb_uint8(qapp: QApplication) -> None:
    del qapp
    intensity = np.arange(64, dtype=np.float64).reshape(8, 8)
    out = render_preview_figure(intensity, _options())
    assert out.ndim == 3
    assert out.shape[2] == 3
    assert out.dtype == np.uint8


def test_render_preview_figure_canvas_is_larger_than_image(qapp: QApplication) -> None:
    del qapp
    intensity = np.ones((20, 30), dtype=np.float64)
    out = render_preview_figure(intensity, _options())
    assert out.shape[0] > intensity.shape[0]
    assert out.shape[1] > intensity.shape[1]


def test_color_bar_enabled_increases_width(qapp: QApplication) -> None:
    del qapp
    intensity = np.ones((20, 30), dtype=np.float64)
    with_bar = render_preview_figure(intensity, _options())
    without_bar = render_preview_figure(
        intensity,
        _options(
            color_bar=ColorBarOptions(
                enabled=False,
                position="right",
                label="PL intensity (a.u.)",
            )
        ),
    )
    assert with_bar.shape[1] > without_bar.shape[1]


def test_scale_bar_enabled_keeps_render_stable(qapp: QApplication) -> None:
    del qapp
    intensity = np.arange(100, dtype=np.float64).reshape(10, 10)
    out = render_preview_figure(
        intensity,
        _options(
            scale_bar=ScaleBarOptions(
                enabled=True,
                image_width_um=200.0,
                scale_length_um=50.0,
            )
        ),
    )
    assert out.shape[0] > 0
    assert out.shape[1] > 0


def test_input_intensity_not_modified(qapp: QApplication) -> None:
    del qapp
    intensity = np.arange(36, dtype=np.float64).reshape(6, 6)
    original = intensity.copy()
    render_preview_figure(intensity, _options())
    assert np.array_equal(intensity, original)


def test_linear_and_log1p_modes_both_supported(qapp: QApplication) -> None:
    del qapp
    intensity = np.arange(1, 65, dtype=np.float64).reshape(8, 8)
    linear = render_preview_figure(
        intensity, _options(display=PreviewDisplayOptions(display_mode="linear", colormap="gray"))
    )
    log1p = render_preview_figure(
        intensity, _options(display=PreviewDisplayOptions(display_mode="log1p", colormap="viridis"))
    )
    assert linear.shape == log1p.shape


def test_preview_compositor_supports_multiple_colormaps(qapp: QApplication) -> None:
    del qapp
    intensity = np.arange(1, 65, dtype=np.float64).reshape(8, 8)
    gray = render_preview_figure(
        intensity, _options(display=PreviewDisplayOptions(colormap="gray"))
    )
    viridis = render_preview_figure(
        intensity, _options(display=PreviewDisplayOptions(colormap="viridis"))
    )
    assert not np.array_equal(gray, viridis)


def test_render_preview_figure_rejects_non_2d_input(qapp: QApplication) -> None:
    del qapp
    with pytest.raises(ValueError):
        render_preview_figure(np.zeros((2, 3, 4), dtype=np.float64), _options())


def test_layout_places_bottom_right_scale_bar_in_lower_half() -> None:
    layout = compute_preview_figure_layout(
        (100, 200),
        _options(
            scale_bar=ScaleBarOptions(
                enabled=True,
                image_width_um=200.0,
                scale_length_um=50.0,
                position="bottom-right",
            )
        ),
    )
    assert layout.scale_bar_line is not None
    _, y1, _, _ = layout.scale_bar_line
    assert y1 > layout.canvas_height // 2
