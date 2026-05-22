from __future__ import annotations

import pytest

from sdt_batch_exporter.core.axis_resolver import infer_axes


def test_infer_axes_for_2d_dataset_marks_not_required() -> None:
    axis_info = infer_axes((32, 64))

    assert axis_info.time_axis_index is None
    assert axis_info.spatial_axes == (0, 1)
    assert axis_info.axis_order == ("y", "x")
    assert axis_info.inference_source == "source_2d_dataset"
    assert axis_info.axis_inference_status == "not_required"
    assert axis_info.is_exportable_intensity is True
    assert axis_info.skipped_intensity_export is False
    assert axis_info.skip_reason is None


def test_infer_axes_resolves_last_axis_when_time_length_matches_last_dimension() -> None:
    axis_info = infer_axes((8, 16, 32), time_length=32)

    assert axis_info.time_axis_index == 2
    assert axis_info.spatial_axes == (0, 1)
    assert axis_info.axis_order == ("y", "x", "time")
    assert axis_info.inference_source == "matched_sdt_times_last_axis"
    assert axis_info.axis_inference_status == "resolved"


def test_infer_axes_resolves_unique_non_last_axis() -> None:
    axis_info = infer_axes((5, 7, 11), time_length=7)

    assert axis_info.time_axis_index == 1
    assert axis_info.spatial_axes == (0, 2)
    assert axis_info.axis_order == ("axis_0", "time", "axis_2")
    assert axis_info.inference_source == "matched_sdt_times_unique_axis"
    assert axis_info.axis_inference_status == "resolved"


def test_infer_axes_marks_ambiguous_when_time_length_matches_multiple_axes() -> None:
    axis_info = infer_axes((4, 6, 6), time_length=6)

    assert axis_info.time_axis_index is None
    assert axis_info.spatial_axes == ()
    assert axis_info.axis_order == ("unknown", "unknown", "unknown")
    assert axis_info.inference_source == "matched_sdt_times_multiple_axes"
    assert axis_info.axis_inference_status == "ambiguous"
    assert axis_info.is_exportable_intensity is False
    assert axis_info.skipped_intensity_export is True
    assert axis_info.skip_reason == "time_length_matches_multiple_axes"


def test_infer_axes_without_time_length_for_3d_dataset_fails() -> None:
    axis_info = infer_axes((10, 20, 30))

    assert axis_info.time_axis_index is None
    assert axis_info.spatial_axes == ()
    assert axis_info.axis_order == ("unknown", "unknown", "unknown")
    assert axis_info.inference_source == "missing_time_length_for_nd_dataset"
    assert axis_info.axis_inference_status == "failed"
    assert axis_info.is_exportable_intensity is False
    assert axis_info.skipped_intensity_export is True
    assert axis_info.skip_reason == "missing_time_length"


def test_infer_axes_fails_when_time_length_matches_no_axis() -> None:
    axis_info = infer_axes((10, 20, 30), time_length=25)

    assert axis_info.axis_inference_status == "failed"
    assert axis_info.inference_source == "matched_sdt_times_no_axis"
    assert axis_info.skip_reason == "time_length_matches_no_axis"


def test_infer_axes_resolves_unique_axis_for_4d_dataset() -> None:
    axis_info = infer_axes((3, 4, 9, 5), time_length=9)

    assert axis_info.time_axis_index == 2
    assert axis_info.spatial_axes == (0, 1, 3)
    assert axis_info.axis_order == ("axis_0", "axis_1", "time", "axis_3")
    assert axis_info.axis_inference_status == "resolved"


@pytest.mark.parametrize("data_shape", [(), (0, 2), (4, -1), (3, 2.5)])
def test_infer_axes_rejects_invalid_shapes(data_shape: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        infer_axes(data_shape)  # type: ignore[arg-type]


@pytest.mark.parametrize("time_length", [0, -1])
def test_infer_axes_rejects_invalid_time_length(time_length: int) -> None:
    with pytest.raises(ValueError):
        infer_axes((3, 4, 5), time_length=time_length)
