"""Advanced preview panel powered by pyqtgraph."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QResizeEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTabWidget, QVBoxLayout, QWidget

from sdt_batch_exporter.gui.color_bar import ColorBarWidget
from sdt_batch_exporter.gui.preview_compositor import (
    PreviewFigureOptions,
    render_preview_figure_pixmap,
)
from sdt_batch_exporter.gui.preview_options import (
    ColorBarOptions,
    PreviewDisplayOptions,
    ScaleBarOptions,
)
from sdt_batch_exporter.gui.preview_rendering import (
    compute_percentile_levels,
    get_colormap_lut,
    prepare_display_array,
)
from sdt_batch_exporter.gui.scale_bar import (
    compute_scale_bar_anchor_position,
    compute_scale_bar_pixels,
)
from sdt_batch_exporter.models.sdt import PreviewData


class PreviewPanel(QWidget):
    """Display interactive and export-style intensity previews."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_preview: PreviewData | None = None
        self._current_image: np.ndarray | None = None
        self._display_options = PreviewDisplayOptions()
        self._scale_bar_options = ScaleBarOptions()
        self._color_bar_options = ColorBarOptions()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget(self)

        interactive_tab = QWidget(self)
        interactive_layout = QVBoxLayout(interactive_tab)
        image_row = QHBoxLayout()

        self._plot_widget = pg.PlotWidget(self)
        self._plot_widget.setBackground("#1a1a1a")
        self._plot_widget.setMenuEnabled(False)
        self._plot_widget.hideButtons()
        self._plot_widget.getPlotItem().hideAxis("left")
        self._plot_widget.getPlotItem().hideAxis("bottom")
        view_box = self._plot_widget.getViewBox()
        view_box.setAspectLocked(True)
        view_box.invertY(True)

        self._image_item = pg.ImageItem(axisOrder="row-major")
        self._plot_widget.getPlotItem().addItem(self._image_item)

        self._scale_line = pg.PlotDataItem()
        self._scale_text = pg.TextItem(anchor=(0.5, 1.2))
        self._plot_widget.getPlotItem().addItem(self._scale_line)
        self._plot_widget.getPlotItem().addItem(self._scale_text)
        self._clear_scale_bar()

        self._right_colorbar = ColorBarWidget(self)
        self._bottom_colorbar = ColorBarWidget(self)
        self._right_colorbar.hide()
        self._bottom_colorbar.hide()

        image_row.addWidget(self._plot_widget, stretch=1)
        image_row.addWidget(self._right_colorbar)
        interactive_layout.addLayout(image_row, stretch=1)
        interactive_layout.addWidget(self._bottom_colorbar)
        self._tabs.addTab(interactive_tab, "Interactive Preview")

        export_tab = QWidget(self)
        export_layout = QVBoxLayout(export_tab)
        self._export_preview_label = QLabel(self)
        self._export_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._export_preview_label.setMinimumHeight(320)
        self._export_preview_label.setStyleSheet("background: #111; border: 1px solid #333;")
        self._export_note_label = QLabel(
            "Export Preview shows the deterministic layout used for preview PNG export.",
            self,
        )
        self._export_note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._export_note_label.setStyleSheet("color: #666;")
        export_layout.addWidget(self._export_preview_label, stretch=1)
        export_layout.addWidget(self._export_note_label)
        self._tabs.addTab(export_tab, "Export Preview")

        self._stats_label = QLabel("", self)
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._note_label = QLabel(
            "Preview only. Exported CSV uses original integrated intensity values.", self
        )
        self._note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._note_label.setStyleSheet("color: #666;")

        layout.addWidget(self._tabs, stretch=1)
        layout.addWidget(self._stats_label)
        layout.addWidget(self._note_label)

    def set_preview(self, preview: PreviewData) -> None:
        self._current_preview = preview
        if preview.intensity is None:
            self.clear()
            self._stats_label.setText("No intensity data available")
            return
        self._current_image = np.asarray(preview.intensity)
        self._render_current()

    def set_display_options(self, options: PreviewDisplayOptions) -> None:
        self._display_options = options
        self._render_current()

    def set_scale_bar_options(self, options: ScaleBarOptions) -> None:
        self._scale_bar_options = options
        self._render_current()

    def set_color_bar_options(self, options: ColorBarOptions) -> None:
        self._color_bar_options = options
        self._render_current()

    def current_preview(self) -> PreviewData | None:
        return self._current_preview

    def export_figure_options(self) -> PreviewFigureOptions:
        return PreviewFigureOptions(
            display=self._display_options,
            scale_bar=self._scale_bar_options,
            color_bar=self._color_bar_options,
            background="black",
        )

    def clear(self) -> None:
        self._current_preview = None
        self._current_image = None
        self._image_item.clear()
        self._clear_scale_bar()
        self._right_colorbar.hide()
        self._bottom_colorbar.hide()
        self._export_preview_label.clear()
        self._stats_label.setText("")

    def _render_current(self) -> None:
        if self._current_preview is None or self._current_image is None:
            return
        try:
            display = prepare_display_array(self._current_image, self._display_options)
            low, high = compute_percentile_levels(
                display,
                self._display_options.low_percentile,
                self._display_options.high_percentile,
            )
            if high <= low:
                high = low + 1.0
            lut = get_colormap_lut(self._display_options.colormap)
            self._image_item.setLookupTable(lut)
            self._image_item.setImage(display, levels=(low, high), autoLevels=False)
            self._render_scale_bar(display.shape)
            self._render_color_bar(lut, low, high)
            self._render_export_preview()
            self._update_stats()
        except Exception as exc:
            self._image_item.clear()
            self._clear_scale_bar()
            self._right_colorbar.hide()
            self._bottom_colorbar.hide()
            self._export_preview_label.clear()
            self._stats_label.setText(f"Preview error: {exc}")

    def _render_scale_bar(self, image_shape: tuple[int, int]) -> None:
        options = self._scale_bar_options
        if not options.enabled or options.image_width_um is None:
            self._clear_scale_bar()
            return
        height, width = image_shape
        try:
            bar_px = compute_scale_bar_pixels(
                image_width_px=width,
                image_width_um=float(options.image_width_um),
                scale_length_um=float(options.scale_length_um),
            )
            x1, y1, x2, y2 = compute_scale_bar_anchor_position(
                image_width_px=width,
                image_height_px=height,
                scale_bar_width_px=bar_px,
                margin_x_px=max(0, options.offset_x_px),
                margin_y_px=max(0, options.offset_y_px),
                position=options.position,
            )
        except Exception as exc:
            self._clear_scale_bar()
            self._stats_label.setText(f"Scale bar: {exc}")
            return

        color = "w" if options.color == "white" else "k"
        pen = pg.mkPen(color=color, width=max(1, options.thickness_px))
        self._scale_line.setData([x1, x2], [y1, y2], pen=pen)
        if options.show_label:
            self._scale_text.setText(f"{options.scale_length_um:g} um", color=color)
            self._scale_text.setPos((x1 + x2) / 2.0, y1)
            font = QFont(options.label_style.font_family, options.label_style.font_size_px)
            font.setBold(options.label_style.bold)
            font.setItalic(options.label_style.italic)
            self._scale_text.setFont(font)
            self._scale_text.show()
        else:
            self._scale_text.hide()

    def _render_color_bar(self, lut: np.ndarray, low: float, high: float) -> None:
        if not self._color_bar_options.enabled:
            self._right_colorbar.hide()
            self._bottom_colorbar.hide()
            return
        label = self._color_bar_options.label
        if self._display_options.display_mode == "log1p":
            label = f"log1p({label})"
        if self._color_bar_options.position == "right":
            self._bottom_colorbar.hide()
            self._right_colorbar.set_colorbar(
                lut,
                low,
                high,
                label=label,
                orientation="vertical",
                label_style=self._color_bar_options.label_style,
                tick_style=self._color_bar_options.tick_style,
            )
            self._right_colorbar.show()
        else:
            self._right_colorbar.hide()
            self._bottom_colorbar.set_colorbar(
                lut,
                low,
                high,
                label=label,
                orientation="horizontal",
                label_style=self._color_bar_options.label_style,
                tick_style=self._color_bar_options.tick_style,
            )
            self._bottom_colorbar.show()

    def _render_export_preview(self) -> None:
        if self._current_image is None:
            self._export_preview_label.clear()
            return
        render_image = self._scaled_export_preview_image()
        pixmap = render_preview_figure_pixmap(
            render_image,
            self.export_figure_options(),
        )
        available = self._export_preview_label.contentsRect().adjusted(12, 12, -12, -12)
        scaled = pixmap.scaled(
            available.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._export_preview_label.setPixmap(scaled)

    def _scaled_export_preview_image(self) -> np.ndarray:
        assert self._current_image is not None
        height, width = self._current_image.shape
        target_rect = self._export_preview_label.contentsRect().adjusted(12, 12, -12, -12)
        target_width = max(1, target_rect.width())
        target_height = max(1, target_rect.height())
        scale_factor = int(
            min(
                max(1, target_width // max(1, width)),
                max(1, target_height // max(1, height)),
            )
        )
        scale_factor = max(1, min(scale_factor, 16))
        if scale_factor == 1:
            return self._current_image
        return np.repeat(
            np.repeat(self._current_image, scale_factor, axis=0),
            scale_factor,
            axis=1,
        )

    def _clear_scale_bar(self) -> None:
        self._scale_line.setData([], [])
        self._scale_text.hide()

    def _update_stats(self) -> None:
        preview = self._current_preview
        if preview is None or preview.intensity is None:
            return
        if preview.intensity_stats:
            stats = preview.intensity_stats
            mean_val = stats.get("mean", 0)
            mean_str = (
                f"{float(mean_val):.1f}" if isinstance(mean_val, (int, float)) else str(mean_val)
            )
            self._stats_label.setText(
                f"min={stats.get('min', '?')}  max={stats.get('max', '?')}  "
                f"mean={mean_str}  shape={preview.intensity.shape}"
            )
        else:
            self._stats_label.setText(f"shape={preview.intensity.shape}")

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_export_preview()
