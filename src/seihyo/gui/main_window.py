"""メインウィンドウ。3 つの画面を QStackedWidget で切り替える。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from seihyo import APP_NAME
from seihyo.core.extractor import ExtractOptions
from seihyo.core.models import ExtractionResult, Table
from seihyo.gui.pages.export_page import ExportPage
from seihyo.gui.pages.preview_page import PreviewPage
from seihyo.gui.pages.select_page import SelectPage
from seihyo.gui.worker import ExtractWorker

_KEY_COLOR = "extract/with_color"
_KEY_MERGE = "extract/merge_across_pages"
_KEY_DIR = "ui/last_dir"


def _to_bool(v: object, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("1", "true", "yes")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1000, 680)

        self._settings = QSettings(APP_NAME, APP_NAME)
        self._worker: ExtractWorker | None = None
        self._result: ExtractionResult | None = None

        self.select_page = SelectPage()
        self.preview_page = PreviewPage()
        self.export_page = ExportPage()
        self.stack = QStackedWidget()
        for p in (self.select_page, self.preview_page, self.export_page):
            self.stack.addWidget(p)
        self.setCentralWidget(self.stack)

        self.select_page.color_toggle.setChecked(_to_bool(self._settings.value(_KEY_COLOR), True))
        self.select_page.merge_toggle.setChecked(_to_bool(self._settings.value(_KEY_MERGE), True))
        self.select_page.start_dir = str(self._settings.value(_KEY_DIR, "") or "")

        self.select_page.extract_requested.connect(self._start_extract)
        self.select_page.cancel_requested.connect(self._cancel_extract)
        self.preview_page.back_requested.connect(
            lambda: self.stack.setCurrentWidget(self.select_page)
        )
        self.preview_page.next_requested.connect(self._go_export)
        self.export_page.back_requested.connect(
            lambda: self.stack.setCurrentWidget(self.preview_page)
        )
        self.export_page.restart_requested.connect(self._restart)

    # ------------------------------------------------------------------ #
    def _start_extract(self, path: Path, options: ExtractOptions) -> None:
        if self._worker is not None:
            return
        self._settings.setValue(_KEY_COLOR, options.with_color)
        self._settings.setValue(_KEY_MERGE, options.merge_across_pages)
        self._settings.setValue(_KEY_DIR, str(path.parent))

        self.select_page.set_busy(True)
        w = ExtractWorker(path, options, self)
        w.progressed.connect(self.select_page.set_progress)
        w.succeeded.connect(self._on_success)
        w.failed.connect(self._on_failed)
        w.cancelled.connect(self._on_cancelled)
        w.finished.connect(self._on_worker_finished)
        self._worker = w
        w.start()

    def _cancel_extract(self) -> None:
        if self._worker is not None:
            self.select_page.cancel_btn.setEnabled(False)
            self._worker.cancel()

    def _on_worker_finished(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        self.select_page.set_busy(False)

    def _on_success(self, result: ExtractionResult) -> None:
        self._result = result
        if not result.tables:
            msg = "表が見つかりませんでした。"
            others = [w for w in result.warnings if "表が見つかりません" not in w]
            if others:
                msg += "\n\n" + "\n".join(others)
            QMessageBox.information(self, APP_NAME, msg)
            return
        self.preview_page.set_result(result)
        self.stack.setCurrentWidget(self.preview_page)

    def _on_failed(self, message: str) -> None:
        QMessageBox.critical(self, APP_NAME, message)

    def _on_cancelled(self) -> None:
        pass

    def _go_export(self, tables: list[Table]) -> None:
        if not tables or self._result is None:
            return
        self.export_page.set_tables(tables, self._result.source)
        self.stack.setCurrentWidget(self.export_page)

    def _restart(self) -> None:
        self._result = None
        self.select_page.set_path(None)
        self.stack.setCurrentWidget(self.select_page)

    def closeEvent(self, event) -> None:  # noqa: ANN001, N802
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait(5000)
        super().closeEvent(event)
