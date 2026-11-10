"""表のプレビュー (セル内の部分的な文字色・結合セルを再現する)。"""

from __future__ import annotations

import html

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAbstractTextDocumentLayout, QPalette, QTextDocument
from PySide6.QtWidgets import (
    QAbstractItemView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from seihyo.core.models import Cell, Table

HTML_ROLE = Qt.ItemDataRole.UserRole + 1


def cell_to_html(cell: Cell) -> str:
    parts: list[str] = []
    for run in cell.runs:
        text = html.escape(run.text).replace("\n", "<br>")
        parts.append(f'<span style="color:#{run.color}">{text}</span>' if run.color else text)
    return "".join(parts)


def _column_name(i: int) -> str:
    name = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        name = chr(65 + r) + name
    return name


class RichTextDelegate(QStyledItemDelegate):
    """HTML_ROLE の HTML を描画するデリゲート。"""

    def _document(self, option: QStyleOptionViewItem, index) -> QTextDocument:  # noqa: ANN001
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setDocumentMargin(4)
        doc.setHtml(index.data(HTML_ROLE) or "")
        return doc

    def paint(self, painter, option, index) -> None:  # noqa: ANN001
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else QStyle()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        doc = self._document(opt, index)
        ctx = QAbstractTextDocumentLayout.PaintContext()
        if opt.state & QStyle.StateFlag.State_Selected:
            ctx.palette.setColor(
                QPalette.ColorRole.Text, opt.palette.color(QPalette.ColorRole.HighlightedText)
            )
        else:
            ctx.palette.setColor(
                QPalette.ColorRole.Text, opt.palette.color(QPalette.ColorRole.Text)
            )
        painter.save()
        dy = max(0.0, (opt.rect.height() - doc.size().height()) / 2)
        painter.translate(opt.rect.left(), opt.rect.top() + dy)
        painter.setClipRect(0, 0, opt.rect.width(), opt.rect.height())
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: ANN001, N802
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        doc = self._document(opt, index)
        return QSize(int(min(doc.idealWidth(), 400)) + 8, int(doc.size().height()))


class TablePreview(QTableWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setItemDelegate(RichTextDelegate(self))
        self.setWordWrap(True)
        self.setAlternatingRowColors(False)

    def show_table(self, table: Table | None) -> None:
        self.clearSpans()
        self.clear()
        if table is None:
            self.setRowCount(0)
            self.setColumnCount(0)
            return
        self.setRowCount(table.n_rows)
        self.setColumnCount(table.n_cols)
        self.setHorizontalHeaderLabels([_column_name(i) for i in range(table.n_cols)])
        for cell in table.cells:
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, None)
            item.setData(HTML_ROLE, cell_to_html(cell))
            item.setToolTip(cell.text)
            self.setItem(cell.row, cell.col, item)
            if cell.rowspan > 1 or cell.colspan > 1:
                self.setSpan(cell.row, cell.col, cell.rowspan, cell.colspan)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
