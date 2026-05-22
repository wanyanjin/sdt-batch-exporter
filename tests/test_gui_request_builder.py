from __future__ import annotations

from pathlib import Path

import pytest

from sdt_batch_exporter.gui.preview_compositor import PreviewFigureOptions
from sdt_batch_exporter.gui.preview_options import (
    ColorBarOptions,
    PreviewDisplayOptions,
    ScaleBarOptions,
)
from sdt_batch_exporter.gui.request_builder import build_batch_request, parse_dataset_indices


def test_build_batch_request_maps_fields() -> None:
    request = build_batch_request(
        source_paths=(Path("/tmp/a.sdt"),),
        output_root=Path("/tmp/out"),
        export_zarr=True,
        export_csv=True,
        export_txt=False,
        export_preview_png=True,
        dataset_selection="indices",
        dataset_indices=(0, 2),
        compression_profile="balanced",
        chunk_strategy="auto",
        overwrite=True,
        preview_figure_options=PreviewFigureOptions(
            display=PreviewDisplayOptions(),
            scale_bar=ScaleBarOptions(),
            color_bar=ColorBarOptions(),
        ),
    )
    assert request.outputs.zarr is True
    assert request.outputs.csv is True
    assert request.outputs.txt is False
    assert request.outputs.preview_png is True
    assert request.dataset_selection == "indices"
    assert request.dataset_indices == (0, 2)
    assert request.zarr_options.compression_profile == "balanced"
    assert request.zarr_options.chunk_strategy == "auto"
    assert request.zarr_options.overwrite is True
    assert request.text_options.overwrite is True
    assert request.preview_figure_options is not None


def test_build_batch_request_rejects_all_outputs_disabled() -> None:
    with pytest.raises(ValueError, match="At least one output format"):
        build_batch_request(
            source_paths=(Path("/tmp/a.sdt"),),
            output_root=Path("/tmp/out"),
            export_zarr=False,
            export_csv=False,
            export_txt=False,
            export_preview_png=False,
            dataset_selection="first",
            dataset_indices=(),
            compression_profile="balanced",
            chunk_strategy="auto",
            overwrite=False,
            preview_figure_options=None,
        )


def test_parse_dataset_indices() -> None:
    assert parse_dataset_indices("0,2,5") == (0, 2, 5)
    assert parse_dataset_indices("  ") == ()


def test_parse_dataset_indices_invalid() -> None:
    with pytest.raises(ValueError):
        parse_dataset_indices("0,-1")
    with pytest.raises(ValueError):
        parse_dataset_indices("0,a")
