from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
ENTRYPOINT = PROJECT_ROOT / "packaging" / "gui_entry.py"
DIST_ROOT = PROJECT_ROOT / "dist"
BUILD_ROOT = PROJECT_ROOT / "build"
EXE_DIR_NAME = "SDT-Batch-Exporter"
EXE_NAME = "SDT-Batch-Exporter.exe"


def _read_version() -> str:
    with PYPROJECT.open("rb") as handle:
        data = tomllib.load(handle)
    version = data["project"]["version"]
    if not isinstance(version, str):
        raise TypeError("project.version must be a string")
    return version


def _read_readme_txt() -> str:
    readme = PROJECT_ROOT / "README.md"
    return readme.read_text(encoding="utf-8")


def _build_pyinstaller_command() -> list[str]:
    return [
        sys.executable,
        "-I",
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        EXE_DIR_NAME,
        "--collect-all",
        "PySide6",
        "--collect-all",
        "pyqtgraph",
        str(ENTRYPOINT),
    ]


def _run_pyinstaller() -> None:
    command = _build_pyinstaller_command()
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONUSERBASE"] = str(PROJECT_ROOT / ".tmp-test" / "py-userbase")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True, env=env)


def _staging_dir() -> Path:
    return DIST_ROOT / EXE_DIR_NAME


def _prepare_release_files(staging_dir: Path) -> None:
    shutil.copy2(PROJECT_ROOT / "LICENSE", staging_dir / "LICENSE")
    (staging_dir / "README.txt").write_text(_read_readme_txt(), encoding="utf-8")


def _create_zip(staging_dir: Path, version: str) -> Path:
    zip_path = DIST_ROOT / f"{EXE_DIR_NAME}-v{version}-Windows.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(staging_dir.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(DIST_ROOT))
    return zip_path


def build_windows_exe() -> Path:
    if os.name != "nt":
        raise RuntimeError("Windows EXE packaging is intended to run on Windows.")

    version = _read_version()
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    if BUILD_ROOT.exists():
        shutil.rmtree(BUILD_ROOT)
    staging_dir = _staging_dir()
    if staging_dir.exists():
        shutil.rmtree(staging_dir)

    _run_pyinstaller()
    if not staging_dir.exists():
        raise FileNotFoundError(f"PyInstaller output directory not found: {staging_dir}")
    if not (staging_dir / EXE_NAME).exists():
        raise FileNotFoundError(f"Expected executable not found: {staging_dir / EXE_NAME}")

    _prepare_release_files(staging_dir)
    return _create_zip(staging_dir, version)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the Windows GUI package.")
    return parser


def main(argv: list[str] | None = None) -> int:
    _build_argument_parser().parse_args(argv)
    zip_path = build_windows_exe()
    print(f"Built Windows release archive: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
