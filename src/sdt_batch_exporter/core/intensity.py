"""Pure intensity and decay calculations."""

from __future__ import annotations

from typing import cast

import numpy as np
from numpy.typing import NDArray


def compute_intensity(
    data: NDArray[np.generic], time_axis_index: int | None
) -> NDArray[np.generic]:
    """Compute integrated intensity without altering the physical meaning."""
    if data.ndim < 2:
        raise ValueError("data must have at least 2 dimensions")
    if data.ndim == 2:
        return data.copy()
    if time_axis_index is None:
        raise ValueError("time_axis_index is required for data with 3 or more dimensions")
    axis_index = _normalize_axis_index(data.ndim, time_axis_index)
    return cast(NDArray[np.generic], data.sum(axis=axis_index))


def compute_global_decay(
    data: NDArray[np.generic], spatial_axes: tuple[int, ...]
) -> NDArray[np.generic]:
    """Sum data across the provided spatial axes."""
    if not spatial_axes:
        raise ValueError("spatial_axes must not be empty")
    if len(set(spatial_axes)) != len(spatial_axes):
        raise ValueError("spatial_axes must not contain duplicates")

    normalized_axes = tuple(_normalize_axis_index(data.ndim, axis) for axis in spatial_axes)
    if len(set(normalized_axes)) != len(normalized_axes):
        raise ValueError("spatial_axes must not resolve to duplicate axes")
    return cast(NDArray[np.generic], data.sum(axis=normalized_axes))


def compute_intensity_stats(intensity: NDArray[np.generic]) -> dict[str, object]:
    """Return JSON-friendly intensity statistics."""
    if intensity.size == 0:
        raise ValueError("intensity array must not be empty")

    minimum = intensity.min()
    maximum = intensity.max()
    mean = intensity.mean()
    total = intensity.sum()

    return {
        "shape": tuple(int(dimension) for dimension in intensity.shape),
        "dtype": str(intensity.dtype),
        "min": _to_python_scalar(minimum),
        "max": _to_python_scalar(maximum),
        "mean": _to_python_scalar(mean),
        "sum": _to_python_scalar(total),
    }


def _normalize_axis_index(ndim: int, axis_index: int) -> int:
    if axis_index < 0:
        axis_index += ndim
    if axis_index < 0 or axis_index >= ndim:
        raise ValueError("axis index is out of range")
    return axis_index


def _to_python_scalar(value: np.generic) -> int | float | bool | str:
    if isinstance(value, np.generic):
        return cast(int | float | bool | str, value.item())
    raise TypeError("value must be a numpy scalar")
