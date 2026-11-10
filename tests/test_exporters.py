import csv

import pytest
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText

from seihyo.core.exporters import export_csv, export_excel, make_sheet_names
from seihyo.core.extractor import extract_tables
from seihyo.core.models import Cell, Table, TextRun


def _table(page=1, idx=1, pages=None):
    return Table(
        pages=pages or (page,),
        index_on_page=idx,
        bbox=(0, 0, 1, 1),
        n_rows=1,
        n_cols=1,
        cells=[Cell(0, 0, [TextRun("x")])],
    )


def test_sheet_names_unique():
    names = make_sheet_names([_table(1, 1), _table(1, 1), _table(3, 2, (3, 4))])
    assert names == ["p1_表1", "p1_表1(2)", "p3-4_表2"]


def test_excel_roundtrip(synthetic_pdf, tmp_path):
    tables = extract_tables(synthetic_pdf).tables
    out = export_excel(tables, tmp_path / "out.xlsx")
    wb = load_workbook(out, rich_text=True)
    assert wb.sheetnames == ["p1_表1", "p2_表1"]
    ws = wb["p1_表1"]
    assert ws["A1"].value == "Merged header"
    assert "A1:B1" in {str(r) for r in ws.merged_cells.ranges}
    # 文字列として保持 (数値変換・数式化しない)
    assert ws["A2"].value == "001" and ws["A2"].data_type == "s"
    assert ws["A3"].value == "=SUM(A1)" and ws["A3"].data_type == "s"
    # 単色セル
    assert ws["B2"].font.color.rgb.endswith("FF0000")
    # 複数色セルはリッチテキスト
    c2 = ws["C2"].value
    assert isinstance(c2, CellRichText)
    assert str(c2) == "line1\nline2"
    assert c2[0].font.color.rgb.endswith("0000FF")
    # 黒は既定色 (色指定なし)
    assert ws["C3"].font.color is None or ws["C3"].font.color.rgb in (None, "FF000000")


def test_excel_requires_tables(tmp_path):
    with pytest.raises(ValueError):
        export_excel([], tmp_path / "x.xlsx")


def test_csv(synthetic_pdf, tmp_path):
    t = extract_tables(synthetic_pdf).tables[0]
    out = export_csv(t, tmp_path / "out.csv")
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    with out.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [
        ["Merged header", "", "H3"],
        ["001", "Red", "line1\nline2"],
        ["=SUM(A1)", "Mixed green", "black"],
    ]
