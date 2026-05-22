"""Pure helpers for preview display transforms and colormaps."""

from __future__ import annotations

from typing import Any

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray

from sdt_batch_exporter.gui.preview_options import ColormapName, PreviewDisplayOptions


def compute_percentile_levels(
    image: NDArray[np.floating[Any] | np.integer[Any]],
    low_percentile: float,
    high_percentile: float,
) -> tuple[float, float]:
    """Compute low/high display levels from percentiles."""
    if image.ndim != 2:
        raise ValueError(f"Expected 2D array, got {image.ndim}D")
    if not (0.0 <= low_percentile < high_percentile <= 100.0):
        raise ValueError("Percentiles must satisfy 0 <= low < high <= 100")

    arr = np.asarray(image, dtype=np.float64)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    level_low = float(np.percentile(arr, low_percentile))
    level_high = float(np.percentile(arr, high_percentile))
    return (level_low, level_high)


def prepare_display_array(
    intensity: NDArray[np.floating[Any] | np.integer[Any]],
    options: PreviewDisplayOptions,
) -> NDArray[np.float64]:
    """Prepare a 2D float image for display only."""
    if intensity.ndim != 2:
        raise ValueError(f"Expected 2D array, got {intensity.ndim}D")
    if not (0.0 <= options.low_percentile < options.high_percentile <= 100.0):
        raise ValueError("Percentiles must satisfy 0 <= low < high <= 100")

    arr = np.asarray(intensity, dtype=np.float64).copy()
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    if options.display_mode == "log1p":
        arr = np.log1p(np.clip(arr, a_min=0.0, a_max=None))
    return arr


def get_colormap_lut(colormap: ColormapName) -> NDArray[np.uint8]:
    """Return an uint8 lookup table for pyqtgraph image display."""
    try:
        cmap = pg.colormap.get(colormap)
        if cmap is not None:
            table = np.asarray(cmap.getLookupTable(nPts=256), dtype=np.uint8)
            return table
    except Exception:
        pass

    # Stable fallback map names across versions
    fallback_names: dict[str, str] = {
        "gray": "CET-L1",
        "hot": "CET-L3",
        "viridis": "viridis",
        "inferno": "inferno",
        "magma": "magma",
        "plasma": "plasma",
        "turbo": "CET-L4",
    }
    fallback = fallback_names.get(colormap, "CET-L1")
    try:
        cmap = pg.colormap.get(fallback)
        if cmap is not None:
            table = np.asarray(cmap.getLookupTable(nPts=256), dtype=np.uint8)
            return table
    except Exception:
        pass
    table = np.asarray(pg.colormap.get("CET-L1").getLookupTable(nPts=256), dtype=np.uint8)
    return table
