"""Single-dataset Zarr exporter for SDT preview pipeline."""

from __future__ import annotations

import contextlib
import os
import shutil
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from math import isqrt
from pathlib import Path
from typing import cast

import zarr
from numcodecs import Blosc

from sdt_batch_exporter import __version__
from sdt_batch_exporter.core.metadata_extractor import to_jsonable
from sdt_batch_exporter.models.export_options import (
    ChunkStrategy,
    CompressionProfile,
    ZarrExportOptions,
)
from sdt_batch_exporter.models.sdt import PreviewData, SdtDatasetData
from sdt_batch_exporter.storage.sdt_reader import build_preview_data, load_sdt_dataset

TARGET_CHUNK_BYTES = 8 * 1024 * 1024
MIN_CHUNK_BYTES = 1 * 1024 * 1024
MAX_CHUNK_BYTES = 32 * 1024 * 1024
MIN_SPATIAL_CHUNK = 16
MAX_SPATIAL_CHUNK = 128
MIN_TIME_CHUNK = 256
_STAGED_WRITE_RETRY_DELAYS_S = (0.2, 0.5, 1.0)


def export_dataset_to_zarr(
    dataset_data: SdtDatasetData,
    preview_data: PreviewData,
    output_path: Path | str,
    options: ZarrExportOptions | None = None,
) -> Path:
    export_options = options or ZarrExportOptions()
    _validate_dataset_preview_consistency(dataset_data, preview_data)

    output = Path(output_path)

    with _staged_write_context(output, overwrite=export_options.overwrite) as tmp_path:
        compressor = build_compressor(export_options.compression_profile)
        root = zarr.open_group(str(tmp_path), mode="w")
        root.attrs.update(
            {
                "schema_version": "0.2.0",
                "source_file": dataset_data.source_path.name,
                "source_path": str(dataset_data.source_path.resolve()),
                "export_time": datetime.now(UTC).isoformat(),
                "software_version": __version__,
                "dataset_count": 1,
                "exporter": "SDT Batch Exporter",
                "compression_profile": export_options.compression_profile,
                "chunk_strategy": export_options.chunk_strategy,
            }
        )

        if export_options.store_metadata:
            metadata_group = root.create_group("metadata")
            metadata_group.attrs["preview_summary"] = to_jsonable(preview_data.metadata_summary)
            metadata_group.attrs["export_options"] = to_jsonable(asdict(export_options))

        dataset_group = root.create_group("dataset_000")
        raw_chunks = choose_chunks(
            dataset_data.summary.shape,
            export_options.chunk_strategy,
            itemsize=dataset_data.data.dtype.itemsize,
        )
        raw_array = dataset_group.create_dataset(
            "raw_counts",
            data=dataset_data.data,
            chunks=raw_chunks,
            compressor=compressor,
        )
        raw_actual_chunks = _normalize_chunks(raw_array.chunks)

        if export_options.store_time and preview_data.time is not None:
            time_chunks = choose_chunks(
                preview_data.time.shape,
                export_options.chunk_strategy,
                itemsize=preview_data.time.dtype.itemsize,
            )
            dataset_group.create_dataset(
                "time",
                data=preview_data.time,
                chunks=time_chunks,
                compressor=compressor,
            )

        if export_options.store_intensity and preview_data.intensity is not None:
            intensity_chunks = choose_chunks(
                preview_data.intensity.shape,
                export_options.chunk_strategy,
                itemsize=preview_data.intensity.dtype.itemsize,
            )
            dataset_group.create_dataset(
                "intensity",
                data=preview_data.intensity,
                chunks=intensity_chunks,
                compressor=compressor,
            )

        axis_info = preview_data.axis_info
        dataset_attrs: dict[str, object] = {
            "dataset_index": dataset_data.dataset_index,
            "original_shape": list(dataset_data.summary.shape),
            "dtype": str(dataset_data.data.dtype),
            "axis_order": list(axis_info.axis_order),
            "time_axis_index": axis_info.time_axis_index,
            "spatial_axes": list(axis_info.spatial_axes),
            "time_axis_length": (
                preview_data.time.shape[0] if preview_data.time is not None else None
            ),
            "inference_source": axis_info.inference_source,
            "axis_inference_status": axis_info.axis_inference_status,
            "is_exportable_intensity": axis_info.is_exportable_intensity,
            "skipped_intensity_export": axis_info.skipped_intensity_export,
            "skip_reason": axis_info.skip_reason,
            "raw_counts_chunks": list(raw_actual_chunks),
            "chunk_strategy": export_options.chunk_strategy,
        }
        if len(dataset_data.summary.shape) == 2 and preview_data.intensity is not None:
            dataset_attrs["intensity_source"] = "source_2d_dataset"
        dataset_group.attrs.update(cast(dict[str, object], to_jsonable(dataset_attrs)))

    return output


