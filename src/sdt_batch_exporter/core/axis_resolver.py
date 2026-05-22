"""Pure axis inference rules for dataset-like arrays."""

from __future__ import annotations

from sdt_batch_exporter.models.axis import AxisInfo


def infer_axes(data_shape: tuple[int, ...], time_length: int | None = None) -> AxisInfo:
    """Infer spatial and time axes from shape metadata alone."""
    _validate_data_shape(data_shape)
    _validate_time_length(time_length)

    if len(data_shape) == 2:
        return AxisInfo(
            data_shape=data_shape,
            time_axis_index=None,
            spatial_axes=(0, 1),
            axis_order=("y", "x"),
            inference_source="source_2d_dataset",
            axis_inference_status="not_required",
            is_exportable_intensity=True,
            skipped_intensity_export=False,
            skip_reason=None,
        )

    if time_length is None:
        return _failed_axis_info(
            data_shape=data_shape,
            inference_source="missing_time_length_for_nd_dataset",
            skip_reason="missing_time_length",
        )

    matching_axes = tuple(index for index, size in enumerate(data_shape) if size == time_length)
    if not matching_axes:
        return _failed_axis_info(
            data_shape=data_shape,
            inference_source="matched_sdt_times_no_axis",
            skip_reason="time_length_matches_no_axis",
        )

    if len(matching_axes) > 1:
        return AxisInfo(
            data_shape=data_shape,
            time_axis_index=None,
            spatial_axes=(),
            axis_order=tuple("unknown" for _ in data_shape),
            inference_source="matched_sdt_times_multiple_axes",
            axis_inference_status="ambiguous",
            is_exportable_intensity=False,
            skipped_intensity_export=True,
            skip_reason="time_length_matches_multiple_axes",
        )

    time_axis_index = matching_axes[0]
    spatial_axes = tuple(index for index in range(len(data_shape)) if index != time_axis_index)
    axis_order: tuple[str, ...]
    if len(data_shape) == 3 and time_axis_index == len(data_shape) - 1:
        inference_source = "matched_sdt_times_last_axis"
        axis_order = ("y", "x", "time")
    else:
        inference_source = "matched_sdt_times_unique_axis"
        axis_order = _build_axis_order(len(data_shape), time_axis_index)

    return AxisInfo(
        data_shape=data_shape,
        time_axis_index=time_axis_index,
        spatial_axes=spatial_axes,
        axis_order=axis_order,
        inference_source=inference_source,
        axis_inference_status="resolved",
        is_exportable_intensity=True,
        skipped_intensity_export=False,
        skip_reason=None,
    )


def _validate_data_shape(data_shape: tuple[int, ...]) -> None:
    if not data_shape:
        raise ValueError("data_shape must not be empty")
    if any(not isinstance(dimension, int) or dimension <= 0 for dimension in data_shape):
        raise ValueError("data_shape must contain only positive integers")


def _validate_time_length(time_length: int | None) -> None:
    if time_length is not None and time_length <= 0:
        raise ValueError("time_length must be a positive integer")


def _failed_axis_info(
    data_shape: tuple[int, ...], inference_source: str, skip_reason: str
) -> AxisInfo:
    return AxisInfo(
        data_shape=data_shape,
        time_axis_index=None,
        spatial_axes=(),
        axis_order=tuple("unknown" for _ in data_shape),
        inference_source=inference_source,
        axis_inference_status="failed",
        is_exportable_intensity=False,
        skipped_intensity_export=True,
        skip_reason=skip_reason,
    )


def _build_axis_order(axis_count: int, time_axis_index: int) -> tuple[str, ...]:
    axis_order: list[str] = []
    for index in range(axis_count):
        if index == time_axis_index:
            axis_order.append("time")
        else:
            axis_order.append(f"axis_{index}")
    return tuple(axis_order)
