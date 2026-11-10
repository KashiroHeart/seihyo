# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 設定 (Windows 向け onedir ビルド)
#   pyinstaller packaging/seihyo.spec --noconfirm
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("pdfminer")  # CMap 等 (日本語 PDF の解析に必要)

a = Analysis(
    ["../src/seihyo/__main__.py"],
    pathex=["../src"],
    datas=datas,
    hiddenimports=[],
    excludes=[
        "tkinter",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtPdf",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="seihyo",
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="seihyo", upx=False)
