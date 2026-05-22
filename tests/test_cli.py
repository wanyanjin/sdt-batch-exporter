from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sdt_batch_exporter.cli import collect_sdt_paths, main
from sdt_batch_exporter.models.workflow import BatchExportResult


def test_collect_sdt_paths_file(tmp_path: Path) -> None:
    file_path = tmp_path / "a.sdt"
    file_path.write_text("x", encoding="utf-8")
    assert collect_sdt_paths(file_path) == (file_path,)


def test_collect_sdt_paths_non_sdt_file(tmp_path: Path) -> None:
    file_path = tmp_path / "a.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        collect_sdt_paths(file_path)


def test_collect_sdt_paths_directory_non_recursive(tmp_path: Path) -> None:
    a = tmp_path / "a.sdt"
    a.write_text("x", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    b = nested / "b.sdt"
    b.write_text("x", encoding="utf-8")
    assert collect_sdt_paths(tmp_path) == (a,)


def test_collect_sdt_paths_directory_recursive(tmp_path: Path) -> None:
    a = tmp_path / "a.sdt"
    a.write_text("x", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    b = nested / "b.sdt"
    b.write_text("x", encoding="utf-8")
    assert collect_sdt_paths(tmp_path, recursive=True) == (a, b)


def test_collect_sdt_paths_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        collect_sdt_paths(tmp_path)


def test_cli_help() -> None:
    code = main(["--help"])
    assert code == 0


def test_cli_parses_and_calls_export_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("x", encoding="utf-8")
    captured = {}

    def _export_batch(request: Any) -> BatchExportResult:
        captured["request"] = request
        return BatchExportResult(
            status="success",
            file_results=(),
            success_count=1,
            failed_count=0,
            skipped_count=0,
            duration_s=0.1,
        )

    monkeypatch.setattr("sdt_batch_exporter.cli.export_batch", _export_batch)
    code = main([str(source), "-o", str(tmp_path / "out"), "--zarr"])
    assert code == 0
    request = captured["request"]
    assert request.dataset_selection == "first"
    assert request.outputs.zarr is True
    assert request.outputs.csv is False
    assert request.outputs.txt is False


def test_cli_indices_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("x", encoding="utf-8")
    captured = {}

    def _export_batch(request: Any) -> BatchExportResult:
        captured["request"] = request
        return BatchExportResult(
            status="success",
            file_results=(),
            success_count=1,
            failed_count=0,
            skipped_count=0,
            duration_s=0.1,
        )

    monkeypatch.setattr("sdt_batch_exporter.cli.export_batch", _export_batch)
    code = main(
        [
            str(source),
            "-o",
            str(tmp_path / "out"),
            "--dataset",
            "indices",
            "--indices",
            "0,2",
        ]
    )
    assert code == 0
    assert captured["request"].dataset_indices == (0, 2)


def test_cli_indices_missing(tmp_path: Path) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("x", encoding="utf-8")
    code = main([str(source), "-o", str(tmp_path / "out"), "--dataset", "indices"])
    assert code == 2


def test_cli_no_output_format_enabled(tmp_path: Path) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("x", encoding="utf-8")
    code = main([str(source), "-o", str(tmp_path / "out"), "--no-zarr"])
    assert code == 2


def test_cli_failed_workflow_returns_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("x", encoding="utf-8")

    def _export_batch(_request: Any) -> BatchExportResult:
        return BatchExportResult(
            status="failed",
            file_results=(),
            success_count=0,
            failed_count=1,
            skipped_count=0,
            duration_s=0.1,
        )

    monkeypatch.setattr("sdt_batch_exporter.cli.export_batch", _export_batch)
    code = main([str(source), "-o", str(tmp_path / "out"), "--zarr"])
    assert code == 1


def test_cli_writes_summary_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "sample.sdt"
    source.write_text("x", encoding="utf-8")
    summary_path = tmp_path / "result" / "summary.json"

    def _export_batch(_request: Any) -> BatchExportResult:
        return BatchExportResult(
            status="success",
            file_results=(),
            success_count=1,
            failed_count=0,
            skipped_count=0,
            duration_s=0.1,
        )

    monkeypatch.setattr("sdt_batch_exporter.cli.export_batch", _export_batch)
    code = main(
        [
            str(source),
            "-o",
            str(tmp_path / "out"),
            "--summary-json",
            str(summary_path),
        ]
    )
    assert code == 0
    assert summary_path.exists()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
