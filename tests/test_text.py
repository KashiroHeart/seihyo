from seihyo.core.text import normalize_text


def test_kangxi_radicals_are_normalized():
    assert normalize_text("⽇本") == "日本"  # ⽇本
    assert normalize_text("⻑野") == "長野"  # ⻑野


def test_other_characters_are_kept():
    s = "ＡＢＣ１２３㈱①ｱｲｳ 全角　スペース"
    assert normalize_text(s) == s
