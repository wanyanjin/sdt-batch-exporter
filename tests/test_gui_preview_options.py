from __future__ import annotations

from sdt_batch_exporter.gui.preview_options import (
    AnnotationStyle,
    ColorBarOptions,
    ScaleBarOptions,
)


def test_annotation_style_defaults() -> None:
    style = AnnotationStyle()
    assert style.font_family == "Arial"
    assert style.font_size_px == 12
    assert style.bold is False
    assert style.italic is False


def test_color_bar_options_defaults() -> None:
    options = ColorBarOptions()
    assert options.enabled is True
    assert options.position == "right"
    assert options.label == "PL intensity (a.u.)"
    assert options.label_style.font_size_px == 12
    assert options.tick_style.font_size_px == 11


def test_scale_bar_and_color_bar_styles_are_independent() -> None:
    scale = ScaleBarOptions()
    color = ColorBarOptions()
    assert scale.label_style is not color.label_style
    assert color.label_style is not color.tick_style


def test_mutating_color_bar_style_does_not_change_scale_bar_style() -> None:
    scale = ScaleBarOptions()
    color = ColorBarOptions(
        label_style=AnnotationStyle(font_family="Times New Roman", font_size_px=16, bold=True),
        tick_style=AnnotationStyle(font_family="Arial", font_size_px=9),
    )
    assert scale.label_style.font_family == "Arial"
    assert scale.label_style.font_size_px == 12
    assert color.label_style.font_family == "Times New Roman"
    assert color.tick_style.font_size_px == 9
