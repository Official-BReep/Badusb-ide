# -*- coding: utf-8 -*-
"""ScriptMonkey for Flipper Zero — PyQt6 rewrite.
Install: py -m pip install PyQt6
Optional serial support: py -m pip install pyserial
"""
from __future__ import annotations
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import asyncio
import re
import sys
import threading
import time
import traceback
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *


from lib.scriptmonkey_diagnostics import _LOGGER, _log_runtime_event

from lib.Ducky_Highlighter import DuckyHighlighter
from lib.js_highlighter import JavaScriptHighlighter
from lib.git import GitManagerDialog
from lib.Splashscreen import StartupSplash
from lib.Codeeditor import CodeEditor
from lib.BADUSB_IDE import BadUSBIDE


from lib.shared_data import (
    COMMANDS,
    EXAMPLES,
    GROUPS,
    JS_GLOBALS,
    JS_METHODS,
    JS_MODULES,
    KEYS,
    STANDALONE,
    THEMES,
)

def validate_lines(source: str):
    bad=[]
    messages=[]
    for n, raw in enumerate(source.splitlines(),1):
        s=raw.strip()
        if not s or s.startswith("#"): continue
        if s.startswith("ID "):
            if len(s.split()) < 2: bad.append(n); messages.append(f"Zeile {n}: ID benötigt einen Namen")
            continue
        cmd=s.split(None,1)[0].upper(); arg=s[len(s.split(None,1)[0]):].strip()
        if cmd not in COMMANDS:
            # Single key names are valid Ducky instructions.
            if cmd in KEYS and not arg: continue
            bad.append(n)
            messages.append(f"Zeile {n}: Unbekannter Befehl '{cmd}'")
            continue
        if cmd in {"DELAY","HOLD"}:
            try:
                if int(arg) < 0: raise ValueError()
            except ValueError: bad.append(n); messages.append(f"Zeile {n}: {cmd} benötigt eine nicht-negative Millisekundenzahl")
        elif cmd == "REPEAT":
            p=arg.split()
            if len(p)<2 or not p[0].isdigit(): bad.append(n); messages.append(f"Zeile {n}: REPEAT benötigt Anzahl und Befehl")
        elif cmd in STANDALONE and arg:
            bad.append(n)
            messages.append(f"Zeile {n}: {cmd} benötigt keine Argumente")
        elif cmd in {"GUI","CTRL","ALT","SHIFT"} and not arg:
            bad.append(n)
            messages.append(f"Zeile {n}: {cmd} benötigt mindestens eine Taste")
        elif cmd in {"STRING","STRINGLN","ALTSTRING","ALTCHAR"} and not arg:
            bad.append(n)
            messages.append(f"Zeile {n}: {cmd} benötigt Text bzw. ein Zeichen")
    return bad, messages




class LineNumberArea(QWidget):
    def __init__(self, editor): super().__init__(editor); self.editor=editor
    def sizeHint(self): return QSize(self.editor.line_number_width(),0)
    def paintEvent(self,event): self.editor.paint_line_numbers(event)

def main():
    # Windows taskbar groups windows by AppUserModelID. Set it BEFORE creating
    # QApplication; otherwise Windows may keep showing the generic Python icon.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "BadUSBIDE.FlipperPayloadEditor"
            )
        except Exception:
            pass

    _log_runtime_event("main() entered", argv=sys.argv, script=str(Path(__file__).resolve()))
    app = QApplication(sys.argv)
    _log_runtime_event("QApplication created")
    app.setApplicationName("ScriptMonkey")
    icon_path = Path(__file__).resolve().parent / "coding_icon_146067.ico"
    app_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
        # Set the default icon before any top-level windows are created.
        QApplication.setWindowIcon(app_icon)

    splash = StartupSplash(icon_path)
    splash.show()
    QApplication.processEvents()
    startup_steps = [
        (8, "Initialisiere Anwendung …"),
        (18, "Lade Einstellungen …"),
        (30, "Prüfe Editor-Konfiguration …"),
        (42, "Bereite Plugin-Verwaltung vor …"),
        (54, "Initialisiere Marketplace …"),
        (66, "Erstelle Hauptfenster …"),
    ]
    for value, message in startup_steps:
        splash.update_progress(value, message)
        time.sleep(0.12)

    try:
        _log_runtime_event("Constructing main window")
        win = BadUSBIDE()
        _log_runtime_event("Main window constructed")
        if not app_icon.isNull():
            win.setWindowIcon(app_icon)
        splash.update_progress(88, "Stelle Oberfläche fertig …")
        time.sleep(0.12)
        # Show the main window normally even if the saved geometry was minimized/off-screen.
        win.showNormal()
        win.show()
        win.raise_()
        win.activateWindow()
        splash.update_progress(100, "Fertig – öffne ScriptMonkey …")
        time.sleep(0.18)
        splash.close()
        QTimer.singleShot(150, lambda: (win.showNormal(), win.raise_(), win.activateWindow()))
        sys.exit(app.exec())
    except Exception:
        splash.close()
        raise