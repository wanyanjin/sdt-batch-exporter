"""Deterministic export-preview compositor for future PNG rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap

from sdt_batch_exporter.gui.color_bar import (
    compute_vertical_colorbar_layout,
    format_colorbar_value,
    render_colorbar_gradient,
)
from sdt_batch_exporter.gui.preview_options import (
    AnnotationStyle,
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


@dataclass(frozen=True)
class PreviewFigureOptions:
    display: PreviewDisplayOptions
    scale_bar: ScaleBarOptions
    color_bar: ColorBarOptions
    background: Literal["black", "white"] = "black"
    canvas_margin_px: int = 24


@dataclass(frozen=True)
class PreviewFigureLayout:
    canvas_width: int
    canvas_height: int
    image_rect: tuple[int, int, int, int]
    color_bar_rect: tuple[int, int, int, int] | None
    scale_bar_line: tuple[int, int, int, int] | None


def _to_qimage_rgb(image: NDArray[np.uint8]) -> QImage:
    height, width, _ = image.shape
    return QImage(image.data, width, height, width * 3, QImage.Format.Format_RGB888).copy()


def _build_font(style: AnnotationStyle) -> QFont:
    font = QFont(style.font_family, style.font_size_px)
    font.setBold(style.bold)
    font.setItalic(style.italic)
    return font


def _display_colorbar_label(options: PreviewFigureOptions) -> str:
    label = options.color_bar.label
    if options.display.display_mode == "log1p":
        return f"log1p({label})"
    return label


def compute_preview_figure_layout(
    image_shape: tuple[int, int],
    options: PreviewFigureOptions,
) -> PreviewFigureLayout:
    """Compute deterministic export-preview layout in top-left image coordinates."""
    image_height, image_width = image_shape
    margin = options.canvas_margin_px
    canvas_width = image_width + margin * 2
    canvas_height = image_height + margin * 2
    color_bar_rect: tuple[int, int, int, int] | None = None

    if options.color_bar.enabled:
        if options.color_bar.position == "right":
            color_bar_width = 84
            color_bar_height = min(max(180, image_height), 260)
            canvas_width += color_bar_width
            color_bar_rect = (
                margin + image_width + 12,
                margin + max(0, (image_height - color_bar_height) // 2),
                color_bar_width - 16,
                color_bar_height,
            )
        else:
            color_bar_height = 60
            color_bar_width = min(max(180, image_width), 320)
            canvas_height += color_bar_height
            color_bar_rect = (
                margin + max(0, (image_width - color_bar_width) // 2),
                margin + image_height + 10,
                color_bar_width,
                color_bar_height - 16,
            )

    scale_bar_line: tuple[int, int, int, int] | None = None
    if options.scale_bar.enabled and options.scale_bar.image_width_um is not None:
        scale_px = compute_scale_bar_pixels(
            image_width_px=image_width,
            image_width_um=float(options.scale_bar.image_width_um),
            scale_length_um=float(options.scale_bar.scale_length_um),
        )
        x1, y1, x2, y2 = compute_scale_bar_anchor_position(
            image_width_px=image_width,
            image_height_px=image_height,
            scale_bar_width_px=scale_px,
            margin_x_px=max(0, options.scale_bar.offset_x_px),
            margin_y_px=max(0, options.scale_bar.offset_y_px),
            position=options.scale_bar.position,
        )
        scale_bar_line = (margin + x1, margin + y1, margin + x2, margin + y2)

    return PreviewFigureLayout(
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        image_rect=(margin, margin, image_width, image_height),
        color_bar_rect=color_bar_rect,
        scale_bar_line=scale_bar_line,
    )


def render_preview_figure(
    intensity: NDArray[np.generic],
    options: PreviewFigureOptions,
) -> NDArray[np.uint8]:
    """Render a deterministic export preview as RGB uint8."""
    if intensity.ndim != 2:
        raise ValueError(f"Expected 2D intensity array, got {intensity.ndim}D")

    source = np.asarray(intensity)
    display = prepare_display_array(source, options.display)
    low, high = compute_percentile_levels(
        display,
        options.display.low_percentile,
        options.display.high_percentile,
    )
    if not np.isfinite(low):
        low = 0.0
    if not np.isfinite(high) or high <= low:
        high = low + 1.0

    clipped = np.clip((display - low) / (high - low), 0.0, 1.0)
    lut = get_colormap_lut(options.display.colormap)
    image_rgb = lut[:, :3][np.rint(clipped * 255.0).astype(np.uint8)]

    layout = compute_preview_figure_layout(display.shape, options)
    canvas = np.empty((layout.canvas_height, layout.canvas_width, 3), dtype=np.uint8)
    if options.background == "black":
        background = np.array([0, 0, 0], dtype=np.uint8)
    else:
        background = np.array([255, 255, 255], dtype=np.uint8)
    canvas[:, :] = background

    image_x, image_y, image_w, image_h = layout.image_rect
    canvas[image_y : image_y + image_h, image_x : image_x + image_w] = image_rgb

    qimage = _to_qimage_rgb(canvas)
    painter = QPainter(qimage)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    fg = QColor("#ffffff" if options.background == "black" else "#000000")
    painter.setPen(QPen(fg))
    painter.setFont(_build_font(options.color_bar.tick_style))

    if layout.scale_bar_line is not None:
        x1, y1, x2, y2 = layout.scale_bar_line
        pen = QPen(QColor("#ffffff" if options.scale_bar.color == "white" else "#000000"))
        pen.setWidth(max(1, options.scale_bar.thickness_px))
        painter.setPen(pen)
        painter.drawLine(x1, y1, x2, y2)
        if options.scale_bar.show_label:
            painter.setFont(_build_font(options.scale_bar.label_style))
            painter.drawText(
                QRect(min(x1, x2) - 20, y1 - 28, abs(x2 - x1) + 40, 20),
                Qt.AlignmentFlag.AlignCenter,
                f"{options.scale_bar.scale_length_um:g} um",
            )
            painter.setFont(_build_font(options.color_bar.tick_style))
        painter.setPen(QPen(fg))

    if layout.color_bar_rect is not None:
        x, y, w, h = layout.color_bar_rect
        if options.color_bar.position == "right":
            gradient_rect, top_tick_rect, bottom_tick_rect, label_rect = (
                compute_vertical_colorbar_layout(w, h)
            )
            grad = render_colorbar_gradient(
                lut,
                gradient_rect.height(),
                gradient_rect.width(),
                "vertical",
            )
            grad_image = QImage(
                grad.data,
                grad.shape[1],
                grad.shape[0],
                grad.shape[1] * 4,
                QImage.Format.Format_RGBA8888,
            ).copy()
            painter.setFont(_build_font(options.color_bar.tick_style))
            draw_gradient_rect = gradient_rect.translated(x, y)
            painter.drawImage(draw_gradient_rect, grad_image)
            painter.drawRect(draw_gradient_rect)
            painter.drawText(
                top_tick_rect.translated(x, y),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                format_colorbar_value(high),
            )
            painter.drawText(
                bottom_tick_rect.translated(x, y),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                format_colorbar_value(low),
            )
            painter.setFont(_build_font(options.color_bar.label_style))
            painter.save()
            painter.translate(x + label_rect.x(), y + h / 2)
            painter.rotate(-90)
            painter.drawText(
                QRectF(-label_rect.width() / 2, -14, label_rect.width(), label_rect.height()),
                Qt.AlignmentFlag.AlignCenter,
                _display_colorbar_label(options),
            )
            painter.restore()
        else:
            grad_h = 18
            grad = render_colorbar_gradient(lut, w, grad_h, "horizontal")
            grad_image = QImage(
                grad.data,
                grad.shape[1],
                grad.shape[0],
                grad.shape[1] * 4,
                QImage.Format.Format_RGBA8888,
            ).copy()
            painter.setFont(_build_font(options.color_bar.tick_style))
            painter.drawImage(QRect(x, y + 18, w, grad_h), grad_image)
            painter.drawRect(QRect(x, y + 18, w, grad_h))
            painter.drawText(
                QRect(x, y, 60, 18),
                Qt.AlignmentFlag.AlignLeft,
                format_colorbar_value(low),
            )
            painter.drawText(
                QRect(x + w - 60, y, 60, 18),
                Qt.AlignmentFlag.AlignRight,
                format_colorbar_value(high),
            )
            painter.setFont(_build_font(options.color_bar.label_style))
            painter.drawText(
                QRect(x, y + 38, w, 18),
                Qt.AlignmentFlag.AlignCenter,
                _display_colorbar_label(options),
            )

    painter.end()
    ptr = qimage.bits()
    arr = np.frombuffer(ptr, dtype=np.uint8)
    bytes_per_line = qimage.bytesPerLine()
    shaped = arr.reshape((qimage.height(), bytes_per_line))
    rgb = shaped[:, : qimage.width() * 3].reshape((qimage.height(), qimage.width(), 3))
    return rgb.copy()


def render_preview_figure_pixmap(
    intensity: NDArray[np.generic],
    options: PreviewFigureOptions,
) -> QPixmap:
    """Render export preview directly to QPixmap for QLabel display."""
    return QPixmap.fromImage(_to_qimage_rgb(render_preview_figure(intensity, options)))
