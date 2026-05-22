"""Deterministic PNG export helpers for preview figures."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PySide6.QtGui import QImage

from sdt_batch_exporter.core.metadata_extractor import to_jsonable
from sdt_batch_exporter.gui.preview_compositor import (
    PreviewFigureOptions,
    render_preview_figure,
)
from sdt_batch_exporter.models.sdt import PreviewData
from sdt_batch_exporter.storage.sdt_reader import build_preview_data


def build_preview_png_metadata(
    *,
    source_path: Path | str | None,
    dataset_index: int,
    options: PreviewFigureOptions,
    preview_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build JSON-serializable sidecar metadata for preview PNG export."""
    resolved_source = Path(source_path) if source_path is not None else None
    metadata = {
        "source_file": resolved_source.name if resolved_source is not None else None,
        "source_path": str(resolved_source) if resolved_source is not None else None,
        "dataset_index": dataset_index,
        "preview_only": True,
        "note": "PNG is display-rendered preview. Quantitative exports use Zarr/CSV/TXT.",
        "display": asdict(options.display),
        "scale_bar": asdict(options.scale_bar),
        "color_bar": asdict(options.color_bar),
        "background": options.background,
        "canvas_margin_px": options.canvas_margin_px,
    }
    if preview_metadata:
        metadata["preview_metadata"] = preview_metadata
    jsonable = to_jsonable(metadata)
    if not isinstance(jsonable, dict):
        raise TypeError("Preview PNG metadata must be a dictionary.")
    return jsonable


def save_preview_png(
    intensity: NDArray[np.generic],
    output_path: Path | str,
    options: PreviewFigureOptions,
    *,
    metadata: dict[str, object] | None = None,
    overwrite: bool = False,
) -> Path:
    """Render and save preview PNG plus sidecar metadata JSON."""
    destination = Path(output_path)
    if destination.suffix.lower() != ".png":
        raise ValueError(f"Output path must end with .png: {destination}")

    sidecar_path = Path(f"{destination}.meta.json")
    if not overwrite and (destination.exists() or sidecar_path.exists()):
        raise FileExistsError(f"Preview PNG already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_preview_figure(np.asarray(intensity), options)
    image = QImage(
        rendered.data,
        rendered.shape[1],
        rendered.shape[0],
        rendered.shape[1] * 3,
        QImage.Format.Format_RGB888,
    ).copy()
    if not image.save(str(destination)):
        raise OSError(f"Failed to save preview PNG: {destination}")

    sidecar_payload = metadata if metadata is not None else {}
    sidecar_path.write_text(
        json.dumps(to_jsonable(sidecar_payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destination


def export_preview_png_for_sdt(
    source_path: Path | str,
    output_path: Path | str,
    *,
    dataset_index: int = 0,
    options: PreviewFigureOptions,
    overwrite: bool = False,
) -> Path:
    """Load preview intensity from an SDT file and export a rendered PNG."""
    preview = build_preview_data(source_path, dataset_index)
    if preview.intensity is None:
        raise ValueError(
            "No exportable intensity is available for "
            f"dataset {dataset_index}: {preview.source_path}"
        )
    metadata = build_preview_png_metadata(
        source_path=preview.source_path,
        dataset_index=preview.dataset_index,
        options=options,
        preview_metadata=preview.metadata_summary,
    )
    return save_preview_png(
        preview.intensity,
        output_path,
        options,
        metadata=metadata,
        overwrite=overwrite,
    )


def export_preview_png_for_preview(
    preview: PreviewData,
    output_path: Path | str,
    *,
    options: PreviewFigureOptions,
    overwrite: bool = False,
) -> Path:
    """Save a preview PNG from already-built preview data."""
    if preview.intensity is None:
        raise ValueError(
            f"No exportable intensity is available for dataset {preview.dataset_index}: "
            f"{preview.source_path}"
        )
    metadata = build_preview_png_metadata(
        source_path=preview.source_path,
        dataset_index=preview.dataset_index,
        options=options,
        preview_metadata=preview.metadata_summary,
    )
    return save_preview_png(
        preview.intensity,
        output_path,
        options,
        metadata=metadata,
        overwrite=overwrite,
    )
