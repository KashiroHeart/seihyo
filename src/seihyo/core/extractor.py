"""pdfplumber を使った表の抽出。

処理の流れ:
    1. ページごとに重ね打ち文字を除去し、罫線ベースで表を検出する
    2. 各セルの bbox から行・列の境界を求め、結合セル (rowspan/colspan) を判定する
    3. 文字の中心座標でセルに割り当て、行ごとに並べて色ごとの TextRun にまとめる
    4. ページ末尾の表と次ページ先頭の表が同じ列構成なら 1 つの表に結合する
"""

from __future__ import annotations

import bisect
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber

from seihyo.core.color import normalize_text_color
from seihyo.core.models import BBox, Cell, ExtractionResult, Table, TextRun
from seihyo.core.text import normalize_text

# 罫線ベースの検出設定。Excel / Word 出力の PDF は表の罫線が矩形や線として描かれる
TABLE_SETTINGS: dict[str, Any] = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 3,
    "edge_min_length": 3,
}

EDGE_TOLERANCE = 2.0  # 行・列境界を同一とみなす距離 (pt)
COLUMN_MATCH_TOLERANCE = 3.0  # ページ跨ぎ判定で列境界を同一とみなす距離 (pt)
PAGE_MARGIN_RATIO = 0.08  # ヘッダー / フッター領域とみなすページ上下の割合
SPACE_GAP_RATIO = 0.5  # 文字間の隙間がフォントサイズのこの割合を超えたら空白を補う
LINE_GAP_RATIO = 0.5  # top の差がフォントサイズのこの割合を超えたら改行とみなす

ProgressCallback = Callable[[int, int], None]
CancelCheck = Callable[[], bool]


class ExtractionError(Exception):
    """PDF を開けない・解析できない場合の例外。メッセージは利用者向け。"""


class ExtractionCancelled(Exception):
    """利用者が抽出をキャンセルした。"""


@dataclass
class ExtractOptions:
    with_color: bool = True
    merge_across_pages: bool = True


@dataclass
class _Segment:
    """ページ跨ぎ判定のために保持する、ページ上の表 1 つ分の情報。"""

    table: Table
    page_number: int
    bbox: BBox
    col_edges: list[float]
    text_after: bool  # 表より下に本文がある
    text_before: bool  # 表より上に本文がある


# --------------------------------------------------------------------------- #
# 公開 API
# --------------------------------------------------------------------------- #


def extract_tables(
    path: str | Path,
    options: ExtractOptions | None = None,
    progress: ProgressCallback | None = None,
    is_cancelled: CancelCheck | None = None,
) -> ExtractionResult:
    options = options or ExtractOptions()
    path = Path(path)
    result = ExtractionResult(source=path)

    try:
        pdf = pdfplumber.open(path)
    except FileNotFoundError as e:
        raise ExtractionError(f"ファイルが見つかりません: {path}") from e
    except Exception as e:  # pdfminer の例外は種類が多いため一括で扱う
        if "password" in type(e).__name__.lower() or "encrypt" in str(e).lower():
            raise ExtractionError("パスワードで保護された PDF には対応していません。") from e
        raise ExtractionError(f"PDF を開けませんでした: {e}") from e

    pages_segments: list[list[_Segment]] = []
    with pdf:
        total = len(pdf.pages)
        for i, raw_page in enumerate(pdf.pages):
            if is_cancelled and is_cancelled():
                raise ExtractionCancelled
            page_number = i + 1
            try:
                segments = _extract_page(raw_page, page_number, options.with_color)
            except Exception as e:
                result.warnings.append(f"p.{page_number} の解析に失敗しました: {e}")
                segments = []
            if not raw_page.chars:
                result.warnings.append(
                    f"p.{page_number} に文字情報がありません (スキャン画像の可能性があります)。"
                )
            pages_segments.append(segments)
            if progress:
                progress(page_number, total)

    if options.merge_across_pages:
        result.tables = _merge_across_pages(pages_segments)
    else:
        result.tables = [s.table for segs in pages_segments for s in segs]

    if not result.tables:
        result.warnings.append("表が見つかりませんでした。")
    return result


# --------------------------------------------------------------------------- #
# ページ単位の処理
# --------------------------------------------------------------------------- #


