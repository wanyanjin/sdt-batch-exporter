"""Pure-function helpers for converting intensity arrays to display images."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def normalize_intensity_to_uint8(
    intensity: NDArray[np.generic],
    *,
    low_percentile: float = 2.0,
    high_percentile: float = 98.0,
) -> NDArray[np.uint8]:
    """Percentile contrast stretch of a 2D intensity array to uint8.

    Parameters
    ----------
    intensity:
        2D array of any numeric dtype.
    low_percentile:
        Lower clip percentile (default 2.0).
    high_percentile:
        Upper clip percentile (default 98.0).

    Returns
    -------
    uint8 array of the same shape.

    Raises
    ------
    ValueError
        If *intensity* is not 2D, or percentile bounds are invalid.
    """
    if intensity.ndim != 2:
        raise ValueError(f"Expected 2D array, got {intensity.ndim}D")
    if not (0.0 <= low_percentile < high_percentile <= 100.0):
        raise ValueError(
            f"Percentiles must satisfy 0 <= low < high <= 100, "
            f"got low={low_percentile}, high={high_percentile}"
        )

    arr = intensity.astype(np.float64)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

    p_low = float(np.percentile(arr, low_percentile))
    p_high = float(np.percentile(arr, high_percentile))

    if p_high <= p_low:
        return np.zeros_like(arr, dtype=np.uint8)

    clipped = np.clip(arr, p_low, p_high)
    scaled = (clipped - p_low) / (p_high - p_low) * 255.0
    return scaled.astype(np.uint8)
