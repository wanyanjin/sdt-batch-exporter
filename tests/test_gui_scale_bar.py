from __future__ import annotations

import pytest

from sdt_batch_exporter.gui.preview_options import ScaleBarOptions
from sdt_batch_exporter.gui.scale_bar import (
    compute_scale_bar_anchor_position,
    compute_scale_bar_pixels,
)


def test_compute_scale_bar_pixels_nominal() -> None:
    assert (
        compute_scale_bar_pixels(image_width_px=256, image_width_um=200, scale_length_um=50)
        == 64
    )


def test_compute_scale_bar_pixels_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        compute_scale_bar_pixels(image_width_px=0, image_width_um=200, scale_length_um=50)
    with pytest.raises(ValueError):
        compute_scale_bar_pixels(image_width_px=256, image_width_um=0, scale_length_um=50)
    with pytest.raises(ValueError):
        compute_scale_bar_pixels(image_width_px=256, image_width_um=200, scale_length_um=0)


def test_compute_scale_bar_pixels_too_long() -> None:
    with pytest.raises(ValueError):
        compute_scale_bar_pixels(image_width_px=256, image_width_um=200, scale_length_um=300)


def test_scale_bar_positions_within_bounds() -> None:
    for pos in ("bottom-left", "bottom-right", "top-left", "top-right"):
        x1, y1, x2, y2 = compute_scale_bar_anchor_position(
            image_width_px=200,
            image_height_px=100,
            scale_bar_width_px=50,
            margin_x_px=10,
            margin_y_px=8,
            position=pos,
        )
        assert 0 <= x1 <= x2 <= 200
        assert 0 <= y1 == y2 < 100


def test_scale_bar_offsets_change_position() -> None:
    base = compute_scale_bar_anchor_position(
        image_width_px=200,
        image_height_px=100,
        scale_bar_width_px=50,
        margin_x_px=0,
        margin_y_px=0,
        position="bottom-left",
    )
    moved = compute_scale_bar_anchor_position(
        image_width_px=200,
        image_height_px=100,
        scale_bar_width_px=50,
        margin_x_px=20,
        margin_y_px=15,
        position="bottom-left",
    )
    assert moved != base


def test_scale_bar_coordinate_convention_top_y_is_smaller() -> None:
    top_left = compute_scale_bar_anchor_position(
        image_width_px=200,
        image_height_px=100,
        scale_bar_width_px=50,
        margin_x_px=10,
        margin_y_px=8,
        position="top-left",
    )
    bottom_left = compute_scale_bar_anchor_position(
        image_width_px=200,
        image_height_px=100,
        scale_bar_width_px=50,
        margin_x_px=10,
        margin_y_px=8,
        position="bottom-left",
    )
    assert top_left[1] < bottom_left[1]


def test_scale_bar_coordinate_convention_right_positions() -> None:
    top_right = compute_scale_bar_anchor_position(
        image_width_px=200,
        image_height_px=100,
        scale_bar_width_px=50,
        margin_x_px=10,
        margin_y_px=8,
        position="top-right",
    )
    bottom_right = compute_scale_bar_anchor_position(
        image_width_px=200,
        image_height_px=100,
        scale_bar_width_px=50,
        margin_x_px=10,
        margin_y_px=8,
        position="bottom-right",
    )
    bottom_left = compute_scale_bar_anchor_position(
        image_width_px=200,
        image_height_px=100,
        scale_bar_width_px=50,
        margin_x_px=10,
        margin_y_px=8,
        position="bottom-left",
    )
    assert top_right[1] < bottom_right[1]
    assert bottom_right[0] > bottom_left[0]


def test_scale_bar_default_position_is_bottom_right() -> None:
    assert ScaleBarOptions().position == "bottom-right"
