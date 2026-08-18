# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for Mark-L (MARK XLIX).

Build with:   python build_exe.py
(or directly: pyinstaller MarkL.spec --noconfirm)

ONEDIR, NOT ONEFILE — deliberately:
  * onefile re-extracts the entire bundle to a temp folder on EVERY launch,
    adding seconds of startup. This is a voice assistant; that delay is felt.
  * onefile cannot be updated incrementally — the updater would have to replace
    a single ~300 MB binary instead of the handful of files that changed.
  * onefile keeps the exe locked while running, which complicates self-update.

Output lands in dist/MarkL/. The user runs dist/MarkL/MarkL.exe. Writable user
data (config/, memory/) is created next to that exe; read-only bundled assets
live in dist/MarkL/_internal/. See paths.py for why those must differ.
"""
import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()

sys.path.insert(0, str(SPEC_DIR))
import branding  # noqa: E402  — single source of truth for name/version/copyright

block_cipher = None

# ── Bundled read-only assets ────────────────────────────────────────────────
# (source, destination-inside-bundle). Reached at runtime via paths.resource_path().
datas = [
    (str(SPEC_DIR / "core" / "prompt.txt"),        "core"),
    (str(SPEC_DIR / "dashboard" / "static"),       "dashboard/static"),
    (str(SPEC_DIR / "config" / "jarvis.ico"),      "config"),
    (str(SPEC_DIR / "LICENSE"),                    "."),
]

# Ship these once they exist (i18n catalogues and bundled fonts are planned work).
for optional_dir in ("lang", "fonts"):
    p = SPEC_DIR / optional_dir
    if p.is_dir():
        datas.append((str(p), optional_dir))

_tp = SPEC_DIR / "THIRD_PARTY_NOTICES.txt"
if _tp.exists():
    datas.append((str(_tp), "."))

# ── Hidden imports ──────────────────────────────────────────────────────────
# PyInstaller's static analysis misses anything imported dynamically, inside a
# function, or through COM. Everything below is imported that way somewhere in
# actions/ and would otherwise fail only at runtime, on the user's machine.
hiddenimports = [
    # Own modules imported lazily or inside functions — static analysis misses these.
    "branding", "paths", "i18n", "dashboard.certs",
    # Windows COM / native
    "comtypes", "comtypes.client", "comtypes.stream",
    "pycaw", "pycaw.pycaw",
    "win32com", "win32com.client", "win32gui", "win32api", "win32con",
    "win32clipboard", "win32process", "pythoncom", "pywintypes",
    "win10toast", "pywinauto",
    # Google / AI
    "google.genai", "google.generativeai",
    # Audio / vision
    "sounddevice", "_sounddevice", "cv2", "mss", "numpy",
    # Web / scraping
    "bs4", "duckduckgo_search", "youtube_transcript_api", "requests",
    # Dashboard
    "uvicorn", "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    "fastapi", "starlette", "multipart",
    "cryptography", "qrcode", "qrcode.image.pil",
    # Files / desktop
    "pptx", "send2trash", "psutil",
    "pyautogui", "pygetwindow", "pyperclip", "PIL", "PIL._tkinter_finder",
]

# Excluding these took the build from 4952 MB to something shippable.
# PyInstaller follows imports it finds in the source tree, including from the dead
# core/stt.py, core/tts.py and core/installer.py — which import torch and
# transformers for a local speech pipeline that NOTHING imports. That alone dragged
# in 4 GB of PyTorch. Verified unused before excluding; pandas is NOT excluded
# because actions/file_processor.py genuinely uses it for CSV/Excel.
excludes = [
    # Dead local-speech stack (core/stt.py, core/tts.py — zero importers)
    "torch", "torchvision", "torchaudio", "transformers", "tokenizers",
    "kokoro", "onnxruntime", "safetensors", "huggingface_hub",
    # Legacy Google SDK — the app uses google.genai, never google.generativeai
    "google.generativeai", "googleapiclient", "google_auth_httplib2",
    # Scientific stack nothing here imports
    "scipy", "pyarrow", "sklearn", "matplotlib", "sympy", "networkx",
    # Dev/test tooling
    "tkinter", "pytest", "IPython", "notebook", "jupyter", "pydoc_data",
    # Never mix Qt bindings in one bundle
    "PyQt5", "PySide2", "PySide6",
]

a = Analysis(
    ["main.py"],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MarkL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX-packed exes trip antivirus heuristics constantly
    console=False,           # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(SPEC_DIR / "config" / "jarvis.ico"),
    version="version_info.txt",   # generated by build_exe.py from branding.py
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MarkL",
)
