"""抽出結果を表すデータモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BBox = tuple[float, float, float, float]  # (x0, top, x1, bottom) — pdfplumber と同じ座標系


@dataclass
class TextRun:
    """同じ色が連続する文字のまとまり。"""

    text: str
    color: str | None = None  # "RRGGBB"。None は既定色 (黒・色取得なしを含む)


@dataclass
class Cell:
    row: int
    col: int
    runs: list[TextRun] = field(default_factory=list)
    rowspan: int = 1
    colspan: int = 1

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)

    @property
    def colors(self) -> set[str | None]:
        return {r.color for r in self.runs if r.text}


@dataclass
class Table:
    pages: tuple[int, ...]  # 取得元ページ (1 始まり)。ページを跨いで結合した表は複数
    index_on_page: int  # 先頭ページ内での通し番号 (1 始まり)
    bbox: BBox  # 先頭ページ上の位置
    n_rows: int
    n_cols: int
    cells: list[Cell]  # 結合セルの被覆部分は含まない

    @property
    def page_label(self) -> str:
        if len(self.pages) == 1:
            return f"p.{self.pages[0]}"
        return f"p.{self.pages[0]}–{self.pages[-1]}"

    @property
    def label(self) -> str:
        return f"{self.page_label} 表{self.index_on_page} ({self.n_rows}行×{self.n_cols}列)"

    def grid(self) -> list[list[Cell | None]]:
        """行列形式で返す。結合セルは左上にのみ Cell を置き、被覆部分は None。"""
        g: list[list[Cell | None]] = [[None] * self.n_cols for _ in range(self.n_rows)]
        for c in self.cells:
            g[c.row][c.col] = c
        return g

    def text_matrix(self) -> list[list[str]]:
        return [[c.text if c else "" for c in row] for row in self.grid()]


@dataclass
class ExtractionResult:
    source: Path
    tables: list[Table] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
