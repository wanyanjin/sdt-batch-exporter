"""GUI labels and output-path descriptions for export semantics."""

from __future__ import annotations

from pathlib import Path

FULL_CUBE_LABEL = "Full TRPL cube (.zarr)"
INTENSITY_CSV_LABEL = "Integrated intensity (.csv)"
INTENSITY_TXT_LABEL = "Integrated intensity (.txt)"

FULL_CUBE_TOOLTIP = (
    "Export full x-y-t photon-count cube as compressed Zarr for downstream analysis."
)
INTENSITY_CSV_TOOLTIP = (
    "Export integrated 2D PL intensity matrix as CSV for plotting in Origin, Excel, MATLAB, etc."
)
INTENSITY_TXT_TOOLTIP = "Export integrated 2D PL intensity matrix as tab-delimited TXT."


def describe_output_path(path: Path) -> str:
    """Return a user-friendly output type label for *path*."""
    name = path.name.lower()
    if name.endswith("_preview.png"):
        return "Preview PNG"
    if name.endswith("_preview.png.meta.json"):
        return "Preview PNG Metadata"
    if name.endswith(".zarr"):
        return "Full cube"
    if name.endswith("_intensity.csv"):
        return "Intensity CSV"
    if name.endswith("_intensity.txt"):
        return "Intensity TXT"
    if name.endswith(".meta.json"):
        return "Metadata JSON"
    return "Output"
