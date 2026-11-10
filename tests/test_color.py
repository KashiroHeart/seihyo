import pytest

from seihyo.core.color import normalize_text_color, to_rgb_hex


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ((0.0,), "000000"),
        ((1.0,), "FFFFFF"),
        (0.5, "808080"),
        ((0.933, 0.0, 0.0), "EE0000"),
        ((0.306, 0.655, 0.18), "4EA72E"),
        ((0, 0, 1), "0000FF"),
        ((0, 1, 1, 0), "FF0000"),
        ((0, 0, 0, 1), "000000"),
        ((1.2, -0.1, 0.5), "FF0080"),
    ],
)
def test_to_rgb_hex(value, expected):
    assert to_rgb_hex(value) == expected


@pytest.mark.parametrize("value", [None, (), (0.1, 0.2), "P0", ("pattern",), [object()]])
def test_to_rgb_hex_unknown(value):
    assert to_rgb_hex(value) is None


def test_black_is_default():
    assert normalize_text_color((0.0,)) is None
    assert normalize_text_color((0, 0, 0)) is None
    assert normalize_text_color((0, 0, 0, 1)) is None
    assert normalize_text_color((1, 0, 0)) == "FF0000"
