"""Models for SDT file summaries, dataset loading, and preview data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from sdt_batch_exporter.models.axis import AxisInfo


@dataclass(frozen=True)
class SdtDatasetSummary:
    dataset_index: int
    shape: tuple[int, ...]
    dtype: str
    time_length: int | None
    axis_info: AxisInfo


@dataclass(frozen=True)
class SdtFileSummary:
    source_path: Path
    source_file: str
    file_size_bytes: int
    dataset_count: int
    datasets: tuple[SdtDatasetSummary, ...]
    sdt_summary_text: str


@dataclass(frozen=True)
class SdtDatasetData:
    source_path: Path
    dataset_index: int
    data: NDArray[np.generic]
    time: NDArray[np.generic] | None
    summary: SdtDatasetSummary


@dataclass(frozen=True)
class PreviewData:
    source_path: Path
    dataset_index: int
    raw_shape: tuple[int, ...]
    dtype: str
    axis_info: AxisInfo
    time: NDArray[np.generic] | None
    intensity: NDArray[np.generic] | None
    global_decay: NDArray[np.generic] | None
    intensity_stats: dict[str, object] | None
    metadata_summary: dict[str, object]
