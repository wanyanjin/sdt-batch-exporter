"""Benchmark helpers for SDT-to-Zarr compression and chunk strategies."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import zarr

from sdt_batch_exporter.models.export_options import (
    ChunkStrategy,
    CompressionProfile,
    ZarrExportOptions,
)
from sdt_batch_exporter.storage.sdt_reader import build_preview_data, load_sdt_dataset
from sdt_batch_exporter.storage.zarr_writer import export_dataset_to_zarr


@dataclass(frozen=True)
class ZarrBenchmarkCase:
    compression_profile: CompressionProfile
    chunk_strategy: ChunkStrategy = "auto"
    store_intensity: bool = True
    store_time: bool = True
    store_metadata: bool = True


@dataclass(frozen=True)
class ZarrBenchmarkResult:
    source_file: str
    dataset_index: int
    compression_profile: CompressionProfile
    chunk_strategy: ChunkStrategy
    store_intensity: bool
    store_time: bool
    store_metadata: bool
    source_sdt_size_bytes: int
    raw_nbytes: int
    zarr_size_bytes: int
    zarr_to_sdt_ratio: float
    zarr_to_raw_ratio: float
    write_time_s: float
    readback_time_s: float


def default_benchmark_cases() -> tuple[ZarrBenchmarkCase, ...]:
    return (
        ZarrBenchmarkCase("fast", "auto"),
        ZarrBenchmarkCase("balanced", "auto"),
        ZarrBenchmarkCase("max", "auto"),
        ZarrBenchmarkCase("balanced", "legacy_auto"),
        ZarrBenchmarkCase("balanced", "zarr_auto"),
        ZarrBenchmarkCase("balanced", "spatial_64"),
        ZarrBenchmarkCase("balanced", "spatial_128"),
        ZarrBenchmarkCase("balanced", "whole_if_possible"),
        ZarrBenchmarkCase("balanced", "auto", store_intensity=False),
    )


def benchmark_sdt_dataset_to_zarr(
    sdt_path: Path | str,
    output_root: Path | str,
    *,
    dataset_index: int = 0,
    cases: tuple[ZarrBenchmarkCase, ...] | None = None,
) -> tuple[ZarrBenchmarkResult, ...]:
    benchmark_cases = cases or default_benchmark_cases()
    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset_data = load_sdt_dataset(sdt_path, dataset_index=dataset_index)
    preview_data = build_preview_data(sdt_path, dataset_index=dataset_index)
    source_size = dataset_data.source_path.stat().st_size
    raw_nbytes = int(dataset_data.data.nbytes)

    results: list[ZarrBenchmarkResult] = []
    for case in benchmark_cases:
        options = ZarrExportOptions(
            compression_profile=case.compression_profile,
            chunk_strategy=case.chunk_strategy,
            overwrite=True,
            store_intensity=case.store_intensity,
            store_time=case.store_time,
            store_metadata=case.store_metadata,
        )
        case_name = (
            f"{case.compression_profile}_{case.chunk_strategy}_"
            f"i{int(case.store_intensity)}_t{int(case.store_time)}_m{int(case.store_metadata)}"
        )
        output_path = output_dir / f"{case_name}.zarr"

        start_write = time.perf_counter()
        export_dataset_to_zarr(dataset_data, preview_data, output_path, options)
        write_time_s = time.perf_counter() - start_write

        start_read = time.perf_counter()
        root = zarr.open_group(str(output_path), mode="r")
        _ = root["dataset_000/raw_counts"][:]
        readback_time_s = time.perf_counter() - start_read

        zarr_size = directory_size_bytes(output_path)
        results.append(
            ZarrBenchmarkResult(
                source_file=dataset_data.source_path.name,
                dataset_index=dataset_index,
                compression_profile=case.compression_profile,
                chunk_strategy=case.chunk_strategy,
                store_intensity=case.store_intensity,
                store_time=case.store_time,
                store_metadata=case.store_metadata,
                source_sdt_size_bytes=source_size,
                raw_nbytes=raw_nbytes,
                zarr_size_bytes=zarr_size,
                zarr_to_sdt_ratio=zarr_size / source_size if source_size else 0.0,
                zarr_to_raw_ratio=zarr_size / raw_nbytes if raw_nbytes else 0.0,
                write_time_s=write_time_s,
                readback_time_s=readback_time_s,
            )
        )
    return tuple(results)


def directory_size_bytes(path: Path | str) -> int:
    root = Path(path)
    return sum(file.stat().st_size for file in root.rglob("*") if file.is_file())
