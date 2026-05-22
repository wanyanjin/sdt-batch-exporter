"""Main window for SDT Batch Exporter."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sdt_batch_exporter.gui.export_labels import (
    FULL_CUBE_LABEL,
    FULL_CUBE_TOOLTIP,
    INTENSITY_CSV_LABEL,
    INTENSITY_CSV_TOOLTIP,
    INTENSITY_TXT_LABEL,
    INTENSITY_TXT_TOOLTIP,
    describe_output_path,
)
from sdt_batch_exporter.gui.export_preflight import run_export_preflight
from sdt_batch_exporter.gui.export_worker import ExportWorker
from sdt_batch_exporter.gui.file_table import FileTable
from sdt_batch_exporter.gui.metadata_panel import MetadataPanel
from sdt_batch_exporter.gui.png_exporter import export_preview_png_for_preview
from sdt_batch_exporter.gui.preview_options import (
    AnnotationStyle,
    ColorBarOptions,
    ColorBarPosition,
    ColormapName,
    DisplayMode,
    PreviewDisplayOptions,
    ScaleBarColor,
    ScaleBarOptions,
    ScaleBarPosition,
)
from sdt_batch_exporter.gui.preview_panel import PreviewPanel
from sdt_batch_exporter.gui.preview_worker import PreviewWorker
from sdt_batch_exporter.gui.request_builder import build_batch_request, parse_dataset_indices
from sdt_batch_exporter.models.export_options import ChunkStrategy, CompressionProfile
from sdt_batch_exporter.models.sdt import PreviewData
from sdt_batch_exporter.models.workflow import (
    BatchExportRequest,
    BatchExportResult,
    DatasetSelectionMode,
    FileExportResult,
)

_PREVIEW_CACHE_MAX = 5
_DISPLAY_MODES: tuple[DisplayMode, ...] = ("linear", "log1p")
_COLORMAPS: tuple[ColormapName, ...] = (
    "gray",
    "hot",
    "viridis",
    "inferno",
    "magma",
    "plasma",
    "turbo",
)
_SCALE_POSITIONS: tuple[ScaleBarPosition, ...] = (
    "bottom-left",
    "bottom-right",
    "top-left",
    "top-right",
)
_SCALE_COLORS: tuple[ScaleBarColor, ...] = ("white", "black")
_COLORBAR_POSITIONS: tuple[ColorBarPosition, ...] = ("right", "bottom")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SDT Batch Exporter")
        self.resize(1360, 840)
        self._worker_thread: QThread | None = None
        self._worker: ExportWorker | None = None
        self._preview_thread: QThread | None = None
        self._preview_worker: PreviewWorker | None = None
        self._pending_preview: tuple[Path, int] | None = None
        self._preview_cache: dict[tuple[Path, int], PreviewData] = {}

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        self._build_toolbar(root)
        self._build_main_splitter(root)
        self._build_bottom(root)
        self._connect_signals()
        self._connect_preview_controls()
        self._apply_preview_controls()

    def _build_toolbar(self, root: QVBoxLayout) -> None:
        bar = QHBoxLayout()
        self.add_files_button = QPushButton("Add Files")
        self.add_folder_button = QPushButton("Add Folder")
        self.clear_button = QPushButton("Clear List")
        bar.addWidget(self.add_files_button)
        bar.addWidget(self.add_folder_button)
        bar.addWidget(self.clear_button)
        bar.addStretch()
        bar.addWidget(QLabel("Output Dir:"))
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        self.select_output_button = QPushButton("Select…")
        bar.addWidget(self.output_dir_edit)
        bar.addWidget(self.select_output_button)
        root.addLayout(bar)

    def _build_main_splitter(self, root: QVBoxLayout) -> None:
        middle = QSplitter(Qt.Orientation.Horizontal)
        middle.addWidget(self._build_left_panel())
        self._preview_panel = PreviewPanel()
        middle.addWidget(self._preview_panel)
        self._metadata_panel = MetadataPanel()
        middle.addWidget(self._metadata_panel)
        middle.setSizes([360, 700, 260])
        root.addWidget(middle, stretch=3)

    def _build_left_panel(self) -> QWidget:
        group = QGroupBox("Options")
        layout = QVBoxLayout(group)
        tabs = QTabWidget(group)
        tabs.addTab(self._build_export_tab(), "Export")
        tabs.addTab(self._build_display_tab(), "Display")
        tabs.addTab(self._build_scale_tab(), "Scale")
        layout.addWidget(tabs)
        return group

    def _build_export_tab(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        self.zarr_checkbox = QCheckBox(FULL_CUBE_LABEL)
        self.csv_checkbox = QCheckBox(INTENSITY_CSV_LABEL)
        self.txt_checkbox = QCheckBox(INTENSITY_TXT_LABEL)
        self.preview_png_checkbox = QCheckBox("Preview PNG")
        self.zarr_checkbox.setChecked(True)
        self.csv_checkbox.setChecked(True)
        self.txt_checkbox.setChecked(False)
        self.preview_png_checkbox.setChecked(False)
        self.zarr_checkbox.setToolTip(FULL_CUBE_TOOLTIP)
        self.csv_checkbox.setToolTip(INTENSITY_CSV_TOOLTIP)
        self.txt_checkbox.setToolTip(INTENSITY_TXT_TOOLTIP)
        self.preview_png_checkbox.setToolTip(
            "Display-rendered preview PNG for reports and papers. "
            "Uses the Export Preview layout and does not change quantitative exports."
        )
        g.addWidget(self.zarr_checkbox, 0, 0, 1, 2)
        g.addWidget(self.csv_checkbox, 1, 0, 1, 2)
        g.addWidget(self.txt_checkbox, 2, 0, 1, 2)
        g.addWidget(self.preview_png_checkbox, 3, 0, 1, 2)
        g.addWidget(QLabel("Dataset"), 4, 0)
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItems(["first", "all", "indices"])
        g.addWidget(self.dataset_combo, 4, 1)
        self.indices_edit = QLineEdit()
        self.indices_edit.setPlaceholderText("0,2,3")
        self.indices_edit.setEnabled(False)
        g.addWidget(self.indices_edit, 5, 0, 1, 2)
        g.addWidget(QLabel("Compression"), 6, 0)
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["fast", "balanced", "max"])
        self.compression_combo.setCurrentText("balanced")
        g.addWidget(self.compression_combo, 6, 1)
        g.addWidget(QLabel("Chunk"), 7, 0)
        self.chunk_combo = QComboBox()
        self.chunk_combo.addItems(
            [
                "auto",
                "legacy_auto",
                "zarr_auto",
                "spatial_32",
                "spatial_64",
                "spatial_128",
                "whole_if_possible",
            ]
        )
        self.chunk_combo.setCurrentText("auto")
        g.addWidget(self.chunk_combo, 7, 1)
        self.overwrite_checkbox = QCheckBox("Overwrite Existing")
        g.addWidget(self.overwrite_checkbox, 8, 0, 1, 2)
        self.start_button = QPushButton("Start Export")
        self.export_current_preview_button = QPushButton("Export Current Preview PNG")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        g.addWidget(self.start_button, 9, 0, 1, 2)
        g.addWidget(self.export_current_preview_button, 10, 0, 1, 2)
        g.addWidget(self.progress_bar, 11, 0, 1, 2)
        g.setRowStretch(12, 1)
        return w

    def _build_display_tab(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.addWidget(QLabel("Colormap"), 0, 0)
        self.preview_colormap_combo = QComboBox()
        self.preview_colormap_combo.addItems(list(_COLORMAPS))
        g.addWidget(self.preview_colormap_combo, 0, 1)
        g.addWidget(QLabel("Display"), 1, 0)
        self.preview_display_combo = QComboBox()
        self.preview_display_combo.addItems(list(_DISPLAY_MODES))
        g.addWidget(self.preview_display_combo, 1, 1)
        g.addWidget(QLabel("Low %"), 2, 0)
        self.preview_low_percentile = QDoubleSpinBox()
        self.preview_low_percentile.setRange(0.0, 99.0)
        self.preview_low_percentile.setValue(2.0)
        g.addWidget(self.preview_low_percentile, 2, 1)
        g.addWidget(QLabel("High %"), 3, 0)
        self.preview_high_percentile = QDoubleSpinBox()
        self.preview_high_percentile.setRange(1.0, 100.0)
        self.preview_high_percentile.setValue(98.0)
        g.addWidget(self.preview_high_percentile, 3, 1)
        self.show_color_bar = QCheckBox("Show color bar")
        self.show_color_bar.setChecked(True)
        g.addWidget(self.show_color_bar, 4, 0, 1, 2)
        g.addWidget(QLabel("Color bar pos"), 5, 0)
        self.color_bar_position_combo = QComboBox()
        self.color_bar_position_combo.addItems(list(_COLORBAR_POSITIONS))
        self.color_bar_position_combo.setCurrentText("right")
        g.addWidget(self.color_bar_position_combo, 5, 1)
        g.addWidget(QLabel("Color bar label"), 6, 0)
        self.color_bar_label_edit = QLineEdit("PL intensity (a.u.)")
        g.addWidget(self.color_bar_label_edit, 6, 1)
        g.addWidget(QLabel("Color bar font"), 7, 0)
        self.color_bar_font_combo = QComboBox()
        self.color_bar_font_combo.addItems(
            ["Arial", "Microsoft YaHei", "SimHei", "Times New Roman"]
        )
        g.addWidget(self.color_bar_font_combo, 7, 1)
        g.addWidget(QLabel("Label size"), 8, 0)
        self.color_bar_label_size = QSpinBox()
        self.color_bar_label_size.setRange(8, 48)
        self.color_bar_label_size.setValue(12)
        g.addWidget(self.color_bar_label_size, 8, 1)
        g.addWidget(QLabel("Tick size"), 9, 0)
        self.color_bar_tick_size = QSpinBox()
        self.color_bar_tick_size.setRange(8, 32)
        self.color_bar_tick_size.setValue(11)
        g.addWidget(self.color_bar_tick_size, 9, 1)
        self.color_bar_bold = QCheckBox("Bold")
        self.color_bar_italic = QCheckBox("Italic")
        g.addWidget(self.color_bar_bold, 10, 0)
        g.addWidget(self.color_bar_italic, 10, 1)
        g.setRowStretch(11, 1)
        return w

    def _build_scale_tab(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        self.scale_enabled = QCheckBox("Show scale bar")
        g.addWidget(self.scale_enabled, 0, 0, 1, 2)
        g.addWidget(QLabel("Image width (um)"), 1, 0)
        self.scale_image_width_um = QDoubleSpinBox()
        self.scale_image_width_um.setRange(0.1, 1_000_000.0)
        self.scale_image_width_um.setValue(200.0)
        g.addWidget(self.scale_image_width_um, 1, 1)
        g.addWidget(QLabel("Scale length (um)"), 2, 0)
        self.scale_length_um = QDoubleSpinBox()
        self.scale_length_um.setRange(0.1, 1_000_000.0)
        self.scale_length_um.setValue(50.0)
        g.addWidget(self.scale_length_um, 2, 1)
        g.addWidget(QLabel("Position"), 3, 0)
        self.scale_position_combo = QComboBox()
        self.scale_position_combo.addItems(list(_SCALE_POSITIONS))
        self.scale_position_combo.setCurrentText("bottom-right")
        g.addWidget(self.scale_position_combo, 3, 1)
        g.addWidget(QLabel("Offset X"), 4, 0)
        self.scale_offset_x = QSpinBox()
        self.scale_offset_x.setRange(0, 10000)
        self.scale_offset_x.setValue(16)
        g.addWidget(self.scale_offset_x, 4, 1)
        g.addWidget(QLabel("Offset Y"), 5, 0)
        self.scale_offset_y = QSpinBox()
        self.scale_offset_y.setRange(0, 10000)
        self.scale_offset_y.setValue(16)
        g.addWidget(self.scale_offset_y, 5, 1)
        g.addWidget(QLabel("Color"), 6, 0)
        self.scale_color_combo = QComboBox()
        self.scale_color_combo.addItems(list(_SCALE_COLORS))
        g.addWidget(self.scale_color_combo, 6, 1)
        g.addWidget(QLabel("Thickness"), 7, 0)
        self.scale_thickness = QSpinBox()
        self.scale_thickness.setRange(1, 20)
        self.scale_thickness.setValue(3)
        g.addWidget(self.scale_thickness, 7, 1)
        self.scale_show_label = QCheckBox("Show label")
        self.scale_show_label.setChecked(True)
        g.addWidget(self.scale_show_label, 8, 0, 1, 2)
        g.addWidget(QLabel("Scale label font"), 9, 0)
        self.scale_font_combo = QComboBox()
        self.scale_font_combo.addItems(
            ["Arial", "Microsoft YaHei", "SimHei", "Times New Roman"]
        )
        g.addWidget(self.scale_font_combo, 9, 1)
        g.addWidget(QLabel("Scale label size"), 10, 0)
        self.scale_font_size = QSpinBox()
        self.scale_font_size.setRange(8, 48)
        self.scale_font_size.setValue(12)
        g.addWidget(self.scale_font_size, 10, 1)
        self.scale_bold = QCheckBox("Bold")
        self.scale_italic = QCheckBox("Italic")
        g.addWidget(self.scale_bold, 11, 0)
        g.addWidget(self.scale_italic, 11, 1)
        g.setRowStretch(12, 1)
        return w

    def _build_bottom(self, root: QVBoxLayout) -> None:
        bottom = QSplitter(Qt.Orientation.Vertical)
        self._file_table = FileTable()
        bottom.addWidget(self._file_table)
        logs_group = QGroupBox("Logs")
        logs_layout = QVBoxLayout(logs_group)
        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        logs_layout.addWidget(self.log_edit)
        bottom.addWidget(logs_group)
        bottom.setSizes([200, 140])
        root.addWidget(bottom, stretch=2)

    def _connect_signals(self) -> None:
        self.add_files_button.clicked.connect(self._add_files)
        self.add_folder_button.clicked.connect(self._add_folder)
        self.clear_button.clicked.connect(self._clear_files)
        self.select_output_button.clicked.connect(self._select_output_dir)
        self.start_button.clicked.connect(self._start_export)
        self.export_current_preview_button.clicked.connect(self._export_current_preview_png)
        self.dataset_combo.currentTextChanged.connect(self._on_dataset_combo_changed)
        self._file_table.file_selected.connect(self._on_file_selected)

    def _connect_preview_controls(self) -> None:
        for sig in [
            self.preview_colormap_combo.currentTextChanged,
            self.preview_display_combo.currentTextChanged,
            self.preview_low_percentile.valueChanged,
            self.preview_high_percentile.valueChanged,
            self.scale_enabled.stateChanged,
            self.scale_image_width_um.valueChanged,
            self.scale_length_um.valueChanged,
            self.scale_position_combo.currentTextChanged,
            self.scale_color_combo.currentTextChanged,
            self.scale_offset_x.valueChanged,
            self.scale_offset_y.valueChanged,
            self.scale_thickness.valueChanged,
            self.scale_show_label.stateChanged,
            self.show_color_bar.stateChanged,
            self.color_bar_position_combo.currentTextChanged,
            self.color_bar_label_edit.textChanged,
            self.color_bar_font_combo.currentTextChanged,
            self.color_bar_label_size.valueChanged,
            self.color_bar_tick_size.valueChanged,
            self.color_bar_bold.stateChanged,
            self.color_bar_italic.stateChanged,
            self.scale_font_combo.currentTextChanged,
            self.scale_font_size.valueChanged,
            self.scale_bold.stateChanged,
            self.scale_italic.stateChanged,
        ]:
            sig.connect(self._apply_preview_controls)

    def _apply_preview_controls(self) -> None:
        low = self.preview_low_percentile.value()
        high = self.preview_high_percentile.value()
        if high <= low:
            self._log(
                "Preview settings error: High percentile must be greater than low percentile."
            )
            return
        self._preview_panel.set_display_options(self._build_display_options())
        self._preview_panel.set_scale_bar_options(self._build_scale_bar_options())
        self._preview_panel.set_color_bar_options(self._build_color_bar_options())

    def _build_display_options(self) -> PreviewDisplayOptions:
        return PreviewDisplayOptions(
            display_mode=cast(DisplayMode, self.preview_display_combo.currentText()),
            colormap=cast(ColormapName, self.preview_colormap_combo.currentText()),
            low_percentile=self.preview_low_percentile.value(),
            high_percentile=self.preview_high_percentile.value(),
        )

    def _build_scale_bar_options(self) -> ScaleBarOptions:
        scale_style = AnnotationStyle(
            font_family=self.scale_font_combo.currentText(),
            font_size_px=self.scale_font_size.value(),
            bold=self.scale_bold.isChecked(),
            italic=self.scale_italic.isChecked(),
        )
        return ScaleBarOptions(
            enabled=self.scale_enabled.isChecked(),
            image_width_um=self.scale_image_width_um.value(),
            scale_length_um=self.scale_length_um.value(),
            position=cast(ScaleBarPosition, self.scale_position_combo.currentText()),
            offset_x_px=self.scale_offset_x.value(),
            offset_y_px=self.scale_offset_y.value(),
            color=cast(ScaleBarColor, self.scale_color_combo.currentText()),
            thickness_px=self.scale_thickness.value(),
            show_label=self.scale_show_label.isChecked(),
            label_style=scale_style,
        )

    def _build_color_bar_options(self) -> ColorBarOptions:
        color_bar_label_style = AnnotationStyle(
            font_family=self.color_bar_font_combo.currentText(),
            font_size_px=self.color_bar_label_size.value(),
            bold=self.color_bar_bold.isChecked(),
            italic=self.color_bar_italic.isChecked(),
        )
        color_bar_tick_style = AnnotationStyle(
            font_family=self.color_bar_font_combo.currentText(),
            font_size_px=self.color_bar_tick_size.value(),
            bold=False,
            italic=False,
        )
        return ColorBarOptions(
            enabled=self.show_color_bar.isChecked(),
            position=cast(ColorBarPosition, self.color_bar_position_combo.currentText()),
            label=self.color_bar_label_edit.text().strip() or "PL intensity (a.u.)",
            label_style=color_bar_label_style,
            tick_style=color_bar_tick_style,
        )

    def _add_files(self) -> None:
        selected, _ = QFileDialog.getOpenFileNames(
            self, "Select SDT Files", "", "SDT Files (*.sdt)"
        )
        for file_path in selected:
            self._file_table.add_path(Path(file_path))

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return
        paths = sorted(Path(folder).glob("*.sdt"))
        added = sum(1 for p in paths if self._file_table.add_path(p))
        self._log(f"Added {added} file(s) from folder: {folder}")

    def _clear_files(self) -> None:
        self._file_table.clear_paths()
        self._preview_panel.clear()
        self._metadata_panel.clear()
        self._pending_preview = None
        self._log("Cleared file list.")

    def _select_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.output_dir_edit.setText(folder)

    def _on_dataset_combo_changed(self, text: str) -> None:
        is_indices = text == "indices"
        self.indices_edit.setEnabled(is_indices)
        if not is_indices:
            self.indices_edit.clear()

    def _on_file_selected(self, source_path: Path, dataset_index: int) -> None:
        self._pending_preview = (source_path, dataset_index)
        cached = self._preview_cache.get((source_path, dataset_index))
        if cached is not None:
            self._preview_panel.set_preview(cached)
            self._metadata_panel.set_preview(cached)
            return
        if self._preview_thread is not None and self._preview_thread.isRunning():
            return
        self._start_preview_worker(source_path, dataset_index)

    def _start_preview_worker(self, source_path: Path, dataset_index: int) -> None:
        self._preview_thread = QThread(self)
        self._preview_worker = PreviewWorker(source_path, dataset_index)
        self._preview_worker.moveToThread(self._preview_thread)
        self._preview_thread.started.connect(self._preview_worker.run)
        self._preview_worker.preview_ready.connect(self._on_preview_done)
        self._preview_worker.preview_failed.connect(self._on_preview_failed)
        self._preview_worker.preview_ready.connect(self._preview_thread.quit)
        self._preview_worker.preview_failed.connect(self._preview_thread.quit)
        self._preview_thread.finished.connect(self._cleanup_preview_worker)
        self._preview_thread.start()

    def _on_preview_done(self, result: object) -> None:
        if not isinstance(result, PreviewData):
            return
        self._cache_preview(result)
        if self._pending_preview != (result.source_path, result.dataset_index):
            if self._pending_preview is not None:
                self._start_preview_worker(*self._pending_preview)
            return
        self._preview_panel.set_preview(result)
        self._metadata_panel.set_preview(result)
        self._file_table.set_status(result.source_path, "previewed")
        self._log(f"Preview ready: {result.source_path.name}")

    def _on_preview_failed(self, message: str) -> None:
        self._log(f"Preview failed: {message}")
        if self._pending_preview is not None:
            self._file_table.set_status(self._pending_preview[0], "failed")

    def _cleanup_preview_worker(self) -> None:
        self._preview_worker = None
        self._preview_thread = None

    def _cache_preview(self, preview: PreviewData) -> None:
        key = (preview.source_path, preview.dataset_index)
        if key in self._preview_cache:
            return
        if len(self._preview_cache) >= _PREVIEW_CACHE_MAX:
            del self._preview_cache[next(iter(self._preview_cache))]
        self._preview_cache[key] = preview

    def _build_request(self) -> BatchExportRequest:
        paths = self._file_table.get_paths()
        if not paths:
            raise ValueError("No .sdt files selected.")
        output_dir_text = self.output_dir_edit.text().strip()
        if not output_dir_text:
            raise ValueError("Output directory is required.")
        return build_batch_request(
            paths,
            Path(output_dir_text),
            export_zarr=self.zarr_checkbox.isChecked(),
            export_csv=self.csv_checkbox.isChecked(),
            export_txt=self.txt_checkbox.isChecked(),
            export_preview_png=self.preview_png_checkbox.isChecked(),
            dataset_selection=cast(DatasetSelectionMode, self.dataset_combo.currentText()),
            dataset_indices=parse_dataset_indices(self.indices_edit.text()),
            compression_profile=cast(CompressionProfile, self.compression_combo.currentText()),
            chunk_strategy=cast(ChunkStrategy, self.chunk_combo.currentText()),
            overwrite=self.overwrite_checkbox.isChecked(),
            preview_figure_options=self._preview_panel.export_figure_options(),
        )

    def _build_preview_png_default_name(self, source_path: Path, dataset_index: int) -> str:
        return f"{source_path.stem}_dataset{dataset_index:03d}_preview.png"

    def _export_current_preview_png(self) -> None:
        preview = self._preview_panel.current_preview()
        if preview is None or preview.intensity is None:
            QMessageBox.information(
                self,
                "No Preview",
                "Load a preview with intensity data before exporting a PNG.",
            )
            return
        initial_dir = self.output_dir_edit.text().strip()
        base_dir = Path(initial_dir) if initial_dir else preview.source_path.parent
        default_path = base_dir / self._build_preview_png_default_name(
            preview.source_path, preview.dataset_index
        )
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Current Preview PNG",
            str(default_path),
            "PNG Files (*.png)",
        )
        if not selected_path:
            return
        output_path = Path(selected_path)
        overwrite = output_path.exists()
        try:
            saved_path = export_preview_png_for_preview(
                preview,
                output_path,
                options=self._preview_panel.export_figure_options(),
                overwrite=overwrite,
            )
        except Exception as exc:
            self._log(f"Preview PNG export failed: {type(exc).__name__}: {exc}")
            QMessageBox.critical(self, "PNG Export Error", str(exc))
            return
        self._append_outputs(preview.source_path, ("Preview PNG",))
        self._log(f"Preview PNG saved: {saved_path}")

    def _start_export(self) -> None:
        try:
            request = self._build_request()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Input", str(exc))
            self._log(f"Input error: {exc}")
            return
        preflight = run_export_preflight(request)
        for warning in preflight.warnings:
            self._log(f"Preflight warning: {warning}")
        if not preflight.ok:
            self._log(f"Preflight failed: {preflight.message}")
            QMessageBox.warning(self, "Preflight Check Failed", preflight.message)
            return
        if preflight.warnings:
            QMessageBox.warning(
                self,
                "Preflight Warnings",
                "\n\n".join(preflight.warnings),
            )
        self.start_button.setEnabled(False)
        self.export_current_preview_button.setEnabled(False)
        self._worker_thread = QThread(self)
        self._worker = ExportWorker(request)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.log_message.connect(self._log)
        self._worker.progress_changed.connect(self._update_progress)
        self._worker.finished.connect(self._on_export_finished)
        self._worker.failed.connect(self._on_export_failed)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.failed.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._cleanup_worker)
        self._worker_thread.start()

    def _on_export_finished(self, result: object) -> None:
        if not isinstance(result, BatchExportResult):
            self.start_button.setEnabled(True)
            self.export_current_preview_button.setEnabled(True)
            return
        for file_result in result.file_results:
            self._file_table.set_status(file_result.source_path, file_result.status)
            labels: set[str] = set()
            for dataset_result in file_result.dataset_results:
                for output_path in dataset_result.output_paths:
                    labels.add(describe_output_path(output_path))
            self._file_table.set_outputs(
                file_result.source_path,
                ", ".join(sorted(labels)) if labels else "-",
            )
        self._log(self._format_batch_result_summary(result))
        failure_summary = self._format_failure_summary(result.file_results)
        if failure_summary:
            self._log(failure_summary)
        self.start_button.setEnabled(True)
        self.export_current_preview_button.setEnabled(True)

    def _on_export_failed(self, message: str) -> None:
        self._log(f"Worker failed: {message}")
        QMessageBox.critical(self, "Export Error", message)
        self.start_button.setEnabled(True)
        self.export_current_preview_button.setEnabled(True)

    def _update_progress(self, current: int, total: int) -> None:
        self.progress_bar.setRange(0, max(1, total))
        self.progress_bar.setValue(min(current, total))

    def _cleanup_worker(self) -> None:
        self._worker = None
        self._worker_thread = None

    def _append_outputs(self, path: Path, labels: tuple[str, ...]) -> None:
        current = self._file_table.get_outputs(path)
        merged = {label for label in current if label and label != "-"}
        merged.update(labels)
        self._file_table.set_outputs(path, ", ".join(sorted(merged)) if merged else "-")

    def _log(self, message: str) -> None:
        self.log_edit.appendPlainText(message)

    def _format_batch_result_summary(self, result: BatchExportResult) -> str:
        return (
            "Batch export finished. "
            f"Status: {result.status}. "
            f"Success: {result.success_count}, Failed: {result.failed_count}, "
            f"Skipped: {result.skipped_count}. Duration: {result.duration_s:.2f} s."
        )

    def _format_failure_summary(self, file_results: tuple[FileExportResult, ...]) -> str:
        lines = ["Failures:"]
        dataset_failure_count = 0
        file_failure_count = 0
        for file_result in file_results:
            for dataset_result in file_result.dataset_results:
                if dataset_result.status != "failed":
                    continue
                dataset_failure_count += 1
                lines.append(
                    f"- {dataset_result.source_path.name} dataset {dataset_result.dataset_index}: "
                    f"{dataset_result.error_type}: {dataset_result.error_message}"
                )
            if file_result.error_type and not file_result.dataset_results:
                file_failure_count += 1
                lines.append(
                    f"- {file_result.source_path.name}: "
                    f"{file_result.error_type}: {file_result.error_message}"
                )
        if dataset_failure_count == 0 and file_failure_count == 0:
            return ""
        return "\n".join(lines)
