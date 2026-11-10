"""画面 3: Excel / CSV への出力。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from seihyo.core.exporters import export_csv, export_excel, make_sheet_names
from seihyo.core.models import Table

CSV_DISABLED_TIP = "CSV は、前の画面で表を 1 つだけ選択した場合に出力できます。"


class ExportPage(QWidget):
    back_requested = Signal()
    restart_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tables: list[Table] = []
        self._source: Path | None = None
        self._last_saved: Path | None = None

        title = QLabel("出力")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.summary = QLabel()
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        self.excel_btn = QPushButton("Excel に出力")
        self.csv_btn = QPushButton("CSV に出力")
        for b in (self.excel_btn, self.csv_btn):
            b.setMinimumHeight(36)
            b.setMinimumWidth(160)
        self.excel_btn.clicked.connect(self._export_excel)
        self.csv_btn.clicked.connect(self._export_csv)
        self.csv_note = QLabel()
        self.csv_note.setStyleSheet("color: gray;")
        self.csv_note.setWordWrap(True)
        out_row = QHBoxLayout()
        out_row.addWidget(self.excel_btn)
        out_row.addWidget(self.csv_btn)
        out_row.addStretch(1)

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.open_folder_btn = QPushButton("保存先フォルダを開く")
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.clicked.connect(self._open_folder)
        st_row = QHBoxLayout()
        st_row.addWidget(self.status, 1)
        st_row.addWidget(self.open_folder_btn)

        self.back_btn = QPushButton("戻る")
        self.restart_btn = QPushButton("最初から")
        self.back_btn.clicked.connect(self.back_requested)
        self.restart_btn.clicked.connect(self.restart_requested)
        nav = QHBoxLayout()
        nav.addWidget(self.back_btn)
        nav.addStretch(1)
        nav.addWidget(self.restart_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(self.summary)
        lay.addWidget(self.list, 1)
        lay.addLayout(out_row)
        lay.addWidget(self.csv_note)
        lay.addLayout(st_row)
        lay.addLayout(nav)

    # ------------------------------------------------------------------ #
    def set_tables(self, tables: list[Table], source: Path) -> None:
        self._tables = list(tables)
        self._source = source
        self._last_saved = None
        n = len(tables)
        self.summary.setText(
            f"{n} 個の表を選択しています。Excel では 1 シートに 1 表を出力します。"
            if n > 1
            else "1 個の表を選択しています。"
        )
        self.list.clear()
        for t, sheet in zip(tables, make_sheet_names(tables), strict=True):
            self.list.addItem(f"{t.label}    →  シート「{sheet}」")
        single = n == 1
        self.csv_btn.setEnabled(single)
        self.csv_btn.setToolTip("" if single else CSV_DISABLED_TIP)
        self.csv_note.setText("CSV には文字色は保持されません。" if single else CSV_DISABLED_TIP)
        self.status.clear()
        self.open_folder_btn.setVisible(False)

    # ------------------------------------------------------------------ #
    def _default_path(self, suffix: str) -> str:
        if self._source is None:
            return ""
        stem = self._source.stem
        if suffix == ".csv" and self._tables:
            stem += "_" + make_sheet_names(self._tables[:1])[0]
        return str(self._source.with_name(stem + suffix))

    def _ask_path(self, caption: str, suffix: str, filt: str) -> Path | None:
        file, _ = QFileDialog.getSaveFileName(self, caption, self._default_path(suffix), filt)
        if not file:
            return None
        path = Path(file)
        if path.suffix.lower() != suffix:
            path = path.with_name(path.name + suffix)
        return path

    def _export_excel(self) -> None:
        path = self._ask_path("Excel に出力", ".xlsx", "Excel ブック (*.xlsx)")
        if path:
            self._run(lambda: export_excel(self._tables, path))

    def _export_csv(self) -> None:
        if len(self._tables) != 1:
            return
        path = self._ask_path("CSV に出力", ".csv", "CSV ファイル (*.csv)")
        if path:
            self._run(lambda: export_csv(self._tables[0], path))

    def _run(self, fn) -> None:  # noqa: ANN001
        try:
            saved: Path = fn()
        except PermissionError:
            QMessageBox.warning(
                self,
                "保存できませんでした",
                "ファイルに書き込めませんでした。\n同じファイルを Excel などで開いている場合は閉じてから再度お試しください。",
            )
            return
        except Exception as e:
            QMessageBox.critical(self, "保存できませんでした", str(e))
            return
        self._last_saved = saved
        self.status.setText(f"保存しました: {saved}")
        self.open_folder_btn.setVisible(True)

    def _open_folder(self) -> None:
        if self._last_saved:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_saved.parent)))
