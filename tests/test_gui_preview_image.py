"""Tests for preview_image pure functions (no Qt required)."""

from __future__ import annotations

import numpy as np
import pytest

from sdt_batch_exporter.gui.preview_image import normalize_intensity_to_uint8


def test_normalize_returns_uint8_dtype() -> None:
    arr = np.array([[0, 100], [200, 300]], dtype=np.uint16)
    result = normalize_intensity_to_uint8(arr)
    assert result.dtype == np.uint8


def test_normalize_output_shape_unchanged() -> None:
    arr = np.random.default_rng(0).integers(0, 1000, size=(8, 12), dtype=np.uint16)
    result = normalize_intensity_to_uint8(arr)
    assert result.shape == arr.shape


def test_normalize_range_maps_to_0_255() -> None:
    arr = np.linspace(0, 1000, num=100, dtype=np.float64).reshape(10, 10)
    result = normalize_intensity_to_uint8(arr, low_percentile=0.0, high_percentile=100.0)
    assert int(result.min()) == 0
    assert int(result.max()) == 255


def test_normalize_flat_array_returns_zeros() -> None:
    arr = np.full((4, 4), 42, dtype=np.float32)
    result = normalize_intensity_to_uint8(arr)
    assert np.all(result == 0)


def test_normalize_single_pixel_array() -> None:
    arr = np.array([[7]], dtype=np.int32)
    result = normalize_intensity_to_uint8(arr)
    assert result.shape == (1, 1)
    assert result.dtype == np.uint8


def test_normalize_handles_nan_values() -> None:
    arr = np.array([[np.nan, 1.0], [2.0, 3.0]])
    result = normalize_intensity_to_uint8(arr)
    assert result.dtype == np.uint8
    assert not np.any(np.isnan(result.astype(np.float64)))


def test_normalize_handles_inf_values() -> None:
    arr = np.array([[np.inf, 1.0], [2.0, -np.inf]])
    result = normalize_intensity_to_uint8(arr)
    assert result.dtype == np.uint8


def test_normalize_rejects_1d_input() -> None:
    arr = np.array([1, 2, 3], dtype=np.float32)
    with pytest.raises(ValueError, match="2D"):
        normalize_intensity_to_uint8(arr)


def test_normalize_rejects_3d_input() -> None:
    arr = np.zeros((2, 3, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="2D"):
        normalize_intensity_to_uint8(arr)


def test_normalize_percentile_clips_outliers() -> None:
    # 98% of values are 0-10, two extreme outliers
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 10, size=(10, 10), dtype=np.int32).astype(np.float64)
    arr[0, 0] = 10000  # high outlier
    arr[9, 9] = -10000  # low outlier
    result = normalize_intensity_to_uint8(arr, low_percentile=2.0, high_percentile=98.0)
    # outlier pixels should be clipped to 0 or 255, not dominate the range
    assert result.dtype == np.uint8
    # the bulk of the image should use a reasonable range
    bulk = result[1:9, 1:9]
    assert int(bulk.max()) > 0
