"""seihyo の起動エントリポイント。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from seihyo import APP_NAME, __version__


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(__version__)

    from seihyo.gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()