def _extract_page(raw_page: Any, page_number: int, with_color: bool) -> list[_Segment]:
    page = raw_page.dedupe_chars()
    found = page.find_tables(TABLE_SETTINGS)
    chars = page.chars
    height = float(page.height)
    header_limit = height * PAGE_MARGIN_RATIO
    footer_limit = height * (1 - PAGE_MARGIN_RATIO)

    segments: list[_Segment] = []
    index = 0
    for ft in sorted(found, key=lambda t: (t.bbox[1], t.bbox[0])):
        built = _build_table(ft.cells, chars, with_color)
        if built is None:
            continue
        cells, n_rows, n_cols, col_edges = built
        if n_rows * n_cols < 2:  # 1 セルだけの枠 (テキストボックス等) は表として扱わない
            continue
        index += 1
        bbox: BBox = tuple(float(v) for v in ft.bbox)  # type: ignore[assignment]
        table = Table(
            pages=(page_number,),
            index_on_page=index,
            bbox=bbox,
            n_rows=n_rows,
            n_cols=n_cols,
            cells=cells,
        )
        text_after = any(
            _is_visible(c) and c["top"] > bbox[3] and c["top"] < footer_limit for c in chars
        )
        text_before = any(
            _is_visible(c) and c["bottom"] < bbox[1] and c["bottom"] > header_limit for c in chars
        )
        segments.append(
            _Segment(
                table, page_number, bbox, [e - bbox[0] for e in col_edges], text_after, text_before
            )
        )
    return segments


def _is_visible(ch: dict[str, Any]) -> bool:
    return bool(ch["text"].strip())


def _cluster(values: Iterable[float], tol: float) -> list[float]:
    """近い値をまとめて昇順の代表値リストを返す。"""
    out: list[float] = []
    for v in sorted(values):
        if out and v - out[-1] <= tol:
            continue
        out.append(v)
    return out


def _nearest(edges: list[float], v: float) -> int:
    i = bisect.bisect_left(edges, v)
    if i == 0:
        return 0
    if i == len(edges):
        return len(edges) - 1
    return i if edges[i] - v < v - edges[i - 1] else i - 1


def _build_table(
    cell_bboxes: list[BBox], chars: list[dict[str, Any]], with_color: bool
) -> tuple[list[Cell], int, int, list[float]] | None:
    if not cell_bboxes:
        return None
    xs = _cluster([v for b in cell_bboxes for v in (b[0], b[2])], EDGE_TOLERANCE)
    ys = _cluster([v for b in cell_bboxes for v in (b[1], b[3])], EDGE_TOLERANCE)
    n_cols, n_rows = len(xs) - 1, len(ys) - 1
    if n_cols < 1 or n_rows < 1:
        return None

    owner: dict[tuple[int, int], int] = {}
    cells: list[Cell] = []
    boxes: list[BBox] = []
    for b in cell_bboxes:
        c0, c1 = _nearest(xs, b[0]), _nearest(xs, b[2])
        r0, r1 = _nearest(ys, b[1]), _nearest(ys, b[3])
        if c1 <= c0 or r1 <= r0:
            continue
        if any((r, c) in owner for r in range(r0, r1) for c in range(c0, c1)):
            continue  # 重複セルは無視
        idx = len(cells)
        cells.append(Cell(row=r0, col=c0, rowspan=r1 - r0, colspan=c1 - c0))
        boxes.append(b)
        for r in range(r0, r1):
            for c in range(c0, c1):
                owner[(r, c)] = idx

    # 文字をセルに割り当てる
    per_cell: list[list[dict[str, Any]]] = [[] for _ in cells]
    x_min, x_max, y_min, y_max = xs[0], xs[-1], ys[0], ys[-1]
    for ch in chars:
        cx = (ch["x0"] + ch["x1"]) / 2
        cy = (ch["top"] + ch["bottom"]) / 2
        if not (x_min <= cx <= x_max and y_min <= cy <= y_max):
            continue
        col = min(max(bisect.bisect_right(xs, cx) - 1, 0), n_cols - 1)
        row = min(max(bisect.bisect_right(ys, cy) - 1, 0), n_rows - 1)
        idx = owner.get((row, col))
        if idx is not None:
            per_cell[idx].append(ch)

    for cell, cell_chars in zip(cells, per_cell, strict=True):
        cell.runs = _chars_to_runs(cell_chars, with_color)

    cells.sort(key=lambda c: (c.row, c.col))
    return cells, n_rows, n_cols, xs


