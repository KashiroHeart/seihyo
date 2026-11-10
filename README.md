# seihyo

PDF から表を抽出し、**文字色を保ったまま** Excel / CSV に出力するデスクトップアプリです。

- 対象: Excel / Word から出力した、罫線で区切られた表を含む PDF
- 動作環境: Windows 11 (Python 3.12 以上)

## 使い方

1. **PDF 選択** — PDF を選択 (ドラッグ＆ドロップ可) して「抽出」
   - 設定「文字色を取得する」: オフにすると色を取得せず、すべて既定色として扱います
   - 設定「ページを跨ぐ表を結合する」: 下記の条件を満たす表を 1 つに結合します
2. **プレビューと選択** — 抽出した表を一覧から選んでプレビュー (取得元ページも表示)。出力する表にチェックを入れて「次へ」
3. **出力**
   - Excel に出力: 1 シートに 1 表。文字色・セル内の部分色・結合セルを再現します
   - CSV に出力: 表を 1 つだけ選択した場合のみ。色は保持しません (BOM 付き UTF-8)

### 出力の仕様

| 項目 | 扱い |
|---|---|
| セルの値 | すべて文字列として出力 (`001` や `=...` もそのまま) |
| 黒の文字 | 明示的に黒が指定されていても既定色として扱う |
| 結合セル | Excel では結合を再現。CSV では左上のセルにのみ値を入れる |
| シート名 | `p3_表1` / ページ跨ぎは `p3-4_表1` |

### ページを跨ぐ表の結合条件

次をすべて満たす場合に、前ページ末尾の表と次ページ先頭の表を結合します。

- 次ページの最初の表であり、前ページでは最後の表である
- 列数と列の境界位置 (左端からの距離) が一致する
- 前ページの表の下、次ページの表の上に本文がない (ページ上下 8% のヘッダー / フッター領域は除く)

次ページの先頭行が前ページの先頭行と同じ場合 (Word の「タイトル行の繰り返し」) は、その行を除外します。
1 行がページをまたいで分割されている場合は、別々の行として扱います。

## 開発

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -e ".[dev]"
```

起動:

```bash
python -m seihyo
```

テスト / Lint:

```bash
pytest
```

```bash
ruff check .
```

`tests/fixtures/word_cases.pdf` は Word から出力した実 PDF (行内 / 右寄せ / テキストボックス内 / ページ跨ぎの表) です。

### Windows 向けビルド

```bash
pyinstaller packaging/seihyo.spec --noconfirm
```

`dist/seihyo/seihyo.exe` が生成されます。GitHub Actions (`.github/workflows/ci.yml`) でもテスト後に同じビルドを行い、成果物をアップロードします。

## 構成

```
src/seihyo/
├─ core/            GUI に依存しない処理
│  ├─ extractor.py  pdfplumber による表の検出・セル割り当て・ページ跨ぎ結合
│  ├─ color.py      Gray / RGB / CMYK → "RRGGBB"
│  ├─ text.py       康煕部首などの文字化け補正
│  ├─ models.py     TextRun / Cell / Table / ExtractionResult
│  └─ exporters/    Excel (openpyxl) / CSV
└─ gui/             PySide6 (3 画面を QStackedWidget で切り替え)
```

## ライセンス (依存ライブラリ)

pdfplumber (MIT) / pypdfium2 (Apache-2.0, BSD-3-Clause) / PySide6 (LGPL-3.0) / openpyxl (MIT)
