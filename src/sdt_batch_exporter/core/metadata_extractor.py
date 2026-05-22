"""Helpers for safe JSON-compatible metadata conversion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def to_jsonable(value: object, *, array_inline_limit: int = 1024) -> object:
    """Convert nested metadata to JSON-compatible structures."""
    if array_inline_limit <= 0:
        raise ValueError("array_inline_limit must be a positive integer")

    if value is None or isinstance(value, bool | int | float | str):
        return value

    if isinstance(value, np.integer | np.floating | np.bool_):
        return value.item()

    if isinstance(value, np.ndarray):
        if value.size <= array_inline_limit:
            return value.tolist()
        return {
            "type": "ndarray",
            "shape": [int(dimension) for dimension in value.shape],
            "dtype": str(value.dtype),
            "size": int(value.size),
        }

    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "type": "bytes",
                "encoding": "hex",
                "value": value.hex(),
            }

    if isinstance(value, Mapping):
        return {
            str(key): to_jsonable(item, array_inline_limit=array_inline_limit)
            for key, item in value.items()
        }

    if isinstance(value, tuple):
        return [to_jsonable(item, array_inline_limit=array_inline_limit) for item in value]

    if isinstance(value, Sequence) and not isinstance(value, str):
        return [to_jsonable(item, array_inline_limit=array_inline_limit) for item in value]

    return str(value)
