import pytest

from seihyo.core.extractor import (
    ExtractionCancelled,
    ExtractionError,
    ExtractOptions,
    extract_tables,
)

from .conftest import WORD_CASES

# --------------------------------------------------------------------------- #
# 合成 PDF
# --------------------------------------------------------------------------- #


def test_synthetic_structure(synthetic_pdf):
    r = extract_tables(synthetic_pdf)
    assert [t.pages for t in r.tables] == [(1,), (2,)]  # 本文があるので結合しない / 1 セル枠は除外
    t = r.tables[0]
    assert (t.n_rows, t.n_cols) == (3, 3)
    head = t.grid()[0][0]
    assert head.text == "Merged header"
    assert (head.rowspan, head.colspan) == (1, 2)
    assert t.grid()[0][1] is None
    assert t.text_matrix() == [
        ["Merged header", "", "H3"],
        ["001", "Red", "line1\nline2"],
        ["=SUM(A1)", "Mixed green", "black"],
    ]


def test_synthetic_colors(synthetic_pdf):
    t = extract_tables(synthetic_pdf).tables[0]
    g = t.grid()
    assert [(x.text, x.color) for x in g[1][1].runs] == [("Red", "FF0000")]
    assert [(x.text, x.color) for x in g[1][2].runs] == [("line1\n", "0000FF"), ("line2", None)]
    assert [(x.text, x.color) for x in g[2][1].runs] == [("Mixed ", None), ("green", "008000")]
    assert g[2][2].runs[0].color is None  # 明示的な黒は既定色


def test_without_color(synthetic_pdf):
    t = extract_tables(synthetic_pdf, ExtractOptions(with_color=False)).tables[0]
    assert all(run.color is None for c in t.cells for run in c.runs)


def test_split_table_is_merged(split_pdf):
    r = extract_tables(split_pdf)
    assert len(r.tables) == 1
    t = r.tables[0]
    assert t.pages == (1, 2, 3)
    m = t.text_matrix()
    assert m[0] == ["No.", "Name"]
    assert ["No.", "Name"] not in m[1:]  # 繰り返し見出しは除外
    assert [row[0] for row in m[1:]] == [str(i) for i in range(1, 58)]
    assert t.label == "p.1–3 表1 (58行×2列)"


def test_split_table_not_merged_when_disabled(split_pdf):
    r = extract_tables(split_pdf, ExtractOptions(merge_across_pages=False))
    assert [t.pages for t in r.tables] == [(1,), (2,), (3,)]


def test_progress_and_cancel(split_pdf):
    calls = []
    extract_tables(split_pdf, progress=lambda d, t: calls.append((d, t)))
    assert calls == [(1, 3), (2, 3), (3, 3)]
    with pytest.raises(ExtractionCancelled):
        extract_tables(split_pdf, is_cancelled=lambda: True)


def test_invalid_file(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(ExtractionError):
        extract_tables(bad)
    with pytest.raises(ExtractionError):
        extract_tables(tmp_path / "missing.pdf")


def test_no_table_warning(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "plain.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(100, 700, "no tables here")
    c.showPage()
    c.save()
    r = extract_tables(path)
    assert r.tables == []
    assert any("表が見つかりません" in w for w in r.warnings)


# --------------------------------------------------------------------------- #
# Word 出力の実 PDF (行内 / 右寄せ / テキストボックス入れ子 / ページ跨ぎ)
# --------------------------------------------------------------------------- #

word = pytest.mark.skipif(not WORD_CASES.exists(), reason="word_cases.pdf がありません")


@word
def test_word_cases_tables():
    r = extract_tables(WORD_CASES)
    assert r.warnings == []
    assert [t.label for t in r.tables] == [
        "p.1 表1 (4行×4列)",  # 行内
        "p.1 表2 (4行×4列)",  # 右寄せ (左の本文・注意枠は表にしない)
        "p.2 表1 (3行×3列)",
        "p.2 表2 (4行×4列)",  # テキストボックスの入れ子
        "p.3–4 表1 (48行×2列)",  # ページ跨ぎ
    ]


@word
def test_word_cases_colors():
    tables = extract_tables(WORD_CASES).tables

    def runs(t, r, c):
        return [(x.text, x.color) for x in tables[t].grid()[r][c].runs]

    assert runs(0, 1, 3) == [("赤色", "EE0000"), ("と黒色を使用。", None)]
    assert runs(0, 2, 3) == [
        ("緑色", "4EA72E"),
        ("と", None),
        ("青色", "0000FF"),
        ("を使用。", None),
    ]
    assert runs(0, 3, 3) == [("黒のみ。一部太字で強調する。", None)]  # 太字の重ね打ちは除去
    assert runs(1, 2, 3) == [("緑", "4EA72E"), ("または", None), ("青", "0000FF")]
    assert runs(3, 2, 3) == [("太字赤色で強調", "EE0000")]


@word
def test_word_cases_split_table():
    t = extract_tables(WORD_CASES).tables[-1]
    m = t.text_matrix()
    assert m[0] == ["No.", "項目1"]
    assert m[1] == ["1", "北海道"]
    assert m[30] == ["30", "和歌山県"]
    assert m[31] == ["31", "鳥取県"]
    assert m[47] == ["47", "沖縄県"]
