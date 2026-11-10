"""画面 1: PDF 選択と抽出。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from seihyo.core.extractor import ExtractOptions
from seihyo.gui.widgets.toggle import LabeledToggle


class SelectPage(QWidget):
    extract_requested = Signal(object, object)  # (Path, ExtractOptions)
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._path: Path | None = None
        self.start_dir = ""

        title = QLabel("PDF を選択してください")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        hint = QLabel(
            "Excel / Word から出力した PDF に対応しています。ファイルをドラッグ＆ドロップすることもできます。"
        )
        hint.setWordWrap(True)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("PDF ファイルが選択されていません")
        self.browse_btn = QPushButton("参照...")
        self.browse_btn.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.browse_btn)

        self.color_toggle = LabeledToggle("文字色を取得する", True)
        self.merge_toggle = LabeledToggle("ページを跨ぐ表を結合する", True)
        settings = QGroupBox("設定")
        s_lay = QVBoxLayout(settings)
        s_lay.addWidget(self.color_toggle)
        s_lay.addWidget(self.merge_toggle)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFormat("%v / %m ページ")
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_requested)
        prow = QHBoxLayout()
        prow.addWidget(self.progress, 1)
        prow.addWidget(self.cancel_btn)

        self.extract_btn = QPushButton("抽出")
        self.extract_btn.setDefault(True)
        self.extract_btn.setMinimumWidth(120)
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self._emit_extract)
        brow = QHBoxLayout()
        brow.addStretch(1)
        brow.addWidget(self.extract_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(hint)
        lay.addSpacing(8)
        lay.addLayout(row)
        lay.addSpacing(8)
        lay.addWidget(settings)
        lay.addStretch(1)
        lay.addLayout(prow)
        lay.addLayout(brow)

    # ------------------------------------------------------------------ #
    @property
    def path(self) -> Path | None:
        return self._path

    def set_path(self, path: Path | None) -> None:
        self._path = path
        self.path_edit.setText(str(path) if path else "")
        self.extract_btn.setEnabled(path is not None)

    def options(self) -> ExtractOptions:
        return ExtractOptions(
            with_color=self.color_toggle.isChecked(),
            merge_across_pages=self.merge_toggle.isChecked(),
        )

    def set_busy(self, busy: bool) -> None:
        for w in (self.browse_btn, self.extract_btn, self.color_toggle, self.merge_toggle):
            w.setEnabled(not busy)
        if not busy:
            self.extract_btn.setEnabled(self._path is not None)
        self.progress.setVisible(busy)
        self.cancel_btn.setVisible(busy)
        self.cancel_btn.setEnabled(busy)
        self.setAcceptDrops(not busy)
        if busy:
            self.progress.setRange(0, 0)  # ページ数が分かるまでは不定表示

    def set_progress(self, done: int, total: int) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(done)

    # ------------------------------------------------------------------ #
    def _browse(self) -> None:
        start = str(self._path.parent) if self._path else self.start_dir
        file, _ = QFileDialog.getOpenFileName(self, "PDF を選択", start, "PDF ファイル (*.pdf)")
        if file:
            self.set_path(Path(file))

    def _emit_extract(self) -> None:
        if self._path is not None:
            self.extract_requested.emit(self._path, self.options())

    @staticmethod
    def _pdf_from_mime(event) -> Path | None:  # noqa: ANN001
        md = event.mimeData()
        if not md.hasUrls():
            return None
        for url in md.urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                return Path(url.toLocalFile())
        return None

    def dragEnterEvent(self, event) -> None:  # noqa: ANN001, N802
        if self._pdf_from_mime(event):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: ANN001, N802
        path = self._pdf_from_mime(event)
        if path:
            self.set_path(path)
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
