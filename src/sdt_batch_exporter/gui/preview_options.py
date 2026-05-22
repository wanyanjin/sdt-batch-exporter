"""Display options for advanced GUI preview rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DisplayMode = Literal["linear", "log1p"]
ColormapName = Literal["gray", "hot", "viridis", "inferno", "magma", "plasma", "turbo"]
ScaleBarPosition = Literal["bottom-left", "bottom-right", "top-left", "top-right"]
ScaleBarColor = Literal["white", "black"]
ColorBarPosition = Literal["right", "bottom"]


@dataclass(frozen=True)
class PreviewDisplayOptions:
    display_mode: DisplayMode = "linear"
    colormap: ColormapName = "gray"
    low_percentile: float = 2.0
    high_percentile: float = 98.0


@dataclass(frozen=True)
class AnnotationStyle:
    font_family: str = "Arial"
    font_size_px: int = 12
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class ScaleBarOptions:
    enabled: bool = False
    image_width_um: float | None = None
    scale_length_um: float = 50.0
    position: ScaleBarPosition = "bottom-right"
    offset_x_px: int = 16
    offset_y_px: int = 16
    color: ScaleBarColor = "white"
    thickness_px: int = 3
    show_label: bool = True
    label_style: AnnotationStyle = field(default_factory=AnnotationStyle)


@dataclass(frozen=True)
class ColorBarOptions:
    enabled: bool = True
    position: ColorBarPosition = "right"
    label: str = "PL intensity (a.u.)"
    label_style: AnnotationStyle = field(default_factory=AnnotationStyle)
    tick_style: AnnotationStyle = field(
        default_factory=lambda: AnnotationStyle(font_family="Arial", font_size_px=11)
    )
