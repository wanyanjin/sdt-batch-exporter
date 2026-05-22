"""Export option models for storage adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CompressionProfile = Literal["fast", "balanced", "max"]
TextExportFormat = Literal["csv", "txt"]
ChunkStrategy = Literal[
    "auto",
    "legacy_auto",
    "zarr_auto",
    "spatial_32",
    "spatial_64",
    "spatial_128",
    "whole_if_possible",
]


@dataclass(frozen=True)
class ZarrExportOptions:
    compression_profile: CompressionProfile = "balanced"
    chunk_strategy: ChunkStrategy = "auto"
    overwrite: bool = False
    store_intensity: bool = True
    store_time: bool = True
    store_metadata: bool = True


@dataclass(frozen=True)
class TextExportOptions:
    overwrite: bool = False
    include_metadata_json: bool = True
    fmt: str = "%.18g"
