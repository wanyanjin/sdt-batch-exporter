"""Paper-style color bar widget and helpers for preview display."""

from __future__ import annotations

from math import isfinite
from typing import Literal

import numpy as np
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QFont, QImage, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from sdt_batch_exporter.gui.preview_options import AnnotationStyle

Orientation = Literal["vertical", "horizontal"]


def render_colorbar_gradient(
    lut: np.ndarray, length: int, thickness: int, orientation: Orientation
) -> np.ndarray:
    """Render RGBA gradient image from LUT."""
    if lut.ndim != 2 or lut.shape[0] < 2 or lut.shape[1] not in (3, 4):
        raise ValueError("lut must be (N,3) or (N,4)")
    if length <= 0 or thickness <= 0:
        raise ValueError("length and thickness must be > 0")
    table = lut.astype(np.uint8, copy=False)
    if table.shape[1] == 3:
        alpha = np.full((table.shape[0], 1), 255, dtype=np.uint8)
        table = np.concatenate([table, alpha], axis=1)
    idx = np.linspace(0, table.shape[0] - 1, num=length).round().astype(int)
    line = table[idx]
    if orientation == "vertical":
        grad = np.repeat(line[::-1, None, :], thickness, axis=1)
    else:
        grad = np.repeat(line[None, :, :], thickness, axis=0)
    return grad


def format_colorbar_value(value: float) -> str:
    """Format color-bar limits for compact annotation display."""
    if not isfinite(value):
        return "nan"
    if abs(value) >= 1000:
        return f"{value:.0f}"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.3g}"


def compute_vertical_colorbar_layout(
    width: int,
    height: int,
    *,
    gradient_width: int = 20,
    tick_height: int = 18,
    label_gap: int = 10,
) -> tuple[QRect, QRect, QRect, QRectF]:
    """Compute compact vertical color-bar geometry with top/bottom ticks."""
    grad_x = 6
    grad_y = tick_height + 4
    grad_height = max(80, height - (tick_height * 2 + 8))
    gradient_rect = QRect(grad_x, grad_y, gradient_width, grad_height)
    top_tick_rect = QRect(grad_x - 8, 0, gradient_width + 16, tick_height)
    bottom_tick_rect = QRect(grad_x - 8, grad_y + grad_height + 2, gradient_width + 16, tick_height)
    label_height = float(grad_height)
    label_rect = QRectF(
        float(grad_x + gradient_width + label_gap),
        float(grad_y),
        label_height,
        28.0,
    )
    return gradient_rect, top_tick_rect, bottom_tick_rect, label_rect


class ColorBarWidget(QWidget):
    """Painter-based color bar preview for paper/export style layouts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lut: np.ndarray | None = None
        self._low: float = 0.0
        self._high: float = 1.0
        self._label: str = "PL intensity (a.u.)"
        self._orientation: Orientation = "vertical"
        self._label_style = AnnotationStyle()
        self._tick_style = AnnotationStyle(font_family="Arial", font_size_px=11)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(84)
        self.setMinimumHeight(220)

    def set_colorbar(
        self,
        lut: np.ndarray,
        low: float,
        high: float,
        *,
        label: str,
        orientation: Orientation = "vertical",
        label_style: AnnotationStyle | None = None,
        tick_style: AnnotationStyle | None = None,
    ) -> None:
        self._lut = np.asarray(lut, dtype=np.uint8)
        self._low = float(low)
        self._high = float(high)
        self._label = label
        self._orientation = orientation
        self._label_style = label_style or AnnotationStyle()
        self._tick_style = tick_style or AnnotationStyle(font_family="Arial", font_size_px=11)
        if orientation == "vertical":
            self.setMinimumWidth(84)
            self.setMinimumHeight(220)
        else:
            self.setMinimumWidth(220)
            self.setMinimumHeight(72)
        self.update()

    def paintEvent(self, event: object) -> None:
        del event
        if self._lut is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._orientation == "vertical":
            self._paint_vertical(painter)
        else:
            self._paint_horizontal(painter)
        painter.end()

    def _paint_vertical(self, painter: QPainter) -> None:
        if self._lut is None:
            return
        rect = self.rect().adjusted(0, 0, -1, -1)
        gradient_rect, top_tick_rect, bottom_tick_rect, label_rect = (
            compute_vertical_colorbar_layout(
                rect.width(),
                rect.height(),
            )
        )
        grad = render_colorbar_gradient(
            self._lut,
            gradient_rect.height(),
            gradient_rect.width(),
            "vertical",
        )
        image = QImage(
            grad.data,
            grad.shape[1],
            grad.shape[0],
            grad.shape[1] * 4,
            QImage.Format.Format_RGBA8888,
        ).copy()
        tick_font = QFont(self._tick_style.font_family, self._tick_style.font_size_px)
        tick_font.setBold(self._tick_style.bold)
        tick_font.setItalic(self._tick_style.italic)
        painter.setFont(tick_font)
        painter.drawImage(gradient_rect, image)
        painter.drawRect(gradient_rect)
        painter.drawText(
            top_tick_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            format_colorbar_value(self._high),
        )
        painter.drawText(
            bottom_tick_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            format_colorbar_value(self._low),
        )
        label_font = QFont(self._label_style.font_family, self._label_style.font_size_px)
        label_font.setBold(self._label_style.bold)
        label_font.setItalic(self._label_style.italic)
        painter.setFont(label_font)
        painter.save()
        painter.translate(label_rect.x(), rect.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(-label_rect.width() / 2, -14, label_rect.width(), label_rect.height()),
            Qt.AlignmentFlag.AlignCenter,
            self._label,
        )
        painter.restore()

    def _paint_horizontal(self, painter: QPainter) -> None:
        if self._lut is None:
            return
        rect = self.rect().adjusted(0, 0, -1, -1)
        grad_width = max(120, rect.width() - 24)
        grad_height = 18
        grad_x = max(8, (rect.width() - grad_width) // 2)
        grad_y = 22
        grad = render_colorbar_gradient(self._lut, grad_width, grad_height, "horizontal")
        image = QImage(
            grad.data,
            grad.shape[1],
            grad.shape[0],
            grad.shape[1] * 4,
            QImage.Format.Format_RGBA8888,
        ).copy()
        tick_font = QFont(self._tick_style.font_family, self._tick_style.font_size_px)
        tick_font.setBold(self._tick_style.bold)
        tick_font.setItalic(self._tick_style.italic)
        painter.setFont(tick_font)
        painter.drawImage(QRect(grad_x, grad_y, grad_width, grad_height), image)
        painter.drawRect(QRect(grad_x, grad_y, grad_width, grad_height))
        painter.drawText(
            QRect(grad_x, 0, 60, 18),
            Qt.AlignmentFlag.AlignLeft,
            format_colorbar_value(self._low),
        )
        painter.drawText(
            QRect(grad_x + grad_width - 60, 0, 60, 18),
            Qt.AlignmentFlag.AlignRight,
            format_colorbar_value(self._high),
        )
        label_font = QFont(self._label_style.font_family, self._label_style.font_size_px)
        label_font.setBold(self._label_style.bold)
        label_font.setItalic(self._label_style.italic)
        painter.setFont(label_font)
        painter.drawText(
            QRect(0, grad_y + grad_height + 6, rect.width(), 18),
            Qt.AlignmentFlag.AlignCenter,
            self._label,
        )
