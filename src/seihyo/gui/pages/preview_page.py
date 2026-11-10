"""画面 2: 抽出結果のプレビューと表の選択。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from seihyo.core.models import ExtractionResult, Table
from seihyo.gui.table_preview import TablePreview

TABLE_ROLE = Qt.ItemDataRole.UserRole + 10


def page_description(table: Table) -> str:
    if len(table.pages) == 1:
        return f"取得元: {table.pages[0]} ページ"
    return f"取得元: {table.pages[0]}〜{table.pages[-1]} ページ (ページを跨ぐ表を結合)"


class PreviewPage(QWidget):
    back_requested = Signal()
    next_requested = Signal(list)  # list[Table]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.source_label = QLabel()
        self.source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet(
            "background:#fff4ce; color:#5c4400; border:1px solid #e0c060; padding:6px;"
        )
        self.warning_label.setVisible(False)

        # 左: 表一覧
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_current_changed)
        self.list.itemChanged.connect(self._update_selection_state)
        all_btn = QPushButton("すべて選択")
        none_btn = QPushButton("すべて解除")
        all_btn.clicked.connect(lambda: self._set_all(True))
        none_btn.clicked.connect(lambda: self._set_all(False))
        self.count_label = QLabel()
        left = QWidget()
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(0, 0, 0, 0)
        l_lay.addWidget(QLabel("抽出した表 (出力する表にチェック)"))
        l_lay.addWidget(self.list, 1)
        btns = QHBoxLayout()
        btns.addWidget(all_btn)
        btns.addWidget(none_btn)
        l_lay.addLayout(btns)
        l_lay.addWidget(self.count_label)

        # 右: プレビュー
        self.preview_title = QLabel()
        self.preview_title.setStyleSheet("font-weight: bold;")
        self.preview_pages = QLabel()
        self.preview = TablePreview()
        right = QWidget()
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.addWidget(self.preview_title)
        r_lay.addWidget(self.preview_pages)
        r_lay.addWidget(self.preview, 1)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([260, 700])

        self.back_btn = QPushButton("戻る")
        self.next_btn = QPushButton("次へ")
        self.next_btn.setDefault(True)
        self.next_btn.setMinimumWidth(120)
        self.back_btn.clicked.connect(self.back_requested)
        self.next_btn.clicked.connect(lambda: self.next_requested.emit(self.selected_tables()))
        nav = QHBoxLayout()
        nav.addWidget(self.back_btn)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(self.source_label)
        lay.addWidget(self.warning_label)
        lay.addWidget(splitter, 1)
        lay.addLayout(nav)

    # ------------------------------------------------------------------ #
    def set_result(self, result: ExtractionResult) -> None:
        self.source_label.setText(
            f"{result.source.name}  —  {len(result.tables)} 個の表を検出しました"
        )
        self.warning_label.setText("\n".join(result.warnings))
        self.warning_label.setVisible(bool(result.warnings))

        self.list.blockSignals(True)
        self.list.clear()
        for t in result.tables:
            item = QListWidgetItem(t.label)
            item.setData(TABLE_ROLE, t)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setToolTip(page_description(t))
            self.list.addItem(item)
        self.list.blockSignals(False)
        if self.list.count():
            self.list.setCurrentRow(0)
        else:
            self._show(None)
        self._update_selection_state()

    def selected_tables(self) -> list[Table]:
        return [
            self.list.item(i).data(TABLE_ROLE)
            for i in range(self.list.count())
            if self.list.item(i).checkState() == Qt.CheckState.Checked
        ]

    # ------------------------------------------------------------------ #
    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(state)
        self.list.blockSignals(False)
        self._update_selection_state()

    def _update_selection_state(self, *_args) -> None:  # noqa: ANN002
        n = len(self.selected_tables())
        self.count_label.setText(f"選択中: {n} / {self.list.count()} 件")
        self.next_btn.setEnabled(n > 0)

    def _on_current_changed(self, current: QListWidgetItem | None, _prev) -> None:  # noqa: ANN001
        self._show(current.data(TABLE_ROLE) if current else None)

    def _show(self, table: Table | None) -> None:
        self.preview.show_table(table)
        self.preview_title.setText(table.label if table else "")
        self.preview_pages.setText(page_description(table) if table else "")
