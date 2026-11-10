"""GUI のスモークテスト (画面遷移とボタンの有効/無効)。"""

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt  # noqa: E402

from seihyo.gui.main_window import MainWindow  # noqa: E402
from seihyo.gui.table_preview import HTML_ROLE  # noqa: E402


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    w = MainWindow()
    qtbot.addWidget(w)
    return w


def _extract(qtbot, w, path):
    w.select_page.set_path(path)
    assert w.select_page.extract_btn.isEnabled()
    qtbot.mouseClick(w.select_page.extract_btn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: w.stack.currentWidget() is w.preview_page, timeout=20000)


def test_full_flow(qtbot, window, synthetic_pdf, tmp_path, monkeypatch):
    w = window
    assert w.stack.currentWidget() is w.select_page
    assert not w.select_page.extract_btn.isEnabled()

    _extract(qtbot, w, synthetic_pdf)
    pp = w.preview_page
    assert pp.list.count() == 2
    assert not pp.next_btn.isEnabled()  # 未選択では次へ進めない
    assert "取得元: 1 ページ" in pp.preview_pages.text()

    # 結合セルと部分色のプレビュー
    assert pp.preview.columnSpan(0, 0) == 2
    html = pp.preview.item(2, 1).data(HTML_ROLE)
    assert "color:#008000" in html and "green" in html

    # 2 つ選択 → CSV は不可
    pp._set_all(True)
    assert pp.next_btn.isEnabled()
    qtbot.mouseClick(pp.next_btn, Qt.MouseButton.LeftButton)
    ep = w.export_page
    assert w.stack.currentWidget() is ep
    assert ep.excel_btn.isEnabled()
    assert not ep.csv_btn.isEnabled()

    out = tmp_path / "out.xlsx"
    monkeypatch.setattr(
        "seihyo.gui.pages.export_page.QFileDialog.getSaveFileName", lambda *a, **k: (str(out), "")
    )
    qtbot.mouseClick(ep.excel_btn, Qt.MouseButton.LeftButton)
    assert out.exists()
    assert "保存しました" in ep.status.text()

    # 1 つだけ選択 → CSV 可
    qtbot.mouseClick(ep.back_btn, Qt.MouseButton.LeftButton)
    pp._set_all(False)
    pp.list.item(0).setCheckState(Qt.CheckState.Checked)
    qtbot.mouseClick(pp.next_btn, Qt.MouseButton.LeftButton)
    assert ep.csv_btn.isEnabled()
    out_csv = tmp_path / "out"  # 拡張子は自動で補われる
    monkeypatch.setattr(
        "seihyo.gui.pages.export_page.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(out_csv), ""),
    )
    qtbot.mouseClick(ep.csv_btn, Qt.MouseButton.LeftButton)
    assert (tmp_path / "out.csv").exists()

    qtbot.mouseClick(ep.restart_btn, Qt.MouseButton.LeftButton)
    assert w.stack.currentWidget() is w.select_page
    assert w.select_page.path is None


def test_split_pages_label(qtbot, window, split_pdf):
    _extract(qtbot, window, split_pdf)
    pp = window.preview_page
    assert pp.list.count() == 1
    assert "1〜3 ページ" in pp.preview_pages.text()


def test_no_table_stays_on_first_page(qtbot, window, tmp_path, monkeypatch):
    from reportlab.pdfgen import canvas

    path = tmp_path / "plain.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(100, 700, "no tables")
    c.showPage()
    c.save()
    shown = []
    monkeypatch.setattr(
        "seihyo.gui.main_window.QMessageBox.information", lambda *a, **k: shown.append(a)
    )
    window.select_page.set_path(path)
    qtbot.mouseClick(window.select_page.extract_btn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: bool(shown), timeout=20000)
    qtbot.waitUntil(lambda: window._worker is None, timeout=5000)
    assert window.stack.currentWidget() is window.select_page
    assert window.select_page.extract_btn.isEnabled()
