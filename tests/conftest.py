"""テスト用 PDF を reportlab で生成する。"""

from __future__ import annotations

import os
from pathlib import Path

# GUI テストは画面のない環境 (CI 等) でも動くようにする
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
WORD_CASES = FIXTURES / "word_cases.pdf"


def _grid(c, x0: float, y_top: float, col_w: list[float], row_h: float, n_rows: int) -> None:
    """y_top は PDF 座標 (下が 0) での表の上端。"""
    xs = [x0]
    for w in col_w:
        xs.append(xs[-1] + w)
    y_bottom = y_top - row_h * n_rows
    for i in range(n_rows + 1):
        y = y_top - row_h * i
        c.line(xs[0], y, xs[-1], y)
    for x in xs:
        c.line(x, y_top, x, y_bottom)


@pytest.fixture(scope="session")
def synthetic_pdf(tmp_path_factory) -> Path:
    """結合セル・CMYK 色・複数行セル・表の後の本文を含む 2 ページの PDF。

    p.1: 3 行 × 3 列の表。1 行目の A1:B1 は横結合 (中間の縦線を描かない)
         B2 は CMYK の赤、C2 は 2 行テキスト、C3 はグレー 0 (黒) 明示
         表の下に本文 → 次ページの表とは結合しない
    p.2: 1 セルだけの枠 (表として扱わない) と 2 行 × 2 列の表
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    path = tmp_path_factory.mktemp("pdf") / "synthetic.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    _, h = A4

    top = h - 100
    c.setLineWidth(0.5)
    # 横線
    for i in range(4):
        y = top - 30 * i
        c.line(50, y, 350, y)
    # 縦線 (x=150 は 1 行目では描かない → A1:B1 が結合)
    c.line(50, top, 50, top - 90)
    c.line(150, top - 30, 150, top - 90)
    c.line(250, top, 250, top - 90)
    c.line(350, top, 350, top - 90)

    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(55, top - 20, "Merged header")
    c.drawString(255, top - 20, "H3")
    c.drawString(55, top - 50, "001")
    c.setFillColorCMYK(0, 1, 1, 0)
    c.drawString(155, top - 50, "Red")
    c.setFillColorRGB(0, 0, 1)
    c.drawString(255, top - 45, "line1")
    c.setFillColorRGB(0, 0, 0)
    c.drawString(255, top - 57, "line2")
    c.drawString(55, top - 80, "=SUM(A1)")
    c.drawString(155, top - 80, "Mixed ")
    c.setFillColorRGB(0, 0.5, 0)
    c.drawString(185, top - 80, "green")
    c.setFillGray(0)
    c.drawString(255, top - 80, "black")
    c.drawString(50, top - 130, "Body text after the table.")
    c.showPage()

    c.setLineWidth(0.5)
    c.rect(50, h - 120, 300, 40)  # 1 セルだけの枠
    c.setFont("Helvetica", 10)
    c.drawString(60, h - 105, "Notice box")
    _grid(c, 50, h - 200, [100, 100], 25, 2)
    c.drawString(55, h - 217, "a")
    c.drawString(155, h - 217, "b")
    c.drawString(55, h - 242, "c")
    c.drawString(155, h - 242, "d")
    c.showPage()
    c.save()
    return path


@pytest.fixture(scope="session")
def split_pdf(tmp_path_factory) -> Path:
    """3 ページに跨る 2 列の表。p.2 / p.3 の先頭で見出し行を繰り返す。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    path = tmp_path_factory.mktemp("pdf") / "split.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    _, h = A4
    n = 0
    for page in range(3):
        c.setFont("Helvetica", 10)
        if page == 0:
            c.drawString(50, h - 80, "Title text above the table")
        top = h - 100 if page == 0 else h - 72
        rows = 20
        c.setLineWidth(0.5)
        _grid(c, 50, top, [60, 200], 30, rows)
        c.drawString(55, top - 20, "No.")
        c.drawString(115, top - 20, "Name")
        for r in range(1, rows):
            n += 1
            c.drawString(55, top - 20 - 30 * r, str(n))
            c.drawString(115, top - 20 - 30 * r, f"item-{n}")
        c.showPage()
    c.save()
    return path
