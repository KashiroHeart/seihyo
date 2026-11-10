"""CSV 出力 (文字色は保持しない)。"""

from __future__ import annotations

import csv
from pathlib import Path

from seihyo.core.models import Table


def export_csv(table: Table, path: str | Path) -> Path:
    """表 1 つを CSV に出力する。

    Windows の Excel で文字化けしないよう BOM 付き UTF-8 で書き出す。
    結合セルの値は左上のセルにのみ入れ、被覆部分は空欄にする。
    """
    path = Path(path)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerows(table.text_matrix())
    return path
