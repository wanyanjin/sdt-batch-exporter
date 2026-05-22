"""Command-line interface for SDT batch export workflows."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import cast

from sdt_batch_exporter.core.metadata_extractor import to_jsonable
from sdt_batch_exporter.models.export_options import TextExportOptions, ZarrExportOptions
from sdt_batch_exporter.models.workflow import BatchExportRequest, BatchExportResult, ExportOutputs
from sdt_batch_exporter.workflows.export_workflow import export_batch


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, int):
            return code
        return 2

    try:
        source_paths = collect_sdt_paths(Path(args.input), recursive=args.recursive)
        outputs = ExportOutputs(zarr=args.zarr, csv=args.csv, txt=args.txt)
        if not (outputs.zarr or outputs.csv or outputs.txt):
            raise ValueError("At least one output format must be enabled.")

        dataset_indices = _parse_indices(args.indices)
        if args.dataset == "indices" and not dataset_indices:
            raise ValueError("--dataset indices requires non-empty --indices")
        if args.dataset != "indices" and args.indices:
            raise ValueError("--indices can only be used with --dataset indices")

        request = BatchExportRequest(
            source_paths=source_paths,
            output_root=Path(args.output),
            dataset_selection=args.dataset,
            dataset_indices=dataset_indices,
            outputs=outputs,
            zarr_options=ZarrExportOptions(
                compression_profile=args.compression,
                chunk_strategy=args.chunk,
                overwrite=args.overwrite,
            ),
            text_options=TextExportOptions(overwrite=args.overwrite),
        )
        result = export_batch(request)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_batch_summary(result))
    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(batch_result_to_dict(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return 0 if result.status == "success" else 1


def collect_sdt_paths(input_path: Path, *, recursive: bool = False) -> tuple[Path, ...]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
    if input_path.is_file():
        if input_path.suffix.lower() != ".sdt":
            raise ValueError(f"Input file is not an .sdt file: {input_path}")
        return (input_path,)
    if not input_path.is_dir():
        raise ValueError(f"Input path is neither a file nor a directory: {input_path}")

    pattern = "**/*.sdt" if recursive else "*.sdt"
    paths = sorted(path for path in input_path.glob(pattern) if path.is_file())
    if not paths:
        raise ValueError(f"No .sdt files found under: {input_path}")
    return tuple(paths)


def format_batch_summary(result: BatchExportResult) -> str:
    lines = [
        "SDT Batch Exporter",
        "",
        f"Status: {result.status}",
        f"Files: {len(result.file_results)}",
        f"Success: {result.success_count}",
        f"Failed: {result.failed_count}",
        f"Skipped: {result.skipped_count}",
        f"Duration: {result.duration_s:.2f} s",
    ]

    output_paths = [
        output_path
        for file_result in result.file_results
        for dataset_result in file_result.dataset_results
        for output_path in dataset_result.output_paths
    ]
    if output_paths:
        lines.append("")
        lines.append("Outputs:")
        lines.extend(f"- {path}" for path in output_paths)

    failures = [
        (
            dataset_result.source_path,
            dataset_result.dataset_index,
            dataset_result.error_type,
            dataset_result.error_message,
        )
        for file_result in result.file_results
        for dataset_result in file_result.dataset_results
        if dataset_result.status == "failed"
    ]
    file_failures = [
        (file_result.source_path, file_result.error_type, file_result.error_message)
        for file_result in result.file_results
        if file_result.error_type is not None
    ]
    if failures or file_failures:
        lines.append("")
        lines.append("Failures:")
        for source_path, dataset_index, error_type, error_message in failures:
            lines.append(f"- {source_path} dataset {dataset_index}: {error_type}: {error_message}")
        for source_path, error_type, error_message in file_failures:
            lines.append(f"- {source_path}: {error_type}: {error_message}")

    return "\n".join(lines)


def batch_result_to_dict(result: BatchExportResult) -> dict[str, object]:
    raw_dict = asdict(result)
    converted = to_jsonable(raw_dict)
    if not isinstance(converted, dict):
        raise TypeError("Batch result serialization failed to produce a dictionary")
    return cast(dict[str, object], converted)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdt-export",
        description="Batch export .sdt files to Zarr / CSV / TXT via backend workflows.",
    )
    parser.add_argument("input", help="Input .sdt file or directory")
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output root directory (required)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan input directory for .sdt files",
    )
    parser.add_argument(
        "--zarr",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable Zarr export (default: enabled)",
    )
    parser.add_argument("--csv", action="store_true", help="Enable CSV intensity export")
    parser.add_argument("--txt", action="store_true", help="Enable TXT intensity export")
    parser.add_argument(
        "--dataset",
        choices=("first", "all", "indices"),
        default="first",
        help="Dataset selection mode (default: first)",
    )
    parser.add_argument(
        "--indices",
        default="",
        help="Comma-separated dataset indices for --dataset indices (e.g. 0,2,3)",
    )
    parser.add_argument(
        "--compression",
        choices=("fast", "balanced", "max"),
        default="balanced",
        help="Zarr compression profile (default: balanced)",
    )
    parser.add_argument(
        "--chunk",
        choices=(
            "auto",
            "legacy_auto",
            "zarr_auto",
            "spatial_32",
            "spatial_64",
            "spatial_128",
            "whole_if_possible",
        ),
        default="auto",
        help="Zarr chunk strategy (default: auto)",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    parser.add_argument(
        "--summary-json",
        default="",
        help="Optional path to write batch summary JSON",
    )
    return parser


def _parse_indices(indices_arg: str) -> tuple[int, ...]:
    if not indices_arg.strip():
        return ()
    values: list[int] = []
    for token in indices_arg.split(","):
        part = token.strip()
        if not part:
            raise ValueError("Invalid --indices format")
        try:
            value = int(part)
        except ValueError as exc:
            raise ValueError("Invalid --indices format") from exc
        if value < 0:
            raise ValueError("Dataset indices must be non-negative integers")
        values.append(value)
    return tuple(values)
