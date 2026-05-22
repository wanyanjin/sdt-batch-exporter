from __future__ import annotations

from pathlib import Path

from sdt_batch_exporter.gui.export_preflight import (
    predict_output_paths_for_gui,
    run_export_preflight,
)
from sdt_batch_exporter.models.export_options import TextExportOptions, ZarrExportOptions
from sdt_batch_exporter.models.workflow import BatchExportRequest, ExportOutputs


def _make_request(
    tmp_path: Path,
    *,
    sources: tuple[Path, ...] = (Path("a.sdt"),),
    output_root: Path | None = None,
    selection: str = "first",
    indices: tuple[int, ...] = (),
    zarr: bool = True,
    csv: bool = True,
    txt: bool = False,
    preview_png: bool = False,
    overwrite: bool = False,
) -> BatchExportRequest:
    return BatchExportRequest(
        source_paths=sources,
        output_root=output_root or (tmp_path / "out"),
        dataset_selection=selection,  # type: ignore[arg-type]
        dataset_indices=indices,
        outputs=ExportOutputs(zarr=zarr, csv=csv, txt=txt, preview_png=preview_png),
        zarr_options=ZarrExportOptions(overwrite=overwrite),
        text_options=TextExportOptions(overwrite=overwrite),
    )


def test_preflight_requires_input_files(tmp_path: Path) -> None:
    result = run_export_preflight(_make_request(tmp_path, sources=()))
    assert result.ok is False


def test_preflight_requires_output_type(tmp_path: Path) -> None:
    result = run_export_preflight(
        _make_request(tmp_path, zarr=False, csv=False, txt=False, preview_png=False)
    )
    assert result.ok is False


def test_predict_paths_first_selection(tmp_path: Path) -> None:
    paths = predict_output_paths_for_gui(
        Path("sample.sdt"),
        tmp_path / "out",
        dataset_selection="first",
        dataset_indices=(),
        export_zarr=True,
        export_csv=True,
        export_txt=True,
        export_preview_png=False,
    )
    assert any(str(p).endswith("_dataset000.zarr") for p in paths)
    assert any(str(p).endswith("_dataset000_intensity.csv") for p in paths)
    assert any(str(p).endswith("_dataset000_intensity.txt") for p in paths)


def test_preflight_conflict_blocks_when_no_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "out"
    target = out / "a" / "a_dataset000.zarr"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")
    result = run_export_preflight(_make_request(tmp_path, output_root=out, overwrite=False))
    assert result.ok is False
    assert result.conflicts


def test_preflight_conflict_warns_when_overwrite_enabled(tmp_path: Path) -> None:
    out = tmp_path / "out"
    target = out / "a" / "a_dataset000_intensity.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")
    result = run_export_preflight(_make_request(tmp_path, output_root=out, overwrite=True))
    assert result.ok is True
    assert result.conflicts
    assert result.warnings


def test_predict_paths_indices_selection(tmp_path: Path) -> None:
    paths = predict_output_paths_for_gui(
        Path("sample.sdt"),
        tmp_path / "out",
        dataset_selection="indices",
        dataset_indices=(1, 3),
        export_zarr=True,
        export_csv=False,
        export_txt=False,
        export_preview_png=False,
    )
    assert len(paths) == 2
    assert any(str(p).endswith("_dataset001.zarr") for p in paths)
    assert any(str(p).endswith("_dataset003.zarr") for p in paths)


def test_preflight_all_selection_warning(tmp_path: Path) -> None:
    result = run_export_preflight(_make_request(tmp_path, selection="all"))
    assert result.ok is True
    assert result.warnings


def test_predict_paths_include_preview_png(tmp_path: Path) -> None:
    paths = predict_output_paths_for_gui(
        Path("sample.sdt"),
        tmp_path / "out",
        dataset_selection="first",
        dataset_indices=(),
        export_zarr=False,
        export_csv=False,
        export_txt=False,
        export_preview_png=True,
    )
    assert any(str(p).endswith("_dataset000_preview.png") for p in paths)
    assert any(str(p).endswith("_dataset000_preview.png.meta.json") for p in paths)


def test_preflight_warns_for_onedrive_output_root(tmp_path: Path) -> None:
    out = tmp_path / "OneDrive" / "exports"
    result = run_export_preflight(_make_request(tmp_path, output_root=out))
    assert result.ok is True
    assert any("OneDrive" in warning or "synced folder" in warning for warning in result.warnings)


def test_preflight_does_not_warn_for_regular_output_root(tmp_path: Path) -> None:
    out = tmp_path / "exports"
    result = run_export_preflight(_make_request(tmp_path, output_root=out))
    assert result.ok is True
    assert not any("synced folder" in warning for warning in result.warnings)
