"""PyInstaller entrypoint for the GUI."""

# ruff: noqa: I001, E402
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sdt_batch_exporter.gui.app import run_gui


raise SystemExit(run_gui())
