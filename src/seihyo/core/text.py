"""抽出テキストの正規化。

Word 等が出力した PDF では、ToUnicode の対応により「日」が康煕部首「⽇」(U+2F47)
のような見た目が同じ別の文字として取り出されることがある。
NFKC を全体に掛けると全角英数→半角、㈱→(株) なども変わってしまうため、
部首ブロックの文字だけを対応する統合漢字に置き換える。
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache

# 康煕部首 (U+2F00–U+2FD5) / CJK 部首補助 (U+2E80–U+2EF3)
_RADICAL_RANGES = ((0x2E80, 0x2EFF), (0x2F00, 0x2FDF))


@lru_cache(maxsize=1)
def _radical_table() -> dict[int, str]:
    table: dict[int, str] = {}
    for start, end in _RADICAL_RANGES:
        for cp in range(start, end + 1):
            ch = chr(cp)
            norm = unicodedata.normalize("NFKC", ch)
            if norm != ch and len(norm) == 1:
                table[cp] = norm
    # CJK 部首補助は NFKC で分解されないものが多いため、通常の漢字と同形のものを補う
    table.setdefault(0x2EA0, "民")  # ⺠
    table.setdefault(0x2EC4, "西")  # ⻄
    table.setdefault(0x2ED1, "長")  # ⻑
    table.setdefault(0x2EDD, "食")  # ⻝
    return table


def normalize_text(text: str) -> str:
    return text.translate(_radical_table())