def export_sdt_dataset_to_zarr(
    sdt_path: Path | str,
    output_path: Path | str,
    *,
    dataset_index: int = 0,
    options: ZarrExportOptions | None = None,
) -> Path:
    dataset_data = load_sdt_dataset(sdt_path, dataset_index=dataset_index)
    preview_data = build_preview_data(sdt_path, dataset_index=dataset_index)
    return export_dataset_to_zarr(dataset_data, preview_data, output_path, options)


def build_compressor(profile: CompressionProfile) -> Blosc:
    if profile == "fast":
        return Blosc(cname="lz4", clevel=1, shuffle=Blosc.BITSHUFFLE)
    if profile == "balanced":
        return Blosc(cname="zstd", clevel=5, shuffle=Blosc.BITSHUFFLE)
    if profile == "max":
        return Blosc(cname="zstd", clevel=9, shuffle=Blosc.BITSHUFFLE)
    raise ValueError(f"Unsupported compression profile: {profile}")


def choose_chunks(
    shape: tuple[int, ...],
    strategy: ChunkStrategy = "auto",
    *,
    itemsize: int | None = None,
) -> tuple[int, ...] | bool:
    if not shape:
        raise ValueError("shape must not be empty")
    if any(dimension <= 0 for dimension in shape):
        raise ValueError("shape dimensions must be positive")
    if itemsize is None:
        itemsize = 4
    if itemsize <= 0:
        raise ValueError("itemsize must be positive")

    if strategy == "zarr_auto":
        return True
    if strategy == "whole_if_possible":
        return shape
    if strategy == "legacy_auto":
        return _choose_legacy_auto_chunks(shape)

    if strategy in {"spatial_32", "spatial_64", "spatial_128"}:
        spatial_size = {"spatial_32": 32, "spatial_64": 64, "spatial_128": 128}[strategy]
        if len(shape) == 1:
            return (min(shape[0], spatial_size),)
        if len(shape) == 2:
            y, x = shape
            return (min(y, spatial_size), min(x, spatial_size))
        if len(shape) == 3:
            ny, nx, nt = shape
            return (min(ny, spatial_size), min(nx, spatial_size), nt)
        return tuple(min(dimension, spatial_size) for dimension in shape)

    if strategy != "auto":
        raise ValueError(f"Unsupported chunk strategy: {strategy}")

    if len(shape) == 1:
        target_elements = max(1, TARGET_CHUNK_BYTES // itemsize)
        return (min(shape[0], target_elements),)

    if len(shape) == 2:
        y, x = shape
        target_elements = max(1, TARGET_CHUNK_BYTES // itemsize)
        side = _clamp(isqrt(target_elements), 64, 512)
        if y <= side and x <= side:
            return shape
        return (min(y, side), min(x, side))

    if len(shape) == 3:
        ny, nx, nt = shape
        bytes_per_decay = max(1, nt * itemsize)
        target_pixels = max(1, TARGET_CHUNK_BYTES // bytes_per_decay)
        spatial_side = _clamp(isqrt(target_pixels), MIN_SPATIAL_CHUNK, MAX_SPATIAL_CHUNK)
        chunk_y = min(ny, spatial_side)
        chunk_x = min(nx, spatial_side)
        chunk_t = nt
        chunk_bytes = chunk_y * chunk_x * chunk_t * itemsize
        if chunk_bytes > MAX_CHUNK_BYTES:
            max_time = MAX_CHUNK_BYTES // max(1, chunk_y * chunk_x * itemsize)
            chunk_t = _clamp(max_time, MIN_TIME_CHUNK, nt)
        elif chunk_bytes < MIN_CHUNK_BYTES and chunk_y == ny and chunk_x == nx:
            chunk_t = min(nt, max(chunk_t, MIN_TIME_CHUNK))
        return (chunk_y, chunk_x, chunk_t)

    return tuple(min(dimension, 64) for dimension in shape)


def _choose_legacy_auto_chunks(shape: tuple[int, ...]) -> tuple[int, ...]:
    if len(shape) == 1:
        return (min(shape[0], 4096),)
    if len(shape) == 2:
        y, x = shape
        if y <= 512 and x <= 512:
            return shape
        return (min(y, 512), min(x, 512))
    if len(shape) == 3:
        ny, nx, nt = shape
        if ny <= 128 and nx <= 128:
            return shape
        if nt <= 1024:
            return (min(ny, 64), min(nx, 64), nt)
        return (min(ny, 32), min(nx, 32), min(nt, 1024))
    return tuple(min(dimension, 64) for dimension in shape)


def _normalize_chunks(chunks: tuple[int, ...] | None) -> tuple[int, ...]:
    if chunks is None:
        raise ValueError("zarr did not return concrete chunk metadata")
    return tuple(int(dimension) for dimension in chunks)


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _validate_dataset_preview_consistency(
    dataset_data: SdtDatasetData, preview_data: PreviewData
) -> None:
    if dataset_data.dataset_index != preview_data.dataset_index:
        raise ValueError("dataset_index mismatch between dataset_data and preview_data")
    if dataset_data.source_path.resolve() != preview_data.source_path.resolve():
        raise ValueError("source_path mismatch between dataset_data and preview_data")


@contextmanager
def _staged_write_context(
    output_path: Path, *, overwrite: bool
) -> Generator[Path, None, None]:
    """Write to a temp path; on success rename it to output_path.

    Keeps the old output intact until the new write completes, so a failed
    write never destroys existing data.
    """
    parent = output_path.parent
    uid = uuid.uuid4().hex[:12]
    tmp_path = parent / f".{output_path.name}.tmp-{uid}"
    bak_path = parent / f".{output_path.name}.bak-{uid}"
    target_exists = output_path.exists()

    if target_exists and not overwrite:
        raise FileExistsError(f"Output path already exists: {output_path}")

    try:
        yield tmp_path

        _commit_staged_write(
            output_path=output_path,
            tmp_path=tmp_path,
            bak_path=bak_path,
            target_exists=target_exists,
        )
        if bak_path.exists():
            _remove_tree_best_effort(bak_path)

    except BaseException as exc:
        # rollback: restore bak if we already moved it, then clean tmp
        if bak_path.exists() and not output_path.exists():
            with contextlib.suppress(OSError):
                os.replace(bak_path, output_path)
        _remove_tree_best_effort(tmp_path)
        if isinstance(exc, OSError) and not isinstance(exc, FileExistsError):
            raise RuntimeError(
                f"Staged write failed for {output_path}. "
                "The output directory may be locked by another application, "
                "OneDrive, or File Explorer. Close any viewer and retry."
            ) from exc
        raise


def _commit_staged_write(
    *,
    output_path: Path,
    tmp_path: Path,
    bak_path: Path,
    target_exists: bool,
) -> None:
    """Commit staged output with short retries for transient Windows locks."""
    for attempt_index, delay_s in enumerate((0.0, *_STAGED_WRITE_RETRY_DELAYS_S), start=1):
        if delay_s > 0.0:
            time.sleep(delay_s)
        try:
            if target_exists and not bak_path.exists():
                os.replace(output_path, bak_path)
            os.replace(tmp_path, output_path)
            return
        except (PermissionError, OSError) as exc:
            if attempt_index >= len(_STAGED_WRITE_RETRY_DELAYS_S) + 1:
                raise RuntimeError(
                    f"Staged write commit failed for {output_path} after {attempt_index} attempts. "
                    "The output path may be locked by OneDrive, File Explorer, "
                    "or another sync/preview process."
                ) from exc


def _remove_tree_best_effort(path: Path) -> None:
    try:
        if path.exists():
            shutil.rmtree(path)
    except OSError:
        pass
