"""トグルスイッチ。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QWidget


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(40, 22)

    def paintEvent(self, _event) -> None:  # noqa: ANN001, N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        pal = self.palette()
        if not self.isEnabled():
            track = pal.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Mid)
        elif self.isChecked():
            track = pal.color(QPalette.ColorRole.Highlight)
        else:
            track = QColor("#9e9e9e")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 4
        x = r.right() - d - 2 if self.isChecked() else r.left() + 2
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x, r.top() + 2, d, d))
        if self.hasFocus():
            p.setPen(pal.color(QPalette.ColorRole.Highlight))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, r.height() / 2, r.height() / 2)


class LabeledToggle(QWidget):
    """ラベル付きトグル。ラベルのクリックでも切り替わる。"""

    def __init__(self, text: str, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.toggle = ToggleSwitch(self)
        self.toggle.setChecked(checked)
        self.toggle.setAccessibleName(text)
        self.label = QLabel(text, self)
        self.label.setBuddy(self.toggle)
        self.label.mousePressEvent = lambda _e: self.toggle.toggle()  # type: ignore[method-assign]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle)
        lay.addWidget(self.label)
        lay.addStretch(1)

    def isChecked(self) -> bool:  # noqa: N802
        return self.toggle.isChecked()

    def setChecked(self, v: bool) -> None:  # noqa: N802
        self.toggle.setChecked(v)
