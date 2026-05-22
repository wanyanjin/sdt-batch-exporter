from __future__ import annotations

import numpy as np
import pytest

from sdt_batch_exporter.gui.preview_options import PreviewDisplayOptions
from sdt_batch_exporter.gui.preview_rendering import (
    compute_percentile_levels,
    get_colormap_lut,
    prepare_display_array,
)


def test_prepare_display_array_linear() -> None:
    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    out = prepare_display_array(arr, PreviewDisplayOptions(display_mode="linear"))
    assert out.shape == (2, 2)


def test_prepare_display_array_log1p() -> None:
    arr = np.array([[0.0, 1.0], [3.0, 9.0]])
    out = prepare_display_array(arr, PreviewDisplayOptions(display_mode="log1p"))
    assert out.shape == (2, 2)
    assert np.all(out >= 0)


def test_prepare_display_array_requires_2d() -> None:
    with pytest.raises(ValueError):
        prepare_display_array(np.zeros((2, 2, 2)), PreviewDisplayOptions())


def test_prepare_display_array_handles_nan_inf() -> None:
    arr = np.array([[np.nan, np.inf], [-np.inf, 1.0]])
    out = prepare_display_array(arr, PreviewDisplayOptions())
    assert out.shape == (2, 2)
    assert np.isfinite(out).all()


def test_percentile_levels_constant_image() -> None:
    arr = np.ones((4, 4))
    low, high = compute_percentile_levels(arr, 2.0, 98.0)
    assert low == high == 1.0


def test_percentile_levels_invalid_percentiles() -> None:
    with pytest.raises(ValueError):
        compute_percentile_levels(np.ones((3, 3)), 50, 40)


def test_get_colormap_lut_shape_and_dtype() -> None:
    for name in ("gray", "hot", "viridis", "inferno", "magma", "plasma", "turbo"):
        lut = get_colormap_lut(name)
        assert lut.shape[0] == 256
        assert lut.shape[1] in (3, 4)
        assert lut.dtype == np.uint8


def test_input_not_modified() -> None:
    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    before = arr.copy()
    _ = prepare_display_array(arr, PreviewDisplayOptions(display_mode="log1p"))
    assert np.array_equal(arr, before)
