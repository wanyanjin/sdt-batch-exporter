from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sdt_batch_exporter.core.axis_resolver import infer_axes
from sdt_batch_exporter.gui.preview_compositor import PreviewFigureOptions
from sdt_batch_exporter.gui.preview_options import (
    ColorBarOptions,
    PreviewDisplayOptions,
    ScaleBarOptions,
)
from sdt_batch_exporter.models.sdt import (
    PreviewData,
    SdtDatasetData,
    SdtDatasetSummary,
    SdtFileSummary,
)
from sdt_batch_exporter.models.workflow import (
    BatchExportRequest,
    DatasetExportRequest,
    DatasetExportResult,
    ExportOutputs,
    FileExportRequest,
    FileExportResult,
)
from sdt_batch_exporter.workflows.export_workflow import (
    export_batch,
    export_dataset,
    export_file,
)


def _dataset_data(path: Path, dataset_index: int = 0) -> SdtDatasetData:
    data = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)
    axis_info = infer_axes(data.shape, time_length=4)
    return SdtDatasetData(
        source_path=path,
        dataset_index=dataset_index,
        data=data,
        time=np.arange(4, dtype=np.float64),
        summary=SdtDatasetSummary(
            dataset_index=dataset_index,
            shape=data.shape,
            dtype=str(data.dtype),
            time_length=4,
            axis_info=axis_info,
        ),
    )


def _preview_data(dataset_data: SdtDatasetData) -> PreviewData:
    intensity = dataset_data.data.sum(axis=2)
    return PreviewData(
        source_path=dataset_data.source_path,
        dataset_index=dataset_data.dataset_index,
        raw_shape=dataset_data.summary.shape,
        dtype=dataset_data.summary.dtype,
        axis_info=dataset_data.summary.axis_info,
        time=dataset_data.time,
        intensity=intensity,
        global_decay=dataset_data.data.sum(axis=(0, 1)),
        intensity_stats={"shape": intensity.shape},
        metadata_summary={"dataset_index": dataset_data.dataset_index},
    )


def test_export_dataset_calls_all_exporters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("placeholder", encoding="utf-8")
    output_dir = tmp_path / "outputs"
    dataset_data = _dataset_data(source)
    preview_data = _preview_data(dataset_data)
    calls: list[str] = []

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.load_sdt_dataset",
        lambda path, dataset_index=0: dataset_data,
    )
    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.build_preview_from_dataset_data",
        lambda data: preview_data,
    )

    def _zarr(dataset: Any, preview: Any, output_path: Path | str, options: Any) -> Path:
        calls.append("zarr")
        path = Path(output_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _csv(preview: Any, output_path: Path | str, options: Any) -> Path:
        calls.append("csv")
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("csv", encoding="utf-8")
        return path

    def _txt(preview: Any, output_path: Path | str, options: Any) -> Path:
        calls.append("txt")
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("txt", encoding="utf-8")
        return path

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.export_dataset_to_zarr",
        _zarr,
    )
    monkeypatch.setattr("sdt_batch_exporter.workflows.export_workflow.export_intensity_csv", _csv)
    monkeypatch.setattr("sdt_batch_exporter.workflows.export_workflow.export_intensity_txt", _txt)

    result = export_dataset(
        DatasetExportRequest(
            source_path=source,
            output_dir=output_dir,
            outputs=ExportOutputs(zarr=True, csv=True, txt=True),
        )
    )

    assert result.status == "success"
    assert calls == ["zarr", "csv", "txt"]
    assert len(result.output_paths) == 3
    assert result.output_paths[0].name == "sample_dataset000.zarr"
    assert result.output_paths[1].name == "sample_dataset000_intensity.csv"
    assert result.output_paths[2].name == "sample_dataset000_intensity.txt"


def test_export_dataset_includes_preview_png(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("placeholder", encoding="utf-8")
    dataset_data = _dataset_data(source)
    preview_data = _preview_data(dataset_data)

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.load_sdt_dataset",
        lambda path, dataset_index=0: dataset_data,
    )
    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.build_preview_from_dataset_data",
        lambda data: preview_data,
    )
    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.export_dataset_to_zarr",
        lambda dataset, preview, output_path, options: Path(output_path),
    )
    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.export_preview_png_for_preview",
        lambda preview, output_path, options, overwrite=False: Path(output_path),
    )

    result = export_dataset(
        DatasetExportRequest(
            source_path=source,
            output_dir=tmp_path / "outputs",
            outputs=ExportOutputs(zarr=False, csv=False, txt=False, preview_png=True),
            preview_figure_options=PreviewFigureOptions(
                display=PreviewDisplayOptions(),
                scale_bar=ScaleBarOptions(),
                color_bar=ColorBarOptions(),
            ),
        )
    )

    assert result.status == "success"
    assert len(result.output_paths) == 1
    assert result.output_paths[0].name == "sample_dataset000_preview.png"


def test_export_dataset_returns_failed_on_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.load_sdt_dataset",
        lambda path, dataset_index=0: (_ for _ in ()).throw(ValueError("boom")),
    )
    result = export_dataset(DatasetExportRequest(source_path=source, output_dir=tmp_path))
    assert result.status == "failed"
    assert result.error_type == "ValueError"


def test_export_file_first_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.read_sdt_summary",
        lambda path: SdtFileSummary(
            source_path=source,
            source_file=source.name,
            file_size_bytes=1,
            dataset_count=3,
            datasets=(),
            sdt_summary_text="summary",
        ),
    )
    calls: list[int] = []

    def _export_dataset(request: DatasetExportRequest) -> DatasetExportResult:
        calls.append(request.dataset_index)
        return DatasetExportResult(
            source_path=request.source_path,
            dataset_index=request.dataset_index,
            status="success",
        )

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.export_dataset",
        _export_dataset,
    )
    result = export_file(FileExportRequest(source_path=source, output_dir=tmp_path))
    assert result.status == "success"
    assert calls == [0]


