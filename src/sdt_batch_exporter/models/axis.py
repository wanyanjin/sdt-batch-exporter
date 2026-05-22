"""Axis inference models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AxisInferenceStatus = Literal["resolved", "ambiguous", "failed", "not_required"]


@dataclass(frozen=True)
class AxisInfo:
    """Result of axis inference for an SDT dataset-like array."""

    data_shape: tuple[int, ...]
    time_axis_index: int | None
    spatial_axes: tuple[int, ...]
    axis_order: tuple[str, ...]
    inference_source: str
    axis_inference_status: AxisInferenceStatus
    is_exportable_intensity: bool
    skipped_intensity_export: bool
    skip_reason: str | None = None
