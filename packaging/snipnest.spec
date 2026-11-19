"""Сборка PyInstaller: один файл (по умолчанию) или каталог.

Запуск:

    SNIPNEST_LAYOUT=onefile uv run pyinstaller packaging/snipnest.spec
    SNIPNEST_LAYOUT=onedir  uv run pyinstaller packaging/snipnest.spec

Переносимый Python (нужный Python-компонентам) берётся из
``build/runtime/python`` — его кладёт ``packaging/build-runtime.sh``.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"
RUNTIME = ROOT / "build" / "runtime" / "python"
LAYOUT = os.environ.get("SNIPNEST_LAYOUT", "onefile")

datas: list[tuple[str, str]] = []
# В один файл переносимый Python входит внутрь: больше некуда его положить.
# В каталоговой сборке его копирует скрипт сборки — рядом с программой,
# иначе он оказался бы внутри _internal и путь к нему был бы неугадаемым.
if LAYOUT == "onefile":
    if RUNTIME.is_dir():
        datas.append((str(RUNTIME), "runtime/python"))
    else:
        print("ПРЕДУПРЕЖДЕНИЕ: нет build/runtime/python — Python-компоненты нельзя будет поставить")

hiddenimports = [
    "keyring.backends.SecretService",
    "keyring.backends.kwallet",
    "keyring.backends.fail",
]

# Модули Qt, которыми приложение не пользуется: без них бандл меньше
# на десятки мегабайт.
excludes = [
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "tkinter",
    "matplotlib",
    "numpy",
    "PIL",
    "pytest",
]

analysis = Analysis(
    [str(ROOT / "packaging" / "entry.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(analysis.pure)

if LAYOUT == "onefile":
    exe = EXE(
        pyz,
        analysis.scripts,
        analysis.binaries,
        analysis.datas,
        [],
        name="snipnest",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "logo" / "snipnest.png"),
    )
else:
    exe = EXE(
        pyz,
        analysis.scripts,
        [],
        exclude_binaries=True,
        name="snipnest",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "logo" / "snipnest.png"),
    )
    coll = COLLECT(
        exe,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=False,
        name="snipnest",
    )