# --------------------------------------------------------------------------- #
# セル内テキストの組み立て
# --------------------------------------------------------------------------- #


def _group_lines(chars: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    lines: list[list[dict[str, Any]]] = []
    line_top = 0.0
    for ch in sorted(chars, key=lambda c: (c["top"], c["x0"])):
        size = float(ch.get("size") or (ch["bottom"] - ch["top"]) or 1)
        if lines and ch["top"] - line_top <= size * LINE_GAP_RATIO:
            lines[-1].append(ch)
        else:
            lines.append([ch])
            line_top = ch["top"]
    for line in lines:
        line.sort(key=lambda c: c["x0"])
    return lines


def _chars_to_runs(chars: list[dict[str, Any]], with_color: bool) -> list[TextRun]:
    """セル内の文字を (文字, 色) 列にし、同色の連続を TextRun にまとめる。"""
    seq: list[tuple[str, str | None]] = []
    for li, line in enumerate(_group_lines(chars)):
        items: list[tuple[str, str | None]] = []
        prev: dict[str, Any] | None = None
        for ch in line:
            text = normalize_text(ch["text"])
            color = normalize_text_color(ch.get("non_stroking_color")) if with_color else None
            if prev is not None and text.strip() and prev["text"].strip():
                size = float(ch.get("size") or 1)
                if ch["x0"] - prev["x1"] > size * SPACE_GAP_RATIO:
                    items.append((" ", None))
            items.append((text, color))
            prev = ch
        # 行頭・行末の空白を除去
        while items and not items[0][0].strip():
            items.pop(0)
        while items and not items[-1][0].strip():
            items.pop()
        if not items:
            continue
        if li and seq:
            seq.append(("\n", None))
        seq.extend(items)

    runs: list[TextRun] = []
    for text, color in seq:
        if not runs:
            runs.append(TextRun(text, color))
        elif not text.strip() or runs[-1].color == color:
            # 空白・改行は色を持たないので直前の run に含める
            runs[-1].text += text
        else:
            runs.append(TextRun(text, color))
    return runs


# --------------------------------------------------------------------------- #
# ページ跨ぎの結合
# --------------------------------------------------------------------------- #


def _columns_match(a: list[float], b: list[float]) -> bool:
    return len(a) == len(b) and all(
        abs(x - y) <= COLUMN_MATCH_TOLERANCE for x, y in zip(a, b, strict=True)
    )


def _can_continue(prev: _Segment, nxt: _Segment) -> bool:
    return (
        nxt.page_number == prev.page_number + 1
        and abs(prev.bbox[0] - nxt.bbox[0]) <= COLUMN_MATCH_TOLERANCE
        and _columns_match(prev.col_edges, nxt.col_edges)
        and not prev.text_after
        and not nxt.text_before
    )


def _append_table(base: Table, add: Table) -> Table:
    add_cells = add.cells
    # 見出し行の繰り返し (Word の「タイトル行の繰り返し」) は除外する
    if base.n_rows and add.n_rows and base.text_matrix()[0] == add.text_matrix()[0]:
        add_cells = [c for c in add.cells if c.row > 0]
        offset_fix = 1
    else:
        offset_fix = 0
    offset = base.n_rows - offset_fix
    for c in add_cells:
        c.row += offset
    return Table(
        pages=base.pages + add.pages,
        index_on_page=base.index_on_page,
        bbox=base.bbox,
        n_rows=base.n_rows + add.n_rows - offset_fix,
        n_cols=base.n_cols,
        cells=base.cells + add_cells,
    )


def _merge_across_pages(pages_segments: list[list[_Segment]]) -> list[Table]:
    tables: list[Table] = []
    carry: _Segment | None = None  # 前ページ末尾の表 (= tables[-1] の末尾部分)
    for segments in pages_segments:
        for i, seg in enumerate(segments):
            if i == 0 and carry is not None and _can_continue(carry, seg):
                tables[-1] = _append_table(tables[-1], seg.table)
            else:
                tables.append(seg.table)
        carry = segments[-1] if segments else None
    return tables
