"""Excel (.xlsx) 出力。1 シートに 1 表を出力する。"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

from seihyo.core.models import Cell, Table

_SHEET_NAME_MAX = 31
_INVALID_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")
_THIN = Side(style="thin", color="000000")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_ALIGN = Alignment(wrap_text=True, vertical="center")
_MIN_WIDTH, _MAX_WIDTH = 6, 60
# 日本語版 Excel (Windows 11) の既定フォント。リッチテキストの各部分にも同じ指定を入れ、
# 部分ごとにフォントが変わって見えるのを防ぐ
FONT_NAME = "游ゴシック"
FONT_SIZE = 11


def make_sheet_names(tables: Sequence[Table]) -> list[str]:
    """Excel の制約 (31 文字・禁止文字・重複不可) を満たすシート名を作る。"""
    names: list[str] = []
    used: set[str] = set()
    for t in tables:
        if len(t.pages) == 1:
            base = f"p{t.pages[0]}_表{t.index_on_page}"
        else:
            base = f"p{t.pages[0]}-{t.pages[-1]}_表{t.index_on_page}"
        base = _INVALID_SHEET_CHARS.sub("_", base)[:_SHEET_NAME_MAX]
        name, n = base, 2
        while name.lower() in used:
            suffix = f"({n})"
            name = base[: _SHEET_NAME_MAX - len(suffix)] + suffix
            n += 1
        used.add(name.lower())
        names.append(name)
    return names


def _display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in "WFA" else 1 for ch in text)


def _cell_value(cell: Cell) -> str | CellRichText:
    runs = [r for r in cell.runs if r.text]
    if len(runs) > 1 and len({r.color for r in runs}) > 1:
        return CellRichText(
            [
                TextBlock(
                    InlineFont(rFont=FONT_NAME, sz=FONT_SIZE, color=r.color or "000000"), r.text
                )
                for r in runs
            ]
        )
    return cell.text


def _write_table(ws, table: Table) -> None:  # noqa: ANN001 - openpyxl Worksheet
    widths: dict[int, int] = {}
    for cell in table.cells:
        r, c = cell.row + 1, cell.col + 1
        xl = ws.cell(row=r, column=c)
        value = _cell_value(cell)
        xl.value = value
        # 数式・数値として解釈させず、常に文字列として扱う
        if isinstance(value, str):
            xl.data_type = "s"
        xl.number_format = "@"
        colors = {run.color for run in cell.runs if run.text}
        color = next(iter(colors)) if len(colors) == 1 else None
        xl.font = Font(name=FONT_NAME, size=FONT_SIZE, color=color)

        if cell.rowspan > 1 or cell.colspan > 1:
            ws.merge_cells(
                start_row=r,
                start_column=c,
                end_row=r + cell.rowspan - 1,
                end_column=c + cell.colspan - 1,
            )

        if cell.colspan == 1:
            w = max((_display_width(line) for line in cell.text.split("\n")), default=0)
            widths[c] = max(widths.get(c, 0), w)

    # 罫線・配置は空セルや結合セルの被覆部分も含めて全体に設定する
    for row in ws.iter_rows(min_row=1, max_row=table.n_rows, max_col=table.n_cols):
        for target in row:
            target.border = _BORDER
            target.alignment = _ALIGN
            if target.value is None:
                target.font = Font(name=FONT_NAME, size=FONT_SIZE)

    for c in range(1, table.n_cols + 1):
        w = widths.get(c, 0) + 2
        ws.column_dimensions[get_column_letter(c)].width = min(max(w, _MIN_WIDTH), _MAX_WIDTH)


def export_excel(tables: Sequence[Table], path: str | Path) -> Path:
    if not tables:
        raise ValueError("出力する表がありません。")
    path = Path(path)
    wb = Workbook()
    wb.remove(wb.active)
    for table, name in zip(tables, make_sheet_names(tables), strict=True):
        _write_table(wb.create_sheet(title=name), table)
    wb.save(path)
    return path
