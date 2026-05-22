"""Pure helpers for scale bar geometry in image coordinates."""

from __future__ import annotations

from sdt_batch_exporter.gui.preview_options import ScaleBarPosition


def compute_scale_bar_pixels(
    *,
    image_width_px: int,
    image_width_um: float,
    scale_length_um: float,
) -> int:
    """Convert requested physical scale length to pixel width."""
    if image_width_px <= 0:
        raise ValueError("image_width_px must be > 0")
    if image_width_um <= 0:
        raise ValueError("image_width_um must be > 0")
    if scale_length_um <= 0:
        raise ValueError("scale_length_um must be > 0")
    pixel_size_um = image_width_um / float(image_width_px)
    scale_px = int(round(scale_length_um / pixel_size_um))
    scale_px = max(1, scale_px)
    if scale_px > image_width_px:
        raise ValueError("scale bar too long for image width")
    return scale_px


def compute_scale_bar_anchor_position(
    *,
    image_width_px: int,
    image_height_px: int,
    scale_bar_width_px: int,
    margin_x_px: int,
    margin_y_px: int,
    position: ScaleBarPosition,
) -> tuple[int, int, int, int]:
    """Return clamped (x1, y1, x2, y2) in image coordinates."""
    if image_width_px <= 0 or image_height_px <= 0:
        raise ValueError("image dimensions must be > 0")
    if scale_bar_width_px <= 0:
        raise ValueError("scale_bar_width_px must be > 0")
    if scale_bar_width_px > image_width_px:
        raise ValueError("scale bar too long for image width")

    max_x_start = max(0, image_width_px - scale_bar_width_px)
    if position.endswith("left"):
        x1 = margin_x_px
    else:
        x1 = image_width_px - scale_bar_width_px - margin_x_px

    y = margin_y_px if position.startswith("top") else image_height_px - 1 - margin_y_px

    x1 = min(max(0, x1), max_x_start)
    x2 = x1 + scale_bar_width_px
    y = min(max(0, y), image_height_px - 1)
    return (x1, y, x2, y)
