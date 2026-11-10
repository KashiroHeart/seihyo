"""PDF の色値を Excel 用の "RRGGBB" に変換する。"""

from __future__ import annotations

from collections.abc import Sequence

DEFAULT_COLOR_HEX = "000000"


def _clamp01(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def _to_byte(v: float) -> int:
    return round(_clamp01(v) * 255)


def to_rgb_hex(value: object) -> str | None:
    """pdfplumber の ``non_stroking_color`` を "RRGGBB" に変換する。

    * 1 要素: DeviceGray
    * 3 要素: DeviceRGB
    * 4 要素: DeviceCMYK
    * それ以外 (パターン・未知の色空間・None): None
    """
    if value is None:
        return None
    if isinstance(value, int | float):
        value = (value,)
    if not isinstance(value, Sequence) or isinstance(value, str):
        return None
    try:
        comps = [float(v) for v in value]
    except (TypeError, ValueError):
        return None

    if len(comps) == 1:
        r = g = b = comps[0]
    elif len(comps) == 3:
        r, g, b = comps
    elif len(comps) == 4:
        c, m, y, k = (_clamp01(v) for v in comps)
        r = (1 - c) * (1 - k)
        g = (1 - m) * (1 - k)
        b = (1 - y) * (1 - k)
    else:
        return None
    return f"{_to_byte(r):02X}{_to_byte(g):02X}{_to_byte(b):02X}"


def normalize_text_color(value: object) -> str | None:
    """文字色として扱う値を返す。黒 (明示含む) と取得不能な色は既定色 (None)。"""
    hex_ = to_rgb_hex(value)
    if hex_ is None or hex_ == DEFAULT_COLOR_HEX:
        return None
    return hex_
