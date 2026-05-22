from __future__ import annotations

import numpy as np

from sdt_batch_exporter.core.metadata_extractor import to_jsonable


class DummyObject:
    def __str__(self) -> str:
        return "dummy-object"


def test_to_jsonable_preserves_basic_types() -> None:
    assert to_jsonable(None) is None
    assert to_jsonable(True) is True
    assert to_jsonable(3) == 3
    assert to_jsonable(1.5) == 1.5
    assert to_jsonable("abc") == "abc"


def test_to_jsonable_handles_nested_list_tuple_and_dict() -> None:
    value = {"a": [1, (2, 3)], "b": {"c": "text"}}

    assert to_jsonable(value) == {"a": [1, [2, 3]], "b": {"c": "text"}}


def test_to_jsonable_converts_non_string_dict_keys() -> None:
    value = {1: "a", ("x", 2): "b"}

    assert to_jsonable(value) == {"1": "a", "('x', 2)": "b"}


def test_to_jsonable_converts_numpy_scalars() -> None:
    assert to_jsonable(np.int64(5)) == 5
    assert to_jsonable(np.float64(2.5)) == 2.5


def test_to_jsonable_inlines_small_arrays() -> None:
    value = np.array([[1, 2], [3, 4]], dtype=np.uint16)

    assert to_jsonable(value) == [[1, 2], [3, 4]]


def test_to_jsonable_summarizes_large_arrays() -> None:
    value = np.arange(12, dtype=np.uint16).reshape(3, 4)

    assert to_jsonable(value, array_inline_limit=4) == {
        "type": "ndarray",
        "shape": [3, 4],
        "dtype": "uint16",
        "size": 12,
    }


def test_to_jsonable_decodes_utf8_bytes() -> None:
    assert to_jsonable(b"abc") == "abc"


def test_to_jsonable_encodes_non_utf8_bytes_as_hex() -> None:
    assert to_jsonable(b"\xff\x00") == {
        "type": "bytes",
        "encoding": "hex",
        "value": "ff00",
    }


def test_to_jsonable_uses_string_for_custom_objects() -> None:
    assert to_jsonable(DummyObject()) == "dummy-object"


def test_to_jsonable_handles_nested_arrays_and_bytes() -> None:
    value = {
        "array": np.array([1, 2, 3], dtype=np.uint16),
        "payload": [b"ok", b"\xff\x01"],
    }

    assert to_jsonable(value) == {
        "array": [1, 2, 3],
        "payload": ["ok", {"type": "bytes", "encoding": "hex", "value": "ff01"}],
    }
