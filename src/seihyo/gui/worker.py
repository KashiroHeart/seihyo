"""抽出処理をバックグラウンドで実行するスレッド。"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from seihyo.core.extractor import (
    ExtractionCancelled,
    ExtractionError,
    ExtractOptions,
    extract_tables,
)
from seihyo.core.models import ExtractionResult


class ExtractWorker(QThread):
    progressed = Signal(int, int)  # (完了ページ数, 総ページ数)
    succeeded = Signal(object)  # ExtractionResult
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, path: Path, options: ExtractOptions, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self._path = path
        self._options = options
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            result: ExtractionResult = extract_tables(
                self._path,
                self._options,
                progress=self.progressed.emit,
                is_cancelled=self._cancel.is_set,
            )
        except ExtractionCancelled:
            self.cancelled.emit()
        except ExtractionError as e:
            self.failed.emit(str(e))
        except Exception as e:  # 想定外のエラーも UI に伝える
            self.failed.emit(f"予期しないエラーが発生しました: {e}")
        else:
            self.succeeded.emit(result)
