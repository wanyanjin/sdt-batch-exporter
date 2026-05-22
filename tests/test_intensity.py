from __future__ import annotations

import numpy as np
import pytest

from sdt_batch_exporter.core.intensity import (
    compute_global_decay,
    compute_intensity,
    compute_intensity_stats,
)


def test_compute_intensity_returns_copy_for_2d_data() -> None:
    data = np.arange(6, dtype=np.uint16).reshape(2, 3)

    intensity = compute_intensity(data, time_axis_index=None)

    assert np.array_equal(intensity, data)
    assert intensity is not data


def test_compute_intensity_sums_along_last_axis() -> None:
    data = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)

    intensity = compute_intensity(data, time_axis_index=2)

    expected = data.sum(axis=2)
    assert np.array_equal(intensity, expected)


def test_compute_intensity_sums_along_non_last_axis() -> None:
    data = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)

    intensity = compute_intensity(data, time_axis_index=1)

    expected = data.sum(axis=1)
    assert np.array_equal(intensity, expected)


def test_compute_intensity_requires_time_axis_for_3d_data() -> None:
    data = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)

    with pytest.raises(ValueError):
        compute_intensity(data, time_axis_index=None)


def test_compute_intensity_rejects_out_of_range_axis() -> None:
    data = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)

    with pytest.raises(ValueError):
        compute_intensity(data, time_axis_index=3)


def test_compute_global_decay_sums_spatial_axes() -> None:
    data = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)

    decay = compute_global_decay(data, spatial_axes=(0, 1))

    expected = data.sum(axis=(0, 1))
    assert decay.shape == (4,)
    assert np.array_equal(decay, expected)


def test_compute_intensity_stats_returns_json_friendly_values() -> None:
    intensity = np.array([[1, 2], [3, 4]], dtype=np.uint16)

    stats = compute_intensity_stats(intensity)

    assert stats == {
        "shape": (2, 2),
        "dtype": "uint16",
        "min": 1,
        "max": 4,
        "mean": 2.5,
        "sum": 10,
    }


def test_compute_intensity_stats_rejects_empty_arrays() -> None:
    intensity = np.array([], dtype=np.uint16)

    with pytest.raises(ValueError):
        compute_intensity_stats(intensity)