def test_export_file_indices_and_all_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.read_sdt_summary",
        lambda path: SdtFileSummary(
            source_path=source,
            source_file=source.name,
            file_size_bytes=1,
            dataset_count=4,
            datasets=(),
            sdt_summary_text="summary",
        ),
    )
    calls: list[int] = []

    def _export_dataset(request: DatasetExportRequest) -> DatasetExportResult:
        calls.append(request.dataset_index)
        return DatasetExportResult(
            source_path=request.source_path,
            dataset_index=request.dataset_index,
            status="success",
        )

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.export_dataset",
        _export_dataset,
    )

    indices_result = export_file(
        FileExportRequest(
            source_path=source,
            output_dir=tmp_path,
            dataset_selection="indices",
            dataset_indices=(1, 3),
        )
    )
    assert indices_result.status == "success"
    assert calls == [1, 3]

    calls.clear()
    all_result = export_file(
        FileExportRequest(
            source_path=source,
            output_dir=tmp_path,
            dataset_selection="all",
        )
    )
    assert all_result.status == "success"
    assert calls == [0, 1, 2, 3]


def test_export_batch_isolates_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sources = (
        tmp_path / "ok.sdt",
        tmp_path / "bad.sdt",
    )
    for path in sources:
        path.write_text("placeholder", encoding="utf-8")

    def _export_file(request: FileExportRequest) -> FileExportResult:
        if request.source_path.name == "bad.sdt":
            raise RuntimeError("failure")
        return FileExportResult(
            source_path=request.source_path,
            status="success",
            dataset_results=(),
        )

    monkeypatch.setattr("sdt_batch_exporter.workflows.export_workflow.export_file", _export_file)

    result = export_batch(
        BatchExportRequest(
            source_paths=sources,
            output_root=tmp_path / "batch_out",
        )
    )
    assert result.status == "failed"
    assert result.success_count == 1
    assert result.failed_count == 1
    assert result.skipped_count == 0


def test_export_batch_output_dir_is_per_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = (tmp_path / "a.sdt",)
    sources[0].write_text("placeholder", encoding="utf-8")
    captured: list[Path] = []

    def _export_file(request: FileExportRequest) -> FileExportResult:
        captured.append(request.output_dir)
        return FileExportResult(
            source_path=request.source_path,
            status="success",
            dataset_results=(),
        )

    monkeypatch.setattr("sdt_batch_exporter.workflows.export_workflow.export_file", _export_file)
    result = export_batch(BatchExportRequest(source_paths=sources, output_root=tmp_path / "out"))
    assert result.success_count == 1
    assert captured == [tmp_path / "out" / "a"]


def test_export_file_cleans_empty_output_dir_on_total_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("placeholder", encoding="utf-8")
    output_dir = tmp_path / "out" / "sample"

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.read_sdt_summary",
        lambda path: SdtFileSummary(
            source_path=source,
            source_file=source.name,
            file_size_bytes=1,
            dataset_count=1,
            datasets=(),
            sdt_summary_text="summary",
        ),
    )

    def _export_dataset(request: DatasetExportRequest) -> DatasetExportResult:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        return DatasetExportResult(
            source_path=request.source_path,
            dataset_index=request.dataset_index,
            status="failed",
            error_type="RuntimeError",
            error_message="locked",
        )

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.export_dataset",
        _export_dataset,
    )

    result = export_file(FileExportRequest(source_path=source, output_dir=output_dir))
    assert result.status == "failed"
    assert not output_dir.exists()


def test_export_file_keeps_output_dir_when_any_outputs_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("placeholder", encoding="utf-8")
    output_dir = tmp_path / "out" / "sample"

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.read_sdt_summary",
        lambda path: SdtFileSummary(
            source_path=source,
            source_file=source.name,
            file_size_bytes=1,
            dataset_count=1,
            datasets=(),
            sdt_summary_text="summary",
        ),
    )

    def _export_dataset(request: DatasetExportRequest) -> DatasetExportResult:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        marker = request.output_dir / "kept.txt"
        marker.write_text("keep", encoding="utf-8")
        return DatasetExportResult(
            source_path=request.source_path,
            dataset_index=request.dataset_index,
            status="failed",
            error_type="RuntimeError",
            error_message="locked",
        )

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.export_dataset",
        _export_dataset,
    )

    result = export_file(FileExportRequest(source_path=source, output_dir=output_dir))
    assert result.status == "failed"
    assert output_dir.exists()
    assert (output_dir / "kept.txt").exists()


def test_export_file_collapses_dataset_failure_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.read_sdt_summary",
        lambda path: SdtFileSummary(
            source_path=source,
            source_file=source.name,
            file_size_bytes=1,
            dataset_count=1,
            datasets=(),
            sdt_summary_text="summary",
        ),
    )
    monkeypatch.setattr(
        "sdt_batch_exporter.workflows.export_workflow.export_dataset",
        lambda request: DatasetExportResult(
            source_path=request.source_path,
            dataset_index=request.dataset_index,
            status="failed",
            error_type="RuntimeError",
            error_message="locked by OneDrive",
        ),
    )

    result = export_file(FileExportRequest(source_path=source, output_dir=tmp_path / "out"))
    assert result.status == "failed"
    assert result.error_type == "RuntimeError"
    assert result.error_message == "locked by OneDrive"
