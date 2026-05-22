"""Preflight checks for GUI export requests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sdt_batch_exporter.models.workflow import BatchExportRequest

_MAX_CONFLICTS = 10
_SYNC_PATH_MARKERS = ("onedrive", "dropbox", "googledrive", "google drive", "icloud")


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    conflicts: tuple[Path, ...] = ()
    warnings: tuple[str, ...] = ()
    message: str = ""


def predict_output_paths_for_gui(
    source_path: Path,
    output_root: Path,
    *,
    dataset_selection: str,
    dataset_indices: tuple[int, ...],
    export_zarr: bool,
    export_csv: bool,
    export_txt: bool,
    export_preview_png: bool,
) -> tuple[Path, ...]:
    """Predict deterministic output paths used by current workflow naming."""
    output_dir = output_root / source_path.stem
    indices: tuple[int, ...]
    if dataset_selection == "first":
        indices = (0,)
    elif dataset_selection == "indices":
        indices = dataset_indices
    else:
        # selection='all' depends on runtime dataset count; use dataset000 as a shallow signal only.
        indices = (0,)

    predicted: list[Path] = []
    for idx in indices:
        prefix = f"{source_path.stem}_dataset{idx:03d}"
        if export_zarr:
            predicted.append(output_dir / f"{prefix}.zarr")
        if export_csv:
            csv_path = output_dir / f"{prefix}_intensity.csv"
            predicted.append(csv_path)
            predicted.append(Path(f"{csv_path}.meta.json"))
        if export_txt:
            txt_path = output_dir / f"{prefix}_intensity.txt"
            predicted.append(txt_path)
            predicted.append(Path(f"{txt_path}.meta.json"))
        if export_preview_png:
            png_path = output_dir / f"{prefix}_preview.png"
            predicted.append(png_path)
            predicted.append(Path(f"{png_path}.meta.json"))
    return tuple(predicted)


def run_export_preflight(request: BatchExportRequest) -> PreflightResult:
    """Validate request and detect likely output conflicts before starting worker."""
    if not request.source_paths:
        return PreflightResult(ok=False, message="No .sdt files selected.")
    if not str(request.output_root).strip():
        return PreflightResult(ok=False, message="Output directory is required.")
    if not (
        request.outputs.zarr
        or request.outputs.csv
        or request.outputs.txt
        or request.outputs.preview_png
    ):
        return PreflightResult(ok=False, message="At least one output type must be enabled.")
    if request.dataset_selection == "indices" and not request.dataset_indices:
        return PreflightResult(ok=False, message="Dataset selection 'indices' requires indices.")

    warnings: list[str] = []
    try:
        request.output_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return PreflightResult(ok=False, message=f"Unable to create output directory: {exc}")

    if _looks_like_synced_directory(request.output_root):
        warnings.append(
            "Output directory appears to be inside a synced folder (for example OneDrive). "
            "Zarr is a directory-based output and may fail intermittently if the folder is "
            "locked by a sync client or File Explorer preview. Prefer a local non-synced "
            "output directory, "
            "or pause syncing and close the folder window before exporting."
        )

    if request.dataset_selection == "all":
        warnings.append(
            "Dataset selection is 'all'; output conflicts will be checked during export."
        )

    conflicts: list[Path] = []
    for source_path in request.source_paths:
        for candidate in predict_output_paths_for_gui(
            source_path,
            request.output_root,
            dataset_selection=request.dataset_selection,
            dataset_indices=request.dataset_indices,
            export_zarr=request.outputs.zarr,
            export_csv=request.outputs.csv,
            export_txt=request.outputs.txt,
            export_preview_png=request.outputs.preview_png,
        ):
            if candidate.exists():
                conflicts.append(candidate)
                if len(conflicts) >= _MAX_CONFLICTS:
                    break
        if len(conflicts) >= _MAX_CONFLICTS:
            break

    if conflicts and not request.zarr_options.overwrite:
        return PreflightResult(
            ok=False,
            conflicts=tuple(conflicts),
            warnings=tuple(warnings),
            message=(
                "Some output paths already exist. "
                "Enable overwrite or choose another output directory."
            ),
        )
    if conflicts and request.zarr_options.overwrite:
        warnings.append("Existing outputs were found and will be overwritten.")

    return PreflightResult(ok=True, conflicts=tuple(conflicts), warnings=tuple(warnings))


def _looks_like_synced_directory(path: Path) -> bool:
    normalized_parts = [part.casefold() for part in path.parts]
    return any(marker in part for marker in _SYNC_PATH_MARKERS for part in normalized_parts)
