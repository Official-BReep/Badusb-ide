"""BadUSB IDE for Flipper Zero — PyQt6 rewrite.
Install: py -m pip install PyQt6
Optional serial support: py -m pip install pyserial
"""
from __future__ import annotations
import importlib.util
import json
import os
import shutil
import subprocess
import asyncio
import re
import sys
import threading
import time
import traceback
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import (
    QUrl,
    QRect,
    QSize,
    QStringListModel,
    Qt,
    QTimer,
    QThread,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QFont,
    QKeySequence,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

COMMANDS = {'REM': 'Kommentarzeile',
 'DELAY': 'Warten in Millisekunden, z. B. DELAY 500',
 'STRING': 'Text tippen, z. B. STRING Hallo',
 'STRINGLN': 'Text tippen + Enter',
 'ALTSTRING': 'Text per Alt+NumPad',
 'GUI': 'Windows/Cmd + Taste, z. B. GUI r',
 'CTRL': 'Strg-Kombination, z. B. CTRL SHIFT ESC',
 'ALT': 'Alt-Kombination',
 'SHIFT': 'Shift-Kombination',
 'ENTER': 'Enter-Taste',
 'TAB': 'Tab-Taste',
 'SPACE': 'Leerzeichen',
 'ESC': 'Escape',
 'BACKSPACE': 'Rücktaste',
 'DELETE': 'Entf',
 'PRINTSCREEN': 'Screenshot',
 'CAPSLOCK': 'Feststelltaste',
 'DOWN': 'Pfeil runter',
 'UP': 'Pfeil hoch',
 'LEFT': 'Pfeil links',
 'RIGHT': 'Pfeil rechts',
 'HOME': 'Pos1',
 'END': 'Ende',
 'INSERT': 'Einfg',
 'PAGEUP': 'Bild hoch',
 'PAGEDOWN': 'Bild runter',
 'REPEAT': 'Befehl wiederholen, z. B. REPEAT 5 TAB',
 'WAIT_FOR_BUTTON_PRESS': 'Auf Flipper-Button warten',
 'HOLD': 'Nächsten Befehl für Millisekunden halten',
 'ALTCHAR': 'Alt+NumPad-Zeichen'}
GROUPS = {'Text': ['STRING', 'STRINGLN', 'ALTSTRING', 'ALTCHAR'],
 'Tastenkombinationen': ['GUI', 'CTRL', 'ALT', 'SHIFT'],
 'Tasten': ['ENTER',
            'TAB',
            'SPACE',
            'ESC',
            'BACKSPACE',
            'DELETE',
            'CAPSLOCK',
            'PRINTSCREEN'],
 'Navigation': ['DOWN',
                'UP',
                'LEFT',
                'RIGHT',
                'HOME',
                'END',
                'INSERT',
                'PAGEUP',
                'PAGEDOWN'],
 'Ablaufsteuerung': ['DELAY', 'HOLD', 'REPEAT', 'WAIT_FOR_BUTTON_PRESS'],
 'Sonstiges': ['REM']}
EXAMPLES = {'Hello Notepad': 'ID Hello_Ducky\n'
                  '\n'
                  'REM Öffnet den Ausführen-Dialog und startet Notepad\n'
                  'GUI r\n'
                  'DELAY 500\n'
                  'STRING notepad\n'
                  'ENTER\n'
                  'DELAY 1000\n'
                  'STRINGLN Hallo vom Flipper Zero!\n',
 'Terminal öffnen': 'ID Open_Terminal\n'
                    '\n'
                    'REM Öffnet Windows Terminal (abhängig von Windows-Version)\n'
                    'GUI r\n'
                    'DELAY 500\n'
                    'STRING wt\n'
                    'ENTER\n'
                    'DELAY 1200\n'
                    'STRINGLN whoami\n',
 'Warten auf Button': 'ID Wait_For_Button\n'
                      '\n'
                      'REM Startet erst nach Bestätigung am Flipper\n'
                      'WAIT_FOR_BUTTON_PRESS\n'
                      'DELAY 200\n'
                      'GUI r\n'
                      'DELAY 500\n'
                      'STRINGLN notepad\n'}
JS_GLOBALS = {'let': 'Variable deklarieren',
 'if': 'Bedingung',
 'else': 'Alternativzweig',
 'for': 'Schleife',
 'while': 'Schleife',
 'function': 'Funktion definieren',
 'return': 'Wert zurückgeben',
 'true': 'Boolescher Wert',
 'false': 'Boolescher Wert',
 'null': 'Nullwert',
 'undefined': 'Nicht definierter Wert',
 'print': 'Text in die JS-Konsole ausgeben',
 'delay': 'Ausführung anhalten',
 'require': 'Flipper-JS-Modul laden',
 'load': 'Weitere JS-Datei laden',
 'JSON': 'JSON-Hilfsfunktionen',
 'Math': 'Mathematikfunktionen',
 'parseInt': 'Ganzzahl parsen',
 'parseFloat': 'Fließkommazahl parsen',
 'checkSdkFeatures': 'Firmware-Features prüfen',
 'doesSdkSupport': 'Firmware-Feature abfragen'}
JS_MODULES = {'badusb': 'USB-HID / Tastatureingabe',
 'storage': 'Dateisystem',
 'event_loop': 'Ereignisgesteuerte Abläufe',
 'flipper': 'Geräteinformationen',
 'gpio': 'GPIO-Pins',
 'gui': 'Flipper-GUI',
 'math': 'Mathematik',
 'notification': 'LED / Ton / Vibration',
 'serial': 'UART / serielle Schnittstelle',
 'i2c': 'I2C (Momentum)',
 'spi': 'SPI (Momentum)',
 'subghz': 'Sub-GHz (Momentum)',
 'blebeacon': 'BLE-Beacons (Momentum)',
 'vgm': 'Video Game Module (Momentum)',
 'widget': 'GUI-Widgets (Momentum)',
 'usbdisk': 'Virtuelles USB-Laufwerk (Momentum)'}
JS_METHODS = {'badusb': {'setup': 'USB-HID initialisieren',
            'isConnected': 'USB-Verbindung prüfen',
            'print': 'Text tippen',
            'println': 'Text tippen und Enter senden',
            'press': 'Taste(n) drücken',
            'hold': 'Taste(n) halten',
            'release': 'Tasten loslassen',
            'quit': 'USB-HID freigeben'},
 'storage': {'exists': 'Pfad prüfen',
             'readDirectory': 'Verzeichnisinhalt lesen',
             'openFile': 'Datei öffnen',
             'read': 'Dateiinhalt lesen',
             'write': 'Dateiinhalt schreiben',
             'mkdir': 'Verzeichnis erstellen',
             'copy': 'Datei kopieren',
             'rename': 'Datei umbenennen',
             'remove': 'Datei entfernen',
             'stat': 'Dateiinformationen abrufen'},
 'event_loop': {'subscribe': 'Ereignis abonnieren',
                'run': 'Event Loop starten',
                'stop': 'Event Loop stoppen'},
 'notification': {'success': 'Erfolg signalisieren',
                  'error': 'Fehler signalisieren',
                  'message': 'Benachrichtigung anzeigen'},
 'flipper': {'getName': 'Flipper-Namen abrufen',
             'getBatteryLevel': 'Akkustand abrufen',
             'firmwareVendor': 'Firmware-Anbieter ermitteln'},
 'gpio': {'get': 'Pinwert lesen',
          'set': 'Pinwert setzen',
          'init': 'GPIO initialisieren'},
 'gui': {'dialog': 'Dialog anzeigen',
         'textBox': 'Text anzeigen',
         'submenu': 'Menü anzeigen',
         'textInput': 'Texteingabe anzeigen'},
 'serial': {'setup': 'Serielle Schnittstelle initialisieren',
            'write': 'Daten senden',
            'read': 'Daten empfangen'},
 'blebeacon': {'isActive': 'Beacon-Status prüfen',
               'setConfig': 'Beacon konfigurieren',
               'setData': 'Paketdaten setzen',
               'start': 'Beacon starten',
               'stop': 'Beacon stoppen',
               'keepAlive': 'Beacon weiterlaufen lassen'},
 'subghz': {'setup': 'Sub-GHz initialisieren',
            'getFrequency': 'Frequenz abfragen',
            'getRssi': 'Signalstärke abfragen',
            'getState': 'Funkzustand abfragen',
            'setFrequency': 'Frequenz einstellen',
            'setIdle': 'IDLE-Modus',
            'setRx': 'Empfang aktivieren',
            'transmitFile': 'Unterstützte Datei senden'},
 'usbdisk': {'createImage': 'Laufwerksabbild erstellen',
             'start': 'USB-Laufwerk bereitstellen',
             'stop': 'Laufwerk trennen'}}

THEMES = {
"Flipper Amber": dict(bg="#12151c", panel="#1a1f29", hover="#242b38", editor="#0e1118", fg="#e8eaf0", muted="#7d8698", accent="#ffb347", key="#6fc3ff", comment="#687386", string="#a8d08d", btn="#2a3242", error="#48232a"),
"Midnight Blue": dict(bg="#101722", panel="#172334", hover="#23354b", editor="#0a111c", fg="#e5efff", muted="#8b9db6", accent="#66c7ff", key="#a6e3a1", comment="#63758d", string="#f9e2af", btn="#25364b", error="#43252d"),
"Nord": dict(bg="#2e3440", panel="#3b4252", hover="#434c5e", editor="#242933", fg="#eceff4", muted="#aab4c5", accent="#88c0d0", key="#81a1c1", comment="#7b879a", string="#a3be8c", btn="#434c5e", error="#4c2f3a"),
"Light": dict(bg="#e9edf2", panel="#dce3eb", hover="#cbd6e2", editor="#ffffff", fg="#202733", muted="#5d6878", accent="#b35b00", key="#006bb6", comment="#657080", string="#357a38", btn="#cbd6e2", error="#ffe1e1"),
"OLED Black": dict(bg="#000000", panel="#090909", hover="#1c1c1c", editor="#000000", fg="#f4f4f4", muted="#929292", accent="#ff9d00", key="#5ecbff", comment="#777777", string="#9be28f", btn="#222222", error="#431b22")
}
STANDALONE = {"ENTER","TAB","SPACE","ESC","PRINTSCREEN","CAPSLOCK","BACKSPACE","DELETE","WAIT_FOR_BUTTON_PRESS","DOWN","UP","LEFT","RIGHT","HOME","END","INSERT","PAGEUP","PAGEDOWN"}
KEYS = {"ENTER","TAB","SPACE","ESC","BACKSPACE","DELETE","PRINTSCREEN","CAPSLOCK","DOWN","UP","LEFT","RIGHT","HOME","END","INSERT","PAGEUP","PAGEDOWN","NUMLOCK", *[chr(i) for i in range(65,91)], *[str(i) for i in range(10)]}

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

def estimate_runtime_ms(source: str):
    total=0
    hold_next=0
    for raw in source.splitlines():
        s=raw.strip()
        p=s.split(None,1)
        if not p: continue
        cmd=p[0].upper()
        arg=p[1].strip() if len(p)>1 else ""
        if cmd=="DELAY":
            try: total += max(0,int(arg))
            except ValueError: pass
        elif cmd=="HOLD":
            try: hold_next=max(0,int(arg)); total += hold_next
            except ValueError: pass
        elif cmd=="REPEAT":
            m=re.match(r"(\d+)\s+",arg)
            if m: total += max(0,int(m.group(1))-1)*100
        elif cmd in {"STRING","STRINGLN","ALTSTRING"}: total += len(arg)*35
        elif cmd in {"ENTER","TAB","GUI","CTRL","ALT","SHIFT"}: total += 100
    return total

class DuckyHighlighter(QSyntaxHighlighter):
    def __init__(self, doc, theme):
        super().__init__(doc)
        self.theme=theme
    def set_theme(self, theme): self.theme=theme; self.rehighlight()
    def highlightBlock(self, text):
        t=self.theme
        def fmt(color,bold=False):
            f=QTextCharFormat()
            f.setForeground(QColor(color))
            f.setFontWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
            return f
        if text.lstrip().startswith(("REM", "#")):
            self.setFormat(0,len(text),fmt(t["comment"]))
            return
        m=re.match(r"\s*([A-Za-z_]+)",text)
        if m:
            cmd=m.group(1).upper()
            if cmd in COMMANDS or cmd in KEYS or cmd=="ID": self.setFormat(m.start(1),len(m.group(1)),fmt(t["accent"] if cmd in COMMANDS else t["key"],True))
        if re.match(r"\s*ID\b",text):
            m=re.match(r"\s*ID\b",text)
            self.setFormat(m.start(),len(m.group()),fmt("#c792ea",True))
        if re.match(r"\s*(STRING|STRINGLN|ALTSTRING)\s+",text,re.I):
            m=re.match(r"\s*(STRING|STRINGLN|ALTSTRING)\s+",text,re.I)
            self.setFormat(m.end(),len(text)-m.end(),fmt(t["string"]))

class JavaScriptHighlighter(QSyntaxHighlighter):
    """Expanded syntax highlighting for JavaScript and Flipper mJS."""
    KEYWORDS = set("let const var function return if else for while do break continue switch case default try catch finally throw new delete typeof void in of this true false null undefined async await class extends import export from as yield instanceof static super".split())
    BUILTINS = set("print delay require parseInt parseFloat JSON Math Object Array String Number Boolean Promise Date Error RegExp Map Set Symbol BigInt checkSdkFeatures doesSdkSupport load".split())
    MODULES = set("badusb storage event_loop flipper gpio gui math notification serial i2c spi subghz blebeacon vgm widget usbdisk".split())

    def __init__(self, doc, theme):
        super().__init__(doc); self.theme = theme

    def set_theme(self, theme):
        self.theme = theme; self.rehighlight()

    def highlightBlock(self, text):
        t = self.theme
        def fmt(color, bold=False, italic=False):
            f=QTextCharFormat(); f.setForeground(QColor(color))
            if bold: f.setFontWeight(QFont.Weight.Bold)
            if italic: f.setFontItalic(True)
            return f
        comment=fmt(t.get("comment","#6a9955"),italic=True)
        string_fmt=fmt(t.get("string","#ce9178"))
        keyword_fmt=fmt("#c792ea",True)
        builtin_fmt=fmt(t.get("accent","#ffb454"),True)
        module_fmt=fmt("#82aaff",True)
        number_fmt=fmt("#b5cea8")
        operator_fmt=fmt("#89ddff")
        # Carry multiline block comments across text blocks.
        in_block = self.previousBlockState() == 1
        i=0
        while i<len(text):
            if in_block:
                end=text.find("*/",i)
                if end<0:
                    self.setFormat(i,len(text)-i,comment); self.setCurrentBlockState(1); return
                self.setFormat(i,end+2-i,comment); i=end+2; in_block=False; continue
            if text.startswith("//",i):
                self.setFormat(i,len(text)-i,comment); break
            if text.startswith("/*",i):
                end=text.find("*/",i+2)
                if end<0:
                    self.setFormat(i,len(text)-i,comment); in_block=True; self.setCurrentBlockState(1); break
                self.setFormat(i,end+2-i,comment); i=end+2; continue
            if text[i] in "\"'`":
                quote=text[i]; j=i+1; escaped=False
                while j<len(text):
                    ch=text[j]
                    if escaped: escaped=False
                    elif ch=="\\": escaped=True
                    elif ch==quote: j+=1; break
                    j+=1
                self.setFormat(i,j-i,string_fmt); i=j; continue
            number=re.match(r"(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",text[i:])
            if number:
                self.setFormat(i,len(number.group()),number_fmt); i+=len(number.group()); continue
            ident=re.match(r"[A-Za-z_$][\w$]*",text[i:])
            if ident:
                word=ident.group(); end=i+len(word)
                if word in self.KEYWORDS: self.setFormat(i,len(word),keyword_fmt)
                elif word in self.BUILTINS: self.setFormat(i,len(word),builtin_fmt)
                elif word in self.MODULES: self.setFormat(i,len(word),module_fmt)
                elif re.match(r"\s*\(",text[end:]): self.setFormat(i,len(word),fmt("#82aaff"))
                i=end; continue
            if text[i] in "=+-*/%<>!&|^~?:": self.setFormat(i,1,operator_fmt)
            elif text[i] in "(){}[];.,": self.setFormat(i,1,fmt("#89ddff",True))
            i+=1
        self.setCurrentBlockState(1 if in_block else 0)


class LineNumberArea(QWidget):
    def __init__(self, editor): super().__init__(editor); self.editor=editor
    def sizeHint(self): return QSize(self.editor.line_number_width(),0)
    def paintEvent(self,event): self.editor.paint_line_numbers(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, theme_getter, parent=None):
        super().__init__(parent)
        self.theme_getter=theme_getter
        self.line_area=LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_area_width)
        self.updateRequest.connect(self.update_line_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.highlighter=DuckyHighlighter(self.document(),theme_getter())
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ')*4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.completer = QCompleter([], self)
        self.completer.setWidget(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self.insert_completion)
        self._suggestions_enabled=True
        self.language_mode='badusb'
        self.update_line_area_width(0)
        self.highlight_current_line()
    def line_number_width(self): return 14+self.fontMetrics().horizontalAdvance('9')*(len(str(max(1,self.blockCount())))+1)
    def update_line_area_width(self,_=0): self.setViewportMargins(self.line_number_width(),0,0,0)
    def update_line_area(self,rect,dy):
        if dy: self.line_area.scroll(0,dy)
        else: self.line_area.update(0,rect.y(),self.line_area.width(),rect.height())
        if rect.contains(self.viewport().rect()): self.update_line_area_width()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        cr=self.contentsRect()
        self.line_area.setGeometry(QRect(cr.left(),cr.top(),self.line_number_width(),cr.height()))
    def paint_line_numbers(self,event):
        p=QPainter(self.line_area)
        t=self.theme_getter()
        p.fillRect(event.rect(),QColor(t['panel']))
        block=self.firstVisibleBlock()
        number=block.blockNumber()
        top=int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom=top+int(self.blockBoundingRect(block).height())
        while block.isValid() and top<=event.rect().bottom():
            if block.isVisible() and bottom>=event.rect().top():
                p.setPen(QColor(t['muted']))
                p.drawText(0,top,self.line_area.width()-6,self.fontMetrics().height(),Qt.AlignmentFlag.AlignRight,str(number+1))
            block=block.next()
            top=bottom
            bottom=top+int(self.blockBoundingRect(block).height())
            number+=1
    def highlight_current_line(self):
        selections=[]
        if not self.isReadOnly():
            sel=QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor(self.theme_getter()['hover']))
            sel.format.setProperty(QTextFormat.Property.FullWidthSelection,True)
            sel.cursor=self.textCursor()
            sel.cursor.clearSelection()
            selections.append(sel)
        self.setExtraSelections(selections)
    def set_theme(self): self.highlighter.set_theme(self.theme_getter()); self.highlight_current_line(); self.line_area.update()
    def set_language_mode(self, mode):
        self.language_mode = mode
        old = self.highlighter
        if mode == "javascript" and not isinstance(old, JavaScriptHighlighter):
            self.highlighter = JavaScriptHighlighter(self.document(), self.theme_getter())
            old.setDocument(None)
        elif mode == "badusb" and not isinstance(old, DuckyHighlighter):
            self.highlighter = DuckyHighlighter(self.document(), self.theme_getter())
            old.setDocument(None)
        self.highlighter.rehighlight()
    def current_prefix(self):
        cur=self.textCursor(); block=cur.block().text()[:cur.positionInBlock()]
        m=re.search(r"([A-Za-z_$][\w$]*)$", block)
        return block, (m.group(1) if m else "")
    def show_suggestions(self, force=False):
        if not self._suggestions_enabled: self.completer.popup().hide(); return
        block,prefix=self.current_prefix()
        candidates={}
        # Offer the complete module catalogue as soon as the user types require,
        # as well as while entering the module name inside require(...).
        require_context = self.language_mode == 'javascript' and bool(
            re.search(r"require\s*(?:\(\s*(?:['\"][^'\"]*)?)?$", block)
        )
        if self.language_mode == 'javascript':
            if require_context:
                candidates = JS_MODULES
            else:
                om=re.search(r"([A-Za-z_$][\w$]*)\.$", block[:len(block)-len(prefix)] if prefix else block)
                if om: candidates=JS_METHODS.get(om.group(1), {})
                else: candidates={**JS_GLOBALS, **JS_MODULES}
        else:
            # Complete only the first token on a line; command names and key names are both useful.
            if not block.strip() or re.fullmatch(r"\s*[A-Za-z_]*",block): candidates={**COMMANDS, **{k:'Tastenkürzel' for k in KEYS if k not in COMMANDS}}
        context_completion = self.language_mode == 'javascript' and (block.rstrip().endswith('.') or require_context)
        if not candidates or (not prefix and not force and not context_completion): self.completer.popup().hide(); return
        labels=sorted(candidates, key=str.lower)
        self.completer.setModel(QStringListModel(labels, self.completer))
        self.completer.setCompletionPrefix(prefix)
        popup=self.completer.popup()
        popup.setCurrentIndex(self.completer.completionModel().index(0,0))
        cr=self.cursorRect()
        cr.setWidth(popup.sizeHintForColumn(0)+popup.verticalScrollBar().sizeHint().width()+24)
        self.completer.complete(cr)
    def insert_completion(self, completion):
        cur = self.textCursor()
        block, prefix = self.current_prefix()
        if prefix:
            cur.movePosition(cur.MoveOperation.Left, cur.MoveMode.KeepAnchor, len(prefix))
        line = self.textCursor().block().text()
        before = line[:self.textCursor().positionInBlock()]
        after = line[self.textCursor().positionInBlock():]
        if self.language_mode == 'javascript' and re.search(r"\brequire\s*$", before):
            # Selecting a module from the bare `require` suggestion builds the
            # complete call, including its semicolon.
            cur.insertText('require(\"' + completion + '\");')
        elif self.language_mode == 'javascript' and re.search(r"require\s*\(\s*[\"'][^\"']*$", before):
            # We're inside the module string. Fill the module, then reuse the
            # auto-inserted quote and parenthesis and append a semicolon.
            cur.insertText(completion)
            pos = cur.position()
            tail = cur.block().text()[pos:]
            if tail.startswith('\")'):
                cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, 2)
                if self.document().characterAt(cur.position()) != ';':
                    cur.insertText(';')
            elif tail.startswith("')"):
                cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, 2)
                if self.document().characterAt(cur.position()) != ';':
                    cur.insertText(';')
        elif self.language_mode == 'javascript' and re.search(r"require\s*\(\s*$", before):
            cur.insertText('\"' + completion + '\");')
        else:
            cur.insertText(completion)
        if self.language_mode == 'badusb' and completion in COMMANDS and completion not in STANDALONE and completion != 'WAIT_FOR_BUTTON_PRESS':
            cur.insertText(' ')
        self.setTextCursor(cur)

    def keyPressEvent(self, event):
        popup = self.completer.popup()
        if popup.isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab):
                idx = popup.currentIndex()
                if idx.isValid():
                    self.completer.activated.emit(idx.data())
                    return
            if event.key() == Qt.Key.Key_Escape:
                popup.hide(); return
            if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
                super().keyPressEvent(event); return
        if self.language_mode == 'javascript':
            pairs = {'(': ')', '[': ']', '{': '}', '\"': '\"', "'": "'", '`': '`'}
            typed = event.text()
            cur = self.textCursor()
            # Skip an automatically inserted closing character when the user types it.
            if typed in (')', ']', '}', '\"', "'", '`') and not cur.hasSelection():
                following = self.document().characterAt(cur.position())
                if following == typed:
                    cur.movePosition(QTextCursor.MoveOperation.Right); self.setTextCursor(cur); return
            if event.key() == Qt.Key.Key_Backspace and not cur.hasSelection() and cur.position() > 0:
                left = self.document().characterAt(cur.position()-1)
                right = self.document().characterAt(cur.position())
                if (left, right) in [(a,b) for a,b in pairs.items()]:
                    cur.beginEditBlock(); cur.deletePreviousChar(); cur.deleteChar(); cur.endEditBlock(); self.setTextCursor(cur); return
            if typed in pairs and not cur.hasSelection():
                super().keyPressEvent(event)
                cur = self.textCursor()
                cur.insertText(pairs[typed])
                cur.movePosition(QTextCursor.MoveOperation.Left)
                self.setTextCursor(cur)
                if typed in ('\"', "'", '`'):
                    self.show_suggestions()
                return
            if event.key() == Qt.Key.Key_Tab:
                cur.insertText('    '); return
        if event.key() == Qt.Key.Key_Space and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.show_suggestions(True); return
        super().keyPressEvent(event)
        if (event.text() and (event.text().isalnum() or event.text() in ("_", "$", ".", "(", ")", '\"', "'"))) or event.key() == Qt.Key.Key_Backspace:
            self.show_suggestions()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Escape):
            popup.hide()

@dataclass
class Document:
    editor: CodeEditor
    path: Path|None = None
    dirty: bool = False

class OllamaWorker(QThread):
    finished_text = pyqtSignal(str, str)
    def __init__(self, base_url, model, prompt, context):
        super().__init__()
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.prompt = prompt
        self.context = context
    def run(self):
        try:
            payload = {
                "model": self.model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "Du bist ein lokaler Programmierassistent in einer Flipper Zero IDE. Hilf bei JavaScript/mJS und BadUSB/DuckyScript. Erkläre Unsicherheiten und erfinde keine API-Funktionen. Gib bei Code-Aufgaben möglichst den vollständigen Code in einem Codeblock zurück."},
                    {"role": "user", "content": self.prompt + ("\n\nAktueller Editorinhalt:\n```\n" + self.context + "\n```" if self.context else "")}
                ]
            }
            req = urllib.request.Request(self.base_url + '/api/chat', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type':'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=180) as response:
                data = json.loads(response.read().decode('utf-8'))
            self.finished_text.emit(data.get('message', {}).get('content', '(Leere Antwort)'), '')
        except Exception as ex:
            self.finished_text.emit('', f'{type(ex).__name__}: {ex}')

class BadUSBIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BadUSB IDE · Flipper Zero Payload Editor")
        self.resize(1350,850)
        self.settings_path=Path.home()/".badusb_ide_pyqt6.json"
        self.settings=self.read_settings()
        # Older versions treated the user's home folder as a project by default.
        # Migrate that implicit default once, but preserve a folder explicitly chosen by the user.
        try:
            if not self.settings.get('project_folder_explicit', False):
                home = Path.home().resolve()
                saved = Path(self.settings.get('last_directory') or home).expanduser().resolve()
                if saved == home:
                    self.settings['last_directory'] = str(Path.cwd())
                saved_project = Path(self.settings.get('recent_project_folder') or home).expanduser().resolve()
                if saved_project == home:
                    self.settings['recent_project_folder'] = str(Path.cwd())
        except (OSError, TypeError, ValueError):
            self.settings['last_directory'] = str(Path.cwd())
            self.settings['recent_project_folder'] = str(Path.cwd())
        self.settings.setdefault('theme', 'Flipper Amber')
        self.settings.setdefault('last_directory', str(Path.cwd()))
        self.settings.setdefault('recent_project_folder', self.settings.get('last_directory', str(Path.cwd())))
        recent_folders = self.settings.get('recent_project_folders', [])
        self.settings['recent_project_folders'] = recent_folders if isinstance(recent_folders, list) else []
        self.settings.setdefault('font_size', 11)
        self.settings.setdefault('live_check', True)
        self.settings.setdefault('autocomplete', True)
        self.settings.setdefault('show_output', True)
        self.settings.setdefault('output_height', 130)
        self.settings.setdefault('palette_collapsed', False)
        self.settings.setdefault('confirm_before_close', True)
        self.settings.setdefault('default_extension', '.txt')
        self.settings.setdefault('remember_window_size', True)
        self.settings.setdefault('font_family', 'Consolas')
        self.settings.setdefault('tab_width', 4)
        self.settings.setdefault('word_wrap', False)
        self.settings.setdefault('output_max_blocks', 1500)
        self.settings.setdefault('show_commands', True)
        self.settings.setdefault('show_ollama', False)
        self.settings.setdefault('show_file_explorer', True)
        self.settings.setdefault('show_status_bar', True)
        self.theme_name=self.settings.get('theme','Flipper Amber')
        self.theme=THEMES.get(self.theme_name,THEMES['Flipper Amber']).copy()
        self.docs={}
        self.addon_actions=[]
        self.addon_modules=[]
        self.addon_records={}
        self.addon_docks=[]
        self.serial_conn=None
        self.serial_port=None
        self.serial_lock=threading.RLock()
        self.language_mode='badusb'
        self._build_ui()
        self._build_menus()
        self.apply_theme()
        self.new_tab()
        self.apply_preferences()
        self.update_working_directory()
        self._load_enabled_addons()
        # Restore the final layout only after every built-in and enabled plugin
        # dock has been created; otherwise Qt cannot restore plugin panel positions.
        self._restore_window_layout()
        self.statusBar().showMessage("Bereit · PyQt6")
    def read_settings(self):
        try: return json.loads(self.settings_path.read_text(encoding='utf-8'))
        except Exception: return {}
    def _restore_window_layout(self):
        """Restore saved geometry and dock layout after all docks exist."""
        if not self.settings.get('remember_window_size', True):
            return
        size = self.settings.get('window_size')
        if isinstance(size, list) and len(size) == 2:
            try:
                self.resize(max(800, int(size[0])), max(600, int(size[1])))
            except (TypeError, ValueError):
                pass
        saved_geometry = self.settings.get('window_geometry')
        if saved_geometry:
            try:
                self.restoreGeometry(bytes.fromhex(saved_geometry))
            except (ValueError, TypeError):
                pass
        saved_dock_state = self.settings.get('dock_state')
        if saved_dock_state:
            try:
                self.restoreState(bytes.fromhex(saved_dock_state), 1)
            except (ValueError, TypeError):
                pass

    def save_settings(self):
        try:
            self.settings['theme'] = self.theme_name
            if hasattr(self, 'palette'):
                self.settings['palette_collapsed'] = self.palette.isHidden()
            if hasattr(self, 'ollama_dock'):
                self.settings['ollama_panel_collapsed'] = not self.ollama_dock.isVisible()
            if hasattr(self, 'output_dock'):
                self.settings['show_output'] = self.output_dock.isVisible()
            if hasattr(self, 'ollama_url'):
                self.settings['ollama_url'] = self.ollama_url.text().strip()
            if hasattr(self, 'ollama_model'):
                self.settings['ollama_model'] = self.ollama_model.currentText().strip()
            if hasattr(self, 'output'):
                self.settings['show_output'] = not self.output.isHidden()
                self.settings['output_height'] = self.output.maximumHeight()
            if self.settings.get('remember_window_size', True):
                self.settings['window_size'] = [self.width(), self.height()]
                self.settings['window_geometry'] = bytes(self.saveGeometry()).hex()
                self.settings['dock_state'] = bytes(self.saveState(1)).hex()
            self.settings_path.write_text(json.dumps(self.settings, indent=2), encoding='utf-8')
        except OSError:
            pass

    def working_directory(self):
        doc = self.current_doc() if hasattr(self, 'tabs') else None
        if doc and doc.path:
            return doc.path.parent
        raw = self.settings.get('last_directory') or str(Path.home())
        return Path(raw).expanduser()

    def update_working_directory(self):
        if not hasattr(self, 'working_dir_label'):
            return
        path = self.working_directory()
        self.working_dir_label.setText(f"Arbeitsverzeichnis: {path}")
        self.working_dir_label.setToolTip(str(path))
        # Keep the explorer on its explicitly selected project folder. Only follow
        # the editor when the active tab has a real local file path.
        doc = self.current_doc() if hasattr(self, 'tabs') else None
        if hasattr(self, 'file_explorer_path') and doc and doc.path:
            self.file_explorer_path.setText(str(doc.path.parent))
            self.refresh_local_file_explorer(doc.path.parent)

    def apply_preferences(self):
        if hasattr(self, 'output_dock'):
            self.output_dock.setVisible(bool(self.settings.get('show_output', True)))
        if hasattr(self, 'palette_dock'):
            self.palette_dock.setVisible(bool(self.settings.get('show_commands', True)))
        if hasattr(self, 'ollama_dock'):
            self.ollama_dock.setVisible(bool(self.settings.get('show_ollama', not self.settings.get('ollama_panel_collapsed', True))))
        if hasattr(self, 'file_explorer_dock'):
            self.file_explorer_dock.setVisible(bool(self.settings.get('show_file_explorer', True)))
        if hasattr(self, 'statusBar'):
            self.statusBar().setVisible(bool(self.settings.get('show_status_bar', True)))
        if hasattr(self, 'output'):
            self.output.setMaximumBlockCount(int(self.settings.get('output_max_blocks', 1500)))
        if hasattr(self, 'ollama_url'):
            self.ollama_url.setText(self.settings.get('ollama_url', 'http://localhost:11434'))
        if hasattr(self, 'ollama_model'):
            self.ollama_model.setCurrentText(self.settings.get('ollama_model', ''))
        for editor in getattr(self, 'docs', {}).keys():
            editor._suggestions_enabled = bool(self.settings.get('autocomplete', True))
            editor.setFont(QFont(self.settings.get('font_family', 'Consolas'), int(self.settings.get('font_size', 11))))
            editor.setTabStopDistance(editor.fontMetrics().horizontalAdvance(' ') * int(self.settings.get('tab_width', 4)))
            editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth if self.settings.get('word_wrap', False) else QPlainTextEdit.LineWrapMode.NoWrap)
            editor.highlight_current_line = editor.highlight_current_line
            if not self.settings.get('highlight_current_line', True):
                editor.setExtraSelections([])
            else:
                editor.highlight_current_line()
    def _build_ui(self):
        self.setDockNestingEnabled(True)
        tb=QToolBar("Hauptwerkzeuge")
        tb.setMovable(False)
        self.main_toolbar=tb
        self.addToolBar(tb)
        for label,slot in [("Neu",self.new_tab),("Öffnen",self.open_file),("Speichern",self.save_file),("Prüfen",self.check_payload),("Vorschau",self.preview),("JS formatieren",self.format_javascript)]:
            a=QAction(label,self); a.triggered.connect(lambda _checked=False, cb=slot: cb()); tb.addAction(a)
        tb.addSeparator()
        tb.addWidget(QLabel(" Theme: "))
        self.theme_combo=QComboBox()
        self.theme_combo.addItems(THEMES)
        self.theme_combo.setCurrentText(self.theme_name)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        tb.addWidget(self.theme_combo)
        # The editor is the central workspace. Tool panels are independent docks,
        # so they can be hidden, floated, tabified, or moved to any dock area.
        self.tabs=QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_current_tab_changed)
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.tab_context_menu)
        self.setCentralWidget(self.tabs)

        # Command palette dock: expanding/collapsing the tree only affects its contents;
        # the whole panel itself is shown/hidden from the View menu or its dock close button.
        self.palette_dock = QDockWidget("Befehle", self)
        self.palette_dock.setObjectName("CommandPaletteDock")
        self.palette_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.palette_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        palette_panel = QWidget()
        palette_layout = QVBoxLayout(palette_panel)
        palette_layout.setContentsMargins(6, 6, 6, 6)
        self.palette_toggle = QPushButton('▼ Befehle')
        self.palette_toggle.setCheckable(True)
        self.palette_toggle.setChecked(not bool(self.settings.get('palette_collapsed', False)))
        self.palette_toggle.clicked.connect(self.toggle_palette)
        palette_layout.addWidget(self.palette_toggle)
        self.palette_search = QLineEdit()
        self.palette_search.setPlaceholderText("Befehl suchen …")
        self.palette_search.textChanged.connect(self.filter_palette)
        palette_layout.addWidget(self.palette_search)
        self.palette = QTreeWidget()
        self.palette.setHeaderHidden(True)
        self.palette.itemDoubleClicked.connect(self.insert_palette_item)
        palette_layout.addWidget(self.palette, 1)
        self.palette_dock.setWidget(palette_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.palette_dock)
        self._populate_palette()

        # Ollama is a separate dock rather than an expandable section in the command panel.
        self.ollama_dock = QDockWidget("Lokale KI (Ollama)", self)
        self.ollama_dock.setObjectName("OllamaDock")
        self.ollama_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.ollama_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.mcp_panel = QWidget()
        mcp_layout = QVBoxLayout(self.mcp_panel)
        mcp_layout.setContentsMargins(6, 6, 6, 6)
        self.ollama_url = QLineEdit(self.settings.get('ollama_url', 'http://localhost:11434'))
        self.ollama_url.setPlaceholderText('Ollama URL, z. B. http://localhost:11434')
        self.ollama_url.setToolTip('Lokale Ollama-API-Adresse. Standard: http://localhost:11434')
        mcp_layout.addWidget(QLabel('Ollama-Adresse:'))
        mcp_layout.addWidget(self.ollama_url)
        model_row = QHBoxLayout()
        self.ollama_model = QComboBox()
        self.ollama_model.setEditable(True)
        self.ollama_model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.ollama_model.setCurrentText(self.settings.get('ollama_model', ''))
        self.ollama_refresh = QPushButton('Modelle laden')
        self.ollama_refresh.clicked.connect(self.load_ollama_models)
        model_row.addWidget(self.ollama_model, 1)
        model_row.addWidget(self.ollama_refresh)
        mcp_layout.addWidget(QLabel('Lokales Modell:'))
        mcp_layout.addLayout(model_row)
        self.ollama_prompt = QPlainTextEdit()
        self.ollama_prompt.setPlaceholderText('Frage stellen oder Code ändern lassen …')
        self.ollama_prompt.setMaximumHeight(120)
        mcp_layout.addWidget(self.ollama_prompt)
        ollama_buttons = QHBoxLayout()
        self.ollama_send = QPushButton('KI fragen')
        self.ollama_send.clicked.connect(self.ask_ollama)
        ollama_buttons.addWidget(self.ollama_send)
        self.ollama_include = QCheckBox('Editorinhalt mitsenden')
        self.ollama_include.setChecked(True)
        ollama_buttons.addWidget(self.ollama_include)
        mcp_layout.addLayout(ollama_buttons)
        self.ollama_answer = QPlainTextEdit()
        self.ollama_answer.setReadOnly(False)
        self.ollama_answer.setPlaceholderText('Antwort der lokalen KI …')
        mcp_layout.addWidget(self.ollama_answer, 1)
        answer_buttons = QHBoxLayout()
        self.ollama_insert = QPushButton('Antwort einfügen')
        self.ollama_insert.clicked.connect(self.insert_ollama_answer)
        answer_buttons.addWidget(self.ollama_insert)
        self.ollama_replace = QPushButton('Editorinhalt ersetzen')
        self.ollama_replace.clicked.connect(self.replace_with_ollama_answer)
        answer_buttons.addWidget(self.ollama_replace)
        mcp_layout.addLayout(answer_buttons)
        self.mcp_status = QLabel('Verbindung zur lokalen Ollama-API · kein MCP-Server erforderlich')
        self.mcp_status.setWordWrap(True)
        mcp_layout.addWidget(self.mcp_status)
        self.ollama_dock.setWidget(self.mcp_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ollama_dock)
        self.ollama_dock.setVisible(not bool(self.settings.get('ollama_panel_collapsed', True)))

        # Output is also a dock, not a fixed-height widget below the editor.
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(1500)
        self.output.setPlaceholderText("Prüfergebnisse erscheinen hier …")
        self.output_dock = QDockWidget("Output / Prüfung", self)
        self.output_dock.setObjectName("OutputDock")
        self.output_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.output_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.output_dock.setWidget(self.output)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.output_dock)
        self.output_dock.setVisible(bool(self.settings.get('show_output', True)))

        self.setDockNestingEnabled(True)
        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AnimatedDocks | QMainWindow.DockOption.GroupedDragging)
        self.setStatusBar(QStatusBar())
        self.working_dir_label = QLabel()
        self.statusBar().addPermanentWidget(self.working_dir_label, 1)
        self._build_local_file_explorer()
    def _build_local_file_explorer(self):
        """A local filesystem browser listing folders and files side by side."""
        self.file_explorer_dock = QDockWidget("Dateiexplorer", self)
        self.file_explorer_dock.setObjectName("LocalFileExplorerDock")
        self.file_explorer_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.file_explorer_dock.setMinimumWidth(260)
        self.file_explorer_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        path_row = QHBoxLayout()
        self.file_explorer_mode = "local"
        self.file_explorer_path = QLineEdit(str(self.working_directory()))
        self.file_explorer_path.setPlaceholderText("Verzeichnispfad …")
        self.file_explorer_path.returnPressed.connect(self.open_local_explorer_path)
        path_row.addWidget(self.file_explorer_path, 2)
        self.recent_folders_combo = QComboBox()
        self.recent_folders_combo.setMinimumWidth(170)
        self.recent_folders_combo.setMaximumWidth(260)
        self.recent_folders_combo.setToolTip("Zuletzt besuchte Projektordner auswählen")
        self.recent_folders_combo.activated.connect(self.jump_to_recent_project_folder)
        path_row.addWidget(self.recent_folders_combo, 1)
        go_btn = QPushButton("↵")
        go_btn.setToolTip("Verzeichnis öffnen")
        go_btn.clicked.connect(self.open_local_explorer_path)
        path_row.addWidget(go_btn)
        layout.addLayout(path_row)
        controls = QHBoxLayout()
        up_btn = QPushButton("↑ Übergeordnet")
        up_btn.clicked.connect(self.local_explorer_up)
        refresh_btn = QPushButton("⟳ Aktualisieren")
        refresh_btn.clicked.connect(lambda: self.refresh_local_file_explorer())
        browse_btn = QPushButton("Durchsuchen…")
        browse_btn.clicked.connect(self.choose_local_explorer_directory)
        self.show_flipper_explorer_btn = QPushButton("Flipper-Explorer anzeigen")
        self.show_flipper_explorer_btn.setToolTip("Öffnet einen zweiten Dateiexplorer für den Flipper. Beide Explorer können gleichzeitig sichtbar sein.")
        self.show_flipper_explorer_btn.clicked.connect(self.show_flipper_explorer)
        import_project_btn = QPushButton("Auswahl als Projektordner")
        import_project_btn.setToolTip("Gewählten Ordner zur Projektordner-Historie hinzufügen; bei einer Datei wird ihr enthaltender Ordner verwendet")
        import_project_btn.clicked.connect(self.import_selected_as_project_folder)
        controls.addWidget(up_btn)
        controls.addWidget(refresh_btn)
        controls.addWidget(browse_btn)
        controls.addWidget(self.show_flipper_explorer_btn)
        controls.addWidget(import_project_btn)
        layout.addLayout(controls)
        self.local_file_tree = QTreeWidget()
        self.local_file_tree.setColumnCount(3)
        self.local_file_tree.setHeaderLabels(["Name", "Typ", "Größe"] )
        self.local_file_tree.header().setStretchLastSection(False)
        self.local_file_tree.setColumnWidth(0, 260)
        self.local_file_tree.setColumnWidth(1, 85)
        self.local_file_tree.setColumnWidth(2, 95)
        self.local_file_tree.setUniformRowHeights(True)
        self.local_file_tree.setAlternatingRowColors(True)
        self.local_file_tree.itemClicked.connect(self.local_explorer_item_clicked)
        self.local_file_tree.itemDoubleClicked.connect(self.local_explorer_item_double_clicked)
        self.local_file_tree.itemExpanded.connect(self._populate_local_explorer_children)
        self.local_file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.local_file_tree.customContextMenuRequested.connect(self.local_explorer_context_menu)
        layout.addWidget(self.local_file_tree, 1)
        self.file_explorer_dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.file_explorer_dock)
        recent = self.settings.get('recent_project_folder') or self.settings.get('last_directory') or str(Path.cwd())
        # Older builds accidentally persisted the home directory as the default project.
        # Do not treat that implicit default as a chosen project folder.
        try:
            home = str(Path.home().resolve())
            if str(Path(recent).expanduser().resolve()) == home and not self.settings.get('project_folder_explicit', False):
                saved_last = Path(self.settings.get('last_directory') or '').expanduser()
                recent = str(saved_last if saved_last.is_dir() and saved_last.resolve() != Path.home().resolve() else Path.cwd())
            if not Path(recent).expanduser().is_dir():
                recent = str(Path.cwd())
        except (OSError, TypeError):
            recent = str(Path.cwd())
        self._update_recent_project_folders(recent, refresh_combo=True)
        self.refresh_local_file_explorer(recent)
        self._build_flipper_file_explorer()

    def _build_flipper_file_explorer(self):
        """Create a second, independent Flipper tree; it can be shown beside the PC explorer."""
        self.flipper_file_explorer_dock = QDockWidget("Flipper-Dateiexplorer", self)
        self.flipper_file_explorer_dock.setObjectName("FlipperFileExplorerDock")
        self.flipper_file_explorer_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.flipper_file_explorer_dock.setMinimumWidth(260)
        self.flipper_file_explorer_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        nav = QHBoxLayout()
        self.flipper_explorer_path = QLineEdit(self.settings.get("recent_flipper_folder", "/ext"))
        self.flipper_explorer_path.setPlaceholderText("Flipper-Pfad, z. B. /ext")
        self.flipper_explorer_path.returnPressed.connect(lambda: self.refresh_flipper_dock(self.flipper_explorer_path.text()))
        nav.addWidget(self.flipper_explorer_path, 1)
        go = QPushButton("Öffnen")
        go.clicked.connect(lambda: self.refresh_flipper_dock(self.flipper_explorer_path.text()))
        nav.addWidget(go)
        up = QPushButton("↑")
        up.setToolTip("Übergeordnetes Verzeichnis")
        up.clicked.connect(self.flipper_explorer_up)
        nav.addWidget(up)
        refresh = QPushButton("⟳")
        refresh.setToolTip("Aktualisieren")
        refresh.clicked.connect(lambda: self.refresh_flipper_dock())
        nav.addWidget(refresh)
        layout.addLayout(nav)
        self.flipper_file_tree = QTreeWidget()
        self.flipper_file_tree.setColumnCount(3)
        self.flipper_file_tree.setHeaderLabels(["Name", "Typ", "Größe"])
        self.flipper_file_tree.header().setStretchLastSection(False)
        self.flipper_file_tree.setColumnWidth(0, 260)
        self.flipper_file_tree.setColumnWidth(1, 85)
        self.flipper_file_tree.setColumnWidth(2, 95)
        self.flipper_file_tree.setUniformRowHeights(True)
        self.flipper_file_tree.setAlternatingRowColors(True)
        self.flipper_file_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.flipper_file_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.flipper_file_tree.itemClicked.connect(self.flipper_explorer_item_clicked)
        self.flipper_file_tree.itemDoubleClicked.connect(self.flipper_explorer_item_double_clicked)
        self.flipper_file_tree.itemExpanded.connect(self._populate_flipper_dock_children)
        layout.addWidget(self.flipper_file_tree, 1)
        self.flipper_file_explorer_dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.flipper_file_explorer_dock)
        self.splitDockWidget(self.file_explorer_dock, self.flipper_file_explorer_dock, Qt.Orientation.Horizontal)
        self.flipper_file_explorer_dock.hide()

    def show_flipper_explorer(self):
        if not self._serial_ready():
            QMessageBox.information(self, "Flipper nicht verbunden", "Verbinde zuerst den Flipper über Werkzeuge → Flipper Zero verbinden.")
            return
        self.flipper_file_explorer_dock.show()
        self.flipper_file_explorer_dock.raise_()
        self.refresh_flipper_dock(self.flipper_explorer_path.text() or "/ext")

    def flipper_explorer_up(self):
        current = self.flipper_explorer_path.text().strip().rstrip("/") or "/ext"
        if current not in ("/ext", "/int"):
            self.refresh_flipper_dock(current.rsplit("/", 1)[0] or "/ext")

    @staticmethod
    def _format_file_size(value):
        try:
            size = int(value)
        except (TypeError, ValueError):
            return "—"
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    def _parse_flipper_listing(self, response, base):
        entries=[]; seen=set()
        for raw in response.replace("\r", "\n").splitlines():
            line=raw.strip().strip("\x00")
            if not line or line.lower().startswith(("storage ", "error", "failed", "ok", "directory:", "path:", "listing files", "welcome", "firmware version", "usage:")) or line in (">", ">:"):
                continue
            kind, name, size = "Datei", line, "—"
            m = re.match(r"^(DIR|DIRECTORY|FILE)\s*:?[ \t]+(.+?)\s*$", line, re.I)
            if m:
                kind = "Ordner" if m.group(1).upper() in ("DIR", "DIRECTORY") else "Datei"
                name = m.group(2).strip()
            else:
                m = re.match(r"^\[([dDfF])\]\s*(.+?)\s*$", line)
                if m:
                    kind = "Ordner" if m.group(1).lower() == "d" else "Datei"
                    name = m.group(2).strip()
                elif line.endswith("/"):
                    kind, name = "Ordner", line.rstrip("/")
                else:
                    # Some firmware/CLI builds append a literal "// Size: 1234" to
                    # each file entry. Keep that metadata out of the filename column.
                    size_suffix = re.match(r"^(.*?)\s*(?://\s*)?Size\s*:\s*(\d+)\s*(?:bytes?|B)?\s*$", line, re.I)
                    if size_suffix:
                        name = size_suffix.group(1).strip().rstrip("/")
                        size = self._format_file_size(size_suffix.group(2))
                    patterns = [
                        (r"^(.*?)\s*\((\d+)\s*(?:bytes?|B)\)\s*$", "name_size"),
                        (r"^(.*?)\s{2,}(\d+)\s*(?:bytes?|B)?\s*$", "name_size"),
                        (r"^(.*?)\s+(\d+)\s*(?:bytes?|B)\s*$", "name_size"),
                        (r"^(\d+)\s+(.+?)\s*$", "size_name"),
                    ]
                    for pattern, order in ([] if size_suffix else patterns):
                        m = re.match(pattern, line, re.I)
                        if m:
                            if order == "size_name":
                                size_raw, name = m.group(1), m.group(2).strip()
                            else:
                                name, size_raw = m.group(1).strip(), m.group(2)
                            size = self._format_file_size(size_raw)
                            break
            name = re.sub(r"^(?:[├└│─|+`-]+\s*)+", "", name.strip().strip('"').strip("'"))
            if not name or name in (".","..") or "/" in name or name in seen: continue
            seen.add(name); entries.append((name,kind,size,base.rstrip("/")+"/"+name))
        return entries

    def refresh_flipper_dock(self, directory=None):
        if not self._serial_ready():
            self.statusBar().showMessage("Flipper nicht verbunden", 4000); return
        target=str(directory or self.flipper_explorer_path.text().strip() or "/ext").replace("\\","/").rstrip("/")
        if not (target in ("/ext","/int") or target.startswith(("/ext/","/int/"))) or ".." in target.split("/"):
            QMessageBox.warning(self,"Ungültiger Flipper-Pfad","Verwende einen Pfad unter /ext oder /int."); return
        try:
            response=self._serial_command("storage list "+target, wait=0.25, timeout=3.0)
            entries=self._parse_flipper_listing(response,target)
            self.flipper_explorer_path.setText(target); self.settings["recent_flipper_folder"]=target; self.save_settings()
            self.flipper_file_tree.clear()
            for name,kind,size,full in sorted(entries,key=lambda e:(e[1]!="Ordner",e[0].casefold())):
                item=QTreeWidgetItem([("📁  " if kind=="Ordner" else "📄  ")+name,kind,size if kind!="Ordner" else "—"])
                item.setData(0,Qt.ItemDataRole.UserRole,full); item.setData(0,Qt.ItemDataRole.UserRole+1,"flipper_directory" if kind=="Ordner" else "flipper_file")
                if kind=="Ordner":
                    placeholder=QTreeWidgetItem(["Unterordner beim Aufklappen laden …","",""]); placeholder.setData(0,Qt.ItemDataRole.UserRole+1,"placeholder"); item.addChild(placeholder)
                self.flipper_file_tree.addTopLevelItem(item)
            self.flipper_file_tree.setColumnWidth(0,300); self.flipper_file_tree.setColumnWidth(1,90); self.flipper_file_tree.setColumnWidth(2,110)
            self.statusBar().showMessage(f"Flipper {target} · {len(entries)} Einträge",4000)
        except Exception as exc:
            self.statusBar().showMessage(f"Flipper-Dateiexplorer: {exc}",6000)

    def _populate_flipper_dock_children(self,item):
        if item.data(0,Qt.ItemDataRole.UserRole+1)!="flipper_directory": return
        if item.childCount()!=1 or item.child(0).data(0,Qt.ItemDataRole.UserRole+1)!="placeholder": return
        target=item.data(0,Qt.ItemDataRole.UserRole)
        try:
            response=self._serial_command("storage list "+target,wait=0.25,timeout=3.0)
            entries=self._parse_flipper_listing(response,target); item.takeChildren()
            for name,kind,size,full in sorted(entries,key=lambda e:(e[1]!="Ordner",e[0].casefold())):
                child=QTreeWidgetItem([("📁  " if kind=="Ordner" else "📄  ")+name,kind,size if kind!="Ordner" else "—"])
                child.setData(0,Qt.ItemDataRole.UserRole,full); child.setData(0,Qt.ItemDataRole.UserRole+1,"flipper_directory" if kind=="Ordner" else "flipper_file")
                if kind=="Ordner":
                    placeholder=QTreeWidgetItem(["Unterordner beim Aufklappen laden …","",""]); placeholder.setData(0,Qt.ItemDataRole.UserRole+1,"placeholder"); child.addChild(placeholder)
                item.addChild(child)
        except Exception as exc:
            item.takeChildren(); item.addChild(QTreeWidgetItem([f"Lesefehler: {exc}","",""]))

    def flipper_explorer_item_clicked(self,item,_column=0):
        if item and item.data(0, Qt.ItemDataRole.UserRole + 1) == "flipper_file":
            self._open_flipper_source_in_editor(item.data(0, Qt.ItemDataRole.UserRole))

    def flipper_explorer_item_double_clicked(self, item, _column=0):
        # Single-click already opens a preview. Do not issue a second serial read here.
        return

    def _update_recent_project_folders(self, folder, refresh_combo=False):
        """Remember visited project folders and expose them in the quick-jump list."""
        try:
            folder = str(Path(folder).expanduser().resolve())
        except (OSError, TypeError, ValueError):
            return
        recent = self.settings.get('recent_project_folders', [])
        if not isinstance(recent, list):
            recent = []
        # Most recently visited first; keep the list manageable and avoid duplicates.
        recent = [folder] + [p for p in recent if isinstance(p, str) and p != folder and Path(p).expanduser().is_dir()]
        self.settings['recent_project_folders'] = recent[:20]
        self.settings['recent_project_folder'] = folder
        self.settings['project_folder_explicit'] = True
        if refresh_combo or hasattr(self, 'recent_folders_combo'):
            combo = getattr(self, 'recent_folders_combo', None)
            if combo is not None:
                combo.blockSignals(True)
                combo.clear()
                for path in self.settings['recent_project_folders']:
                    combo.addItem(path, path)
                combo.setCurrentIndex(0 if combo.count() else -1)
                combo.blockSignals(False)
        self.save_settings()

    def jump_to_recent_project_folder(self, index):
        combo = getattr(self, 'recent_folders_combo', None)
        if combo is None or index < 0:
            return
        folder = combo.itemData(index) or combo.itemText(index)
        if folder and Path(folder).expanduser().is_dir():
            self.refresh_local_file_explorer(folder)
        else:
            QMessageBox.information(self, "Projektordner", "Dieser Ordner existiert nicht mehr und wurde aus der Liste entfernt.")
            self._update_recent_project_folders(self.file_explorer_path.text())

    def _add_local_explorer_entry(self, parent, entry):
        """Add one filesystem entry; directories get a placeholder for lazy expansion."""
        try:
            if entry.is_dir():
                item = QTreeWidgetItem(["📁 " + entry.name, "Ordner", "—"])
                item.setData(0, Qt.ItemDataRole.UserRole, str(entry))
                item.setData(0, Qt.ItemDataRole.UserRole + 1, 'directory')
                # A dummy child makes Qt show the expand arrow without scanning the
                # whole subtree until the user actually expands this folder.
                placeholder = QTreeWidgetItem(["Lade Unterordner …", ""])
                placeholder.setData(0, Qt.ItemDataRole.UserRole + 1, 'placeholder')
                item.addChild(placeholder)
            else:
                size = entry.stat().st_size
                if size < 1024:
                    size_text = f"{size} B"
                elif size < 1024 * 1024:
                    size_text = f"{size / 1024:.1f} KB"
                else:
                    size_text = f"{size / (1024 * 1024):.1f} MB"
                item = QTreeWidgetItem(["📄 " + entry.name, entry.suffix.lower().lstrip(".") or "Datei", size_text])
                item.setData(0, Qt.ItemDataRole.UserRole, str(entry))
                item.setData(0, Qt.ItemDataRole.UserRole + 1, 'file')
            if parent is None:
                self.local_file_tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
        except OSError:
            pass

    def _populate_local_explorer_children(self, item):
        """Populate local or Flipper folders lazily when expanded."""
        if self.file_explorer_mode == "flipper":
            self._populate_flipper_explorer_children(item)
            return
        if item.data(0, Qt.ItemDataRole.UserRole + 1) != 'directory':
            return
        if item.childCount() != 1 or item.child(0).data(0, Qt.ItemDataRole.UserRole + 1) != 'placeholder':
            return
        folder = Path(item.data(0, Qt.ItemDataRole.UserRole))
        item.takeChildren()
        try:
            entries = sorted(folder.iterdir(), key=lambda e: (not e.is_dir(), e.name.casefold()))
        except OSError as exc:
            item.addChild(QTreeWidgetItem([f"Zugriff fehlgeschlagen: {exc}", ""]))
            return
        for entry in entries:
            self._add_local_explorer_entry(item, entry)
        self.local_file_tree.sortItems(0, Qt.SortOrder.AscendingOrder)

    def refresh_local_file_explorer(self, directory=None):
        if not hasattr(self, 'local_file_tree'):
            return
        if self.file_explorer_mode == "flipper":
            self.refresh_flipper_file_explorer(directory)
            return
        raw = str(directory) if directory is not None else self.file_explorer_path.text().strip()
        try:
            folder = Path(raw).expanduser().resolve()
            if not folder.is_dir():
                raise NotADirectoryError(f"Kein Verzeichnis: {folder}")
            entries = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))
        except (OSError, ValueError) as exc:
            self.statusBar().showMessage(f"Dateiexplorer: {exc}", 5000)
            return
        self.file_explorer_path.setText(str(folder))
        self._update_recent_project_folders(folder)
        self.local_file_tree.clear()
        for entry in entries:
            self._add_local_explorer_entry(None, entry)
        self.local_file_tree.setColumnWidth(0, 300)
        self.local_file_tree.setColumnWidth(1, 90)
        self.local_file_tree.setColumnWidth(2, 110)
        self.local_file_tree.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.save_settings()

    def _select_local_explorer_path(self, path):
        """Select a local file/folder in the file explorer tree if it is visible."""
        if not hasattr(self, 'local_file_tree'):
            return
        target = Path(path).expanduser().resolve()
        def walk(parent):
            for index in range(parent.childCount()):
                item = parent.child(index)
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path and Path(item_path).expanduser().resolve() == target:
                    self.local_file_tree.setCurrentItem(item)
                    item.setSelected(True)
                    self.local_file_tree.scrollToItem(item)
                    return True
                if walk(item):
                    return True
            return False
        walk(self.local_file_tree.invisibleRootItem())

    def open_local_explorer_path(self):
        self.refresh_local_file_explorer(self.file_explorer_path.text().strip())

    def toggle_file_explorer_source(self):
        """Switch the same explorer tree between the PC and the connected Flipper."""
        if self.file_explorer_mode == "local":
            if not self._serial_ready():
                QMessageBox.information(self, "Flipper nicht verbunden", "Verbinde zuerst den Flipper über Werkzeuge → Flipper Zero verbinden.")
                return
            self.file_explorer_mode = "flipper"
            self.file_explorer_source_btn.setText("PC-Dateien anzeigen")
            self.file_explorer_path.setText(self.settings.get("recent_flipper_folder", "/ext"))
            self.statusBar().showMessage("Dateiexplorer zeigt jetzt das Flipper-Dateisystem – es werden keine Dateien übertragen.", 5000)
            self.refresh_flipper_file_explorer(self.file_explorer_path.text())
        else:
            self.file_explorer_mode = "local"
            self.file_explorer_source_btn.setText("Flipper im Explorer")
            self.file_explorer_path.setText(self.settings.get("recent_project_folder", str(self.working_directory())))
            self.refresh_local_file_explorer(self.file_explorer_path.text())

    def local_explorer_up(self):
        if self.file_explorer_mode == "flipper":
            current = self.file_explorer_path.text().strip().rstrip("/") or "/ext"
            if current not in ("/ext", "/int"):
                self.refresh_flipper_file_explorer(current.rsplit("/", 1)[0] or "/ext")
            return
        current = Path(self.file_explorer_path.text()).expanduser()
        parent = current.parent
        if parent != current:
            self.refresh_local_file_explorer(parent)

    def refresh_flipper_file_explorer(self, directory=None):
        """Render remote Flipper entries in the existing tree without downloading them."""
        if not self._serial_ready():
            QMessageBox.information(self, "Flipper nicht verbunden", "Verbinde zuerst den Flipper.")
            return
        target = str(directory or self.file_explorer_path.text().strip() or "/ext").replace("\\", "/").rstrip("/")
        if not (target == "/ext" or target.startswith("/ext/") or target == "/int" or target.startswith("/int/")) or ".." in target.split("/"):
            QMessageBox.warning(self, "Ungültiger Flipper-Pfad", "Verwende einen Pfad unter /ext oder /int.")
            return
        try:
            response = self._serial_command("storage list " + target, wait=0.25, timeout=3.0)
            entries = []
            seen = set()
            for raw in response.replace("\r", "\n").splitlines():
                line = raw.strip().strip("\x00")
                if not line or line.lower().startswith(("storage ", "error", "failed", "ok", "directory:", "path:", "listing files", "welcome", "firmware version", "usage:")) or line in (">", ">:"):
                    continue
                kind, name, size = "Datei", line, "—"
                m = re.match(r"^(DIR|DIRECTORY|FILE)\s*:?[ \t]+(.+?)\s*$", line, re.I)
                if m:
                    kind = "Ordner" if m.group(1).upper() in ("DIR", "DIRECTORY") else "Datei"
                    name = m.group(2)
                else:
                    m = re.match(r"^\[([dDfF])\]\s*(.+?)\s*$", line)
                    if m:
                        kind = "Ordner" if m.group(1).lower() == "d" else "Datei"
                        name = m.group(2)
                    elif line.endswith("/"):
                        kind, name = "Ordner", line.rstrip("/")
                    else:
                        m = re.match(r"^(.*?)(?:\s{2,}|\t+)(\d+)\s*(?:bytes?)?$", line, re.I)
                        if m:
                            name, size = m.group(1).strip(), m.group(2) + " B"
                name = re.sub(r"^(?:[├└│─|+`-]+\s*)+", "", name.strip().strip('"').strip("'"))
                if not name or name in (".", "..") or "/" in name or name in seen:
                    continue
                seen.add(name)
                entries.append((name, kind, size, target + "/" + name))
            self.file_explorer_path.setText(target)
            self.local_file_tree.clear()
            for name, kind, size, full in sorted(entries, key=lambda e: (e[1] != "Ordner", e[0].casefold())):
                item = QTreeWidgetItem([("📁 " if kind == "Ordner" else "📄 ") + name, kind, size if kind != "Ordner" else "—"] )
                item.setData(0, Qt.ItemDataRole.UserRole, full)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, "flipper_directory" if kind == "Ordner" else "flipper_file")
                if kind == "Ordner":
                    placeholder = QTreeWidgetItem(["Unterordner beim Aufklappen laden …", ""])
                    placeholder.setData(0, Qt.ItemDataRole.UserRole + 1, "placeholder")
                    item.addChild(placeholder)
                self.local_file_tree.addTopLevelItem(item)
            self.local_file_tree.sortItems(0, Qt.SortOrder.AscendingOrder)
            self.settings["recent_flipper_folder"] = target
            self.save_settings()
            self.statusBar().showMessage(f"Flipper {target} · {len(entries)} Einträge (nur Ansicht, keine Übertragung)", 5000)
        except Exception as exc:
            QMessageBox.warning(self, "Flipper-Dateiexplorer", f"Verzeichnis konnte nicht gelesen werden:\n{exc}")

    def _populate_flipper_explorer_children(self, item):
        if item.data(0, Qt.ItemDataRole.UserRole + 1) != "flipper_directory":
            return
        if item.childCount() != 1 or item.child(0).data(0, Qt.ItemDataRole.UserRole + 1) != "placeholder":
            return
        target = item.data(0, Qt.ItemDataRole.UserRole)
        # Populate children in place, so folders expand like a normal tree.
        try:
            response = self._serial_command("storage list " + target, wait=0.25, timeout=3.0)
            item.takeChildren()
            entries = []
            for raw in response.replace("\r", "\n").splitlines():
                line = raw.strip().strip("\x00")
                if not line or line.lower().startswith(("storage ", "error", "failed", "ok", "directory:", "path:", "listing files", "welcome", "firmware version", "usage:")) or line in (">", ">:"):
                    continue
                kind, name, size = "Datei", line, "—"
                m = re.match(r"^(DIR|DIRECTORY|FILE)\s*:?[ \t]+(.+?)\s*$", line, re.I)
                if m:
                    kind = "Ordner" if m.group(1).upper() in ("DIR", "DIRECTORY") else "Datei"
                    name = m.group(2)
                else:
                    m = re.match(r"^\[([dDfF])\]\s*(.+?)\s*$", line)
                    if m:
                        kind = "Ordner" if m.group(1).lower() == "d" else "Datei"
                        name = m.group(2)
                    elif line.endswith("/"):
                        kind, name = "Ordner", line.rstrip("/")
                    else:
                        m = re.match(r"^(.*?)(?:\s{2,}|\t+)(\d+)\s*(?:bytes?)?$", line, re.I)
                        if m:
                            name, size = m.group(1).strip(), m.group(2) + " B"
                name = re.sub(r"^(?:[├└│─|+`-]+\s*)+", "", name.strip().strip('"').strip("'"))
                if not name or name in (".", "..") or "/" in name:
                    continue
                full = target.rstrip("/") + "/" + name
                child = QTreeWidgetItem([("📁 " if kind == "Ordner" else "📄 ") + name, kind, size if kind != "Ordner" else "—"] )
                child.setData(0, Qt.ItemDataRole.UserRole, full)
                child.setData(0, Qt.ItemDataRole.UserRole + 1, "flipper_directory" if kind == "Ordner" else "flipper_file")
                if kind == "Ordner":
                    placeholder = QTreeWidgetItem(["Unterordner beim Aufklappen laden …", ""])
                    placeholder.setData(0, Qt.ItemDataRole.UserRole + 1, "placeholder")
                    child.addChild(placeholder)
                entries.append(child)
            for child in sorted(entries, key=lambda x: (x.data(0, Qt.ItemDataRole.UserRole + 1) != "flipper_directory", x.text(0).casefold())):
                item.addChild(child)
        except Exception as exc:
            item.takeChildren()
            item.addChild(QTreeWidgetItem([f"Lesefehler: {exc}", ""]))

    def choose_local_explorer_directory(self):
        if self.file_explorer_mode == "flipper":
            QMessageBox.information(self, "Flipper-Pfad", "Im Flipper-Modus kannst du den Pfad oben direkt eingeben, z. B. /ext oder /int, und Enter drücken.")
            return
        start = self.file_explorer_path.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Verzeichnis auswählen", start)
        if folder:
            self.refresh_local_file_explorer(folder)

    def local_explorer_item_clicked(self, item, _column=0):
        """Single-click files to preview source in the editor, like a lightweight VS Code preview."""
        if not item:
            return
        kind = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if self.file_explorer_mode == "flipper":
            if kind == "flipper_file":
                self._open_flipper_source_in_editor(item.data(0, Qt.ItemDataRole.UserRole))
        elif kind == "file":
            self._open_local_source_in_editor(item.data(0, Qt.ItemDataRole.UserRole))

    def _open_local_source_in_editor(self, raw):
        if not raw: return
        path = Path(raw)
        try:
            text = path.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            QMessageBox.information(self, "Datei öffnen", "Diese Datei ist keine lesbare UTF-8-Textdatei.")
            return
        except OSError as exc:
            QMessageBox.critical(self, "Datei öffnen fehlgeschlagen", str(exc)); return
        self.settings['last_directory'] = str(path.parent)
        self.set_language_mode(self.detect_language_mode(path, text), update_all=False)
        # Reuse an already open tab for the same local path instead of opening duplicates.
        for editor, doc in self.docs.items():
            if doc.path and doc.path.resolve() == path.resolve():
                self.tabs.setCurrentWidget(editor); return
        self.new_tab(text, str(path)); self.update_working_directory()

    def _open_flipper_source_in_editor(self, raw):
        if not raw: return
        try:
            response = self._serial_command("storage read " + raw, wait=0.25, timeout=4.0)
            lines = response.replace("\r", "").splitlines()
            cleaned = []
            for line in lines:
                stripped = line.strip()
                low = stripped.lower()
                if not stripped or stripped in ("storage read " + raw, ">:", ">"):
                    continue
                if low.startswith(("error", "failed", "unknown command", "storage read: error")):
                    raise RuntimeError(stripped)
                # Drop common serial CLI command echoes and prompts, not source lines.
                if low == ("storage read " + raw).lower() or low.startswith("welcome to flipper"):
                    continue
                cleaned.append(line)
            text = "\n".join(cleaned).rstrip("\n") + "\n"
            if "\x00" in text:
                raise ValueError("Die Datei scheint binär zu sein, nicht Quelltext.")
            if not cleaned:
                raise RuntimeError("Keine Dateiinhalte empfangen. Prüfe, ob die Firmware `storage read` über die CLI unterstützt.")
            for editor, doc in self.docs.items():
                if getattr(editor, "_flipper_source_path", None) == raw:
                    self.tabs.setCurrentWidget(editor); return
            self.set_language_mode(self.detect_language_mode(Path(raw).name, text), update_all=False)
            editor = self.new_tab(text)
            editor._flipper_source_path = raw
            index = self.tabs.indexOf(editor)
            self.tabs.setTabText(index, "📟 " + Path(raw).name)
            editor.setToolTip("Quelle auf dem Flipper: " + raw + "\nMit Speichern unter… lokal speichern; Änderungen werden nicht automatisch auf den Flipper übertragen.")
            self.statusBar().showMessage(f"Quelltext geöffnet: {raw} (Speichern unter… für lokale Kopie)", 5000)
        except Exception as exc:
            QMessageBox.warning(self, "Flipper-Datei öffnen", f"Konnte {raw} nicht als Quelltext öffnen:\n{exc}")

    def local_explorer_item_double_clicked(self, item, _column=0):
        # Qt's native tree behavior expands/collapses folders; files are previewed on single click.
        return

    def import_selected_as_project_folder(self):
        """Add selected local/Flipper folder to the appropriate recent-folder history."""
        if self.file_explorer_mode == "flipper":
            item = self.local_file_tree.currentItem()
            raw = item.data(0, Qt.ItemDataRole.UserRole) if item else self.file_explorer_path.text().strip()
            if item and item.data(0, Qt.ItemDataRole.UserRole + 1) == "flipper_file":
                raw = str(raw).rsplit("/", 1)[0]
            if not raw:
                raw = "/ext"
            self.settings["recent_flipper_folder"] = str(raw)
            recent = self.settings.get("recent_flipper_folders", [])
            if not isinstance(recent, list):
                recent = []
            recent = [str(raw)] + [x for x in recent if x != str(raw)]
            self.settings["recent_flipper_folders"] = recent[:20]
            self.save_settings()
            self.statusBar().showMessage(f"Flipper-Verzeichnis gemerkt: {raw}", 5000)
            return
        item = self.local_file_tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Projektordner übernehmen", "Wähle zuerst einen Ordner oder eine Datei im Dateiexplorer aus.")
            return
        raw = item.data(0, Qt.ItemDataRole.UserRole)
        if not raw:
            return
        selected_path = Path(raw).expanduser()
        folder = selected_path if selected_path.is_dir() else selected_path.parent
        if not folder.is_dir():
            QMessageBox.warning(self, "Projektordner übernehmen", f"Der Ordner existiert nicht mehr:\n{folder}")
            return
        # This is an import into the project-folder history, not a copy of files.
        self.refresh_local_file_explorer(folder)
        self._update_recent_project_folders(folder, refresh_combo=True)
        self.statusBar().showMessage(f"Projektordner übernommen: {folder}", 5000)

    def local_explorer_context_menu(self, pos):
        item = self.local_file_tree.itemAt(pos)
        if item is not None:
            self.local_file_tree.setCurrentItem(item)
        menu = QMenu(self.local_file_tree)
        refresh_action = menu.addAction("Aktualisieren")
        open_action = menu.addAction("Öffnen") if item else None
        project_action = menu.addAction("Als Projektordner übernehmen") if item else None
        chosen = menu.exec(self.local_file_tree.viewport().mapToGlobal(pos))
        if chosen == refresh_action:
            self.refresh_local_file_explorer()
        elif item and chosen == open_action:
            self.local_explorer_item_double_clicked(item, 0)
        elif item and chosen == project_action:
            self.import_selected_as_project_folder()

    def toggle_mcp_panel(self, checked=None):
        expanded = (not self.ollama_dock.isVisible()) if checked is None else bool(checked)
        self.ollama_dock.setVisible(expanded)
        self.settings['ollama_panel_collapsed'] = not expanded
        self.save_settings()
        if expanded and self.ollama_model.count() == 0:
            self.load_ollama_models()

    def reset_dock_layout(self):
        # Restore a practical default layout; all docks remain movable and floatable.
        for dock in (self.palette_dock, self.file_explorer_dock, self.flipper_file_explorer_dock):
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ollama_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.output_dock)
        self.splitDockWidget(self.file_explorer_dock, self.flipper_file_explorer_dock, Qt.Orientation.Horizontal)
        self.palette_dock.show()
        self.output_dock.show()
        self.flipper_file_explorer_dock.hide()

    def _ollama_api_url(self):
        return self.ollama_url.text().strip().rstrip('/')

    def load_ollama_models(self):
        base = self._ollama_api_url()
        self.settings['ollama_url'] = base
        self.ollama_refresh.setEnabled(False)
        self.mcp_status.setText('Verbinde mit Ollama und lade lokale Modelle …')
        class ModelWorker(QThread):
            result = pyqtSignal(list, str)
            def __init__(self, url): super().__init__(); self.url=url
            def run(self):
                try:
                    req=urllib.request.Request(self.url + '/api/tags')
                    with urllib.request.urlopen(req, timeout=8) as resp: data=json.loads(resp.read().decode('utf-8'))
                    self.result.emit([m.get('name','') for m in data.get('models',[]) if m.get('name')], '')
                except Exception as ex: self.result.emit([], str(ex))
        self._ollama_model_worker = ModelWorker(base)
        def done(models, error):
            self.ollama_refresh.setEnabled(True)
            if error:
                self.mcp_status.setText('Ollama nicht erreichbar: ' + error + ' · Läuft Ollama?')
                return
            previous=self.ollama_model.currentText().strip() or self.settings.get('ollama_model','')
            self.ollama_model.clear(); self.ollama_model.addItems(models)
            if previous:
                self.ollama_model.setCurrentText(previous)
            elif models:
                self.ollama_model.setCurrentIndex(0)
            self.mcp_status.setText(f'Ollama verbunden · {len(models)} Modell(e) gefunden' if models else 'Ollama erreichbar, aber keine Modelle installiert. Nutze z. B. „ollama pull qwen2.5-coder:7b“.')
            self.save_settings()
        self._ollama_model_worker.result.connect(done)
        self._ollama_model_worker.start()

    def ask_ollama(self):
        prompt=self.ollama_prompt.toPlainText().strip()
        model=self.ollama_model.currentText().strip()
        if not prompt:
            QMessageBox.information(self, 'Lokale KI', 'Bitte gib zuerst eine Frage oder Aufgabe ein.')
            return
        if not model:
            QMessageBox.information(self, 'Lokale KI', 'Bitte lade die Modelle und wähle ein installiertes Ollama-Modell aus.')
            return
        editor=self.current_editor()
        context=editor.toPlainText() if editor and self.ollama_include.isChecked() else ''
        self.settings['ollama_url']=self._ollama_api_url(); self.settings['ollama_model']=model; self.save_settings()
        self.ollama_send.setEnabled(False); self.mcp_status.setText(f'Frage an {model} wird verarbeitet …')
        self._ollama_chat_worker=OllamaWorker(self._ollama_api_url(),model,prompt,context)
        self._ollama_chat_worker.finished_text.connect(self._ollama_response_ready)
        self._ollama_chat_worker.start()

    def _ollama_response_ready(self, answer, error):
        self.ollama_send.setEnabled(True)
        if error:
            self.mcp_status.setText('Ollama-Fehler: ' + error)
            return
        self.ollama_answer.setPlainText(answer)
        self.mcp_status.setText('Antwort von Ollama erhalten. Du kannst sie prüfen und in den Editor übernehmen.')

    def _clean_ollama_code(self):
        text=self.ollama_answer.toPlainText().strip()
        match=re.search(r'```(?:javascript|js|mjs|duckyscript|text)?\s*\n(.*?)```',text,re.S|re.I)
        return match.group(1).strip() if match else text

    def insert_ollama_answer(self):
        editor=self.current_editor()
        if not editor:
            QMessageBox.information(self,'Lokale KI','Kein Editor geöffnet.'); return
        cursor=editor.textCursor(); cursor.insertText(self._clean_ollama_code()); editor.setTextCursor(cursor); editor.setFocus()

    def replace_with_ollama_answer(self):
        editor=self.current_editor()
        if not editor:
            QMessageBox.information(self,'Lokale KI','Kein Editor geöffnet.'); return
        answer=self._clean_ollama_code()
        if QMessageBox.question(self,'Editorinhalt ersetzen','Soll der gesamte aktuelle Editorinhalt durch die KI-Antwort ersetzt werden?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        editor.setPlainText(answer); editor.setFocus()

    def show_mcp_info(self):
        QMessageBox.information(self, 'Lokale KI mit Ollama',
            'Diese Funktion spricht direkt mit deiner lokalen Ollama-HTTP-API unter http://localhost:11434. Es wird kein MCP-Server und kein Cloud-API-Schlüssel verwendet.\n\n'
            '1. Ollama installieren und starten.\n2. Ein Modell laden, z. B. ollama pull qwen2.5-coder:7b.\n3. Auf „Modelle laden“ klicken, ein Modell auswählen und eine Frage stellen.\n\n'
            'Der aktuelle Editorinhalt wird nur mitgesendet, wenn „Editorinhalt mitsenden“ aktiviert ist.')

    def toggle_palette(self, checked=None):
        expanded = self.palette_toggle.isChecked() if checked is None else bool(checked)
        self.palette.setVisible(expanded)
        self.palette_search.setVisible(expanded)
        self.palette_toggle.setText('▼ Befehle' if expanded else '▶ Befehle')
        self.settings['palette_collapsed'] = not expanded
        self.save_settings()
    def _populate_palette(self):
        self.palette.clear()
        if self.language_mode == 'javascript':
            root = QTreeWidgetItem(['mJS-Module (require)'])
            self.palette.addTopLevelItem(root)
            for name, desc in sorted(JS_MODULES.items()):
                item = QTreeWidgetItem([name])
                item.setToolTip(0, desc)
                item.setData(0, Qt.ItemDataRole.UserRole, f'let {name} = require("{name}");')
                root.addChild(item)
            root.setExpanded(True)
            globals_root = QTreeWidgetItem(['JavaScript-Grundlagen'])
            self.palette.addTopLevelItem(globals_root)
            for name, desc in sorted(JS_GLOBALS.items()):
                item = QTreeWidgetItem([name]); item.setToolTip(0, desc)
                item.setData(0, Qt.ItemDataRole.UserRole, name)
                globals_root.addChild(item)
            globals_root.setExpanded(False)
            return
        for group,commands in GROUPS.items():
            root=QTreeWidgetItem([group])
            self.palette.addTopLevelItem(root)
            for c in commands:
                item=QTreeWidgetItem([c])
                item.setToolTip(0,COMMANDS[c])
                item.setData(0,Qt.ItemDataRole.UserRole,c)
                root.addChild(item)
            root.setExpanded(True)
        for c in sorted(KEYS-set(COMMANDS)):
            root=QTreeWidgetItem(["Einzeltasten"])
            root.setData(0,Qt.ItemDataRole.UserRole,None)
            # Group single keys once, below dedicated group
            break
        single=QTreeWidgetItem(["Einzeltasten"])
        self.palette.addTopLevelItem(single)
        for c in sorted(KEYS-set(COMMANDS)):
            item=QTreeWidgetItem([c])
            item.setData(0,Qt.ItemDataRole.UserRole,c)
            single.addChild(item)
        single.setExpanded(False)
    def filter_palette(self,text):
        q=text.strip().lower()
        for i in range(self.palette.topLevelItemCount()):
            group=self.palette.topLevelItem(i)
            visible=not q
            for j in range(group.childCount()):
                child=group.child(j)
                show=q in child.text(0).lower() or q in child.toolTip(0).lower()
                child.setHidden(not show)
                visible |= show
            group.setHidden(not visible)
            group.setExpanded(bool(q))
    def _build_menus(self):
        bar=self.menuBar()
        filem=bar.addMenu("Datei")
        self.action("Neu",self.new_tab,filem,"Ctrl+N")
        self.action("Öffnen…",self.open_file,filem,"Ctrl+O")
        self.action("Speichern",self.save_file,filem,"Ctrl+S")
        self.action("Speichern unter…",self.save_as,filem,"Ctrl+Shift+S")
        filem.addSeparator()
        self.action("Beenden",self.close,filem,"Alt+F4")
        edit=bar.addMenu("Bearbeiten"); self.action("Rückgängig",lambda:self.editor_action('undo'),edit,"Ctrl+Z"); self.action("Wiederholen",lambda:self.editor_action('redo'),edit,"Ctrl+Y"); edit.addSeparator(); self.action("Suchen…",self.find_text,edit,"Ctrl+F"); self.action("Zeile duplizieren",self.duplicate_line,edit,"Ctrl+D"); self.action("Kommentar umschalten",self.toggle_comment,edit,"Ctrl+/")
        payload=bar.addMenu("Payload")
        self.action("Payload prüfen",self.check_payload,payload,"F7")
        self.action("Vorschau",self.preview,payload,"Ctrl+Alt+P")
        self.action("Alle kopieren",self.copy_all,payload,"Ctrl+Shift+C")
        examples=payload.addMenu("Beispiele laden")
        for name in EXAMPLES: self.action(name,lambda checked=False,n=name:self.load_example(n),examples)
        self.extensions_menu=bar.addMenu("Erweiterungen")
        self.action("Plugin-Verwaltung / Marktplatz…",self.show_plugin_manager,self.extensions_menu,"Ctrl+Shift+X")
        self.action("Python-Add-on laden…",self.load_addon,self.extensions_menu)
        self.action("Add-on-Ordner öffnen",self.open_addon_folder,self.extensions_menu)
        tools=bar.addMenu("Werkzeuge")
        self.action("Flipper Zero verbinden…",self.connect_flipper,tools)
        self.action("Flipper-Konsole…",self.show_flipper_console,tools)
        self.action("Aktuellen Payload auf Flipper speichern…",self.save_to_flipper,tools)
        self.action("Flipper trennen",self.disconnect_flipper,tools)
        tools.addSeparator()
        self.action("JavaScript-Modus umschalten",self.toggle_language_mode,tools,"F6")
        self.action("JavaScript prüfen",self.check_javascript,tools,"Shift+F7")
        self.action("JavaScript formatieren",self.format_javascript,tools,"Ctrl+Alt+F")
        view=bar.addMenu("Ansicht")
        themes=view.addMenu("Theme")
        for name in THEMES: self.action(name,lambda checked=False,n=name:self.change_theme(n),themes)
        self.action("Befehle ein-/ausblenden",lambda:self.palette_dock.setVisible(not self.palette_dock.isVisible()),view,"Ctrl+B")
        self.action("PC-Dateiexplorer ein-/ausblenden",lambda:self.file_explorer_dock.setVisible(not self.file_explorer_dock.isVisible()),view,"Ctrl+Shift+E")
        self.action("Flipper-Dateiexplorer ein-/ausblenden",lambda:self.flipper_file_explorer_dock.setVisible(not self.flipper_file_explorer_dock.isVisible()),view,"Ctrl+Shift+F")
        self.action("Einstellungen…",self.show_settings,view)
        self.action("Ollama ein-/ausblenden",lambda:self.ollama_dock.setVisible(not self.ollama_dock.isVisible()),view,"Ctrl+Alt+M")
        self.action("Output ein-/ausblenden",lambda:self.output_dock.setVisible(not self.output_dock.isVisible()),view,"Ctrl+Shift+O")
        view.addSeparator()
        self.action("Fensteranordnung zurücksetzen",self.reset_dock_layout,view)
        self.action("Autovervollständigung anzeigen",lambda:self.current_editor() and self.current_editor().show_suggestions(True),view,"Ctrl+Space")
        helpm=bar.addMenu("Hilfe")
        self.action("Befehlsreferenz",self.show_js_sandbox,helpm)
        self.action("Über",self.about,helpm)
        self.action("Befehlspalette öffnen…", self.show_command_palette, bar, "Ctrl+Shift+P")
    def _collect_command_actions(self):
        """Collect executable menu actions for a VS-Code-style command palette."""
        commands = []
        def walk(menu, prefix=""):
            for act in menu.actions():
                sub = act.menu()
                if sub:
                    walk(sub, f"{prefix}{act.text().replace('&', '')} › ")
                elif act.isEnabled() and act.text().strip():
                    label = act.text().replace("&", "").replace("…", "...").strip()
                    if label and label != "Befehlspalette öffnen...":
                        commands.append((f"{prefix}{label}", act))
        for menu in self.menuBar().findChildren(QMenu):
            # Only process top-level menus; recursive traversal handles children.
            if menu.parent() is self.menuBar():
                walk(menu)
        # Also add common editor commands not represented by menu actions yet.
        extra = [
            ("Editor: Neue Datei", self.new_tab),
            ("Editor: Aktuelle Datei speichern", self.save_file),
            ("Editor: Suchen", self.find_text),
            ("Editor: Zeile duplizieren", self.duplicate_line),
            ("Editor: Kommentar umschalten", self.toggle_comment),
            ("Payload: Prüfen", self.check_payload),
            ("Payload: Vorschau anzeigen", self.preview),
            ("JavaScript: Formatieren", self.format_javascript),
            ("Ansicht: Befehle ein-/ausblenden", lambda: self.palette_dock.setVisible(not self.palette_dock.isVisible())),
            ("Ansicht: Ollama ein-/ausblenden", lambda: self.ollama_dock.setVisible(not self.ollama_dock.isVisible())),
            ("Ansicht: Output ein-/ausblenden", lambda: self.output_dock.setVisible(not self.output_dock.isVisible())),
            ("Ansicht: PC-Dateiexplorer ein-/ausblenden", lambda: self.file_explorer_dock.setVisible(not self.file_explorer_dock.isVisible())),
            ("Ansicht: Flipper-Dateiexplorer ein-/ausblenden", lambda: self.flipper_file_explorer_dock.setVisible(not self.flipper_file_explorer_dock.isVisible())),
            ("Ansicht: Fensteranordnung zurücksetzen", self.reset_dock_layout),
            ("Einstellungen öffnen", self.show_settings),
        ]
        known = {name.lower() for name, _ in commands}
        for name, callback in extra:
            if name.lower() not in known:
                commands.append((name, callback))
        return sorted(commands, key=lambda item: item[0].casefold())

    def show_command_palette(self):
        """Open a searchable command picker inspired by VS Code's Ctrl+Shift+P."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Befehlspalette")
        dialog.setMinimumSize(650, 460)
        dialog.resize(760, 540)
        layout = QVBoxLayout(dialog)
        search = QLineEdit(dialog)
        search.setPlaceholderText("Befehl eingeben, z. B. 'speichern', 'Ollama', 'Payload prüfen' …")
        search.setClearButtonEnabled(True)
        layout.addWidget(search)
        listing = QListWidget(dialog)
        listing.setUniformItemSizes(True)
        layout.addWidget(listing, 1)
        commands = self._collect_command_actions()
        def populate(query=""):
            query = query.strip().casefold()
            listing.clear()
            for label, target in commands:
                if query in label.casefold():
                    item = QListWidgetItem(label)
                    item.setData(Qt.ItemDataRole.UserRole, target)
                    listing.addItem(item)
            if listing.count():
                listing.setCurrentRow(0)
        def execute_current():
            item = listing.currentItem()
            if item is None:
                return
            target = item.data(Qt.ItemDataRole.UserRole)
            dialog.accept()
            if isinstance(target, QAction):
                target.trigger()
            else:
                target()
        search.textChanged.connect(populate)
        search.returnPressed.connect(execute_current)
        listing.itemActivated.connect(lambda _item: execute_current())
        listing.itemDoubleClicked.connect(lambda _item: execute_current())
        populate()
        search.setFocus()
        dialog.exec()

    def action(self,label,callback,menu,shortcut=None):
        a=QAction(label,self); a.triggered.connect(lambda _checked=False, cb=callback: cb())
        if shortcut: a.setShortcut(QKeySequence(shortcut))
        menu.addAction(a)
        return a
    def current_doc(self): return self.docs.get(self.tabs.currentWidget())
    def on_current_tab_changed(self, *_):
        editor = self.current_editor()
        if editor:
            self.language_mode = getattr(editor, "language_mode", self.language_mode)
            if hasattr(self, 'palette'):
                self._populate_palette()
                self.filter_palette(self.palette_search.text())
        self.update_status()
        self.update_working_directory()
    def current_editor(self):
        d=self.current_doc()
        return d.editor if d else None
    def detect_language_mode(self, path=None, content=""):
        """Infer the editor/reference mode from a filename or recognizable script syntax."""
        suffix = Path(path).suffix.lower() if path else ""
        if suffix in (".js", ".mjs", ".javascript"):
            return "javascript"
        if suffix in (".txt", ".payload", ".ducky", ".dd"):
            return "badusb"
        text = content.lstrip("\ufeff\n\r ")
        if re.search(r'(^|\n)\s*(?:let|const|var)\s+\w+\s*=\s*require\s*\(|(^|\n)\s*(?:function\s+\w+|import\s+.*from\s+)', text):
            return "javascript"
        if re.search(r'(^|\n)\s*(?:DELAY|STRINGLN?|ALTSTRING|GUI|CTRL|REM|ID)\b', text, re.I):
            return "badusb"
        return self.language_mode
    def set_language_mode(self, mode, update_all=False):
        if mode not in ("badusb", "javascript"):
            return
        self.language_mode = mode
        if update_all:
            for editor in self.docs:
                editor.set_language_mode(mode)
                editor.completer.popup().hide()
        else:
            editor = self.current_editor()
            if editor:
                editor.set_language_mode(mode)
                editor.completer.popup().hide()
        self._populate_palette()
        if hasattr(self, 'palette_search'):
            self.filter_palette(self.palette_search.text())
        self.statusBar().showMessage("Editor-Modus: " + ("Flipper mJS / JavaScript" if mode == "javascript" else "BadUSB Payload"))
        self.update_working_directory()
    def new_tab(self,content="",path=None):
        if path:
            self.set_language_mode(self.detect_language_mode(path, content), update_all=False)
        editor=CodeEditor(lambda:self.theme); editor.setFont(QFont("Consolas",int(self.settings.get('font_size',11)))); editor._suggestions_enabled=bool(self.settings.get('autocomplete',True)); editor.set_language_mode(self.language_mode); editor.setPlainText(content); editor.textChanged.connect(lambda e=editor:self.on_edit(e)); editor.cursorPositionChanged.connect(lambda e=editor:e.show_suggestions())
        doc=Document(editor,Path(path) if path else None,False)
        self.docs[editor]=doc
        title=doc.path.name if doc.path else "Unbenannt"
        idx=self.tabs.addTab(editor,title)
        self.tabs.setCurrentIndex(idx)
        self.update_status()
        if doc.path: self.set_tab_dirty(editor,False)
        return editor
    def set_tab_dirty(self,editor,dirty):
        doc=self.docs.get(editor)
        if not doc:return
        doc.dirty=dirty
        name=doc.path.name if doc.path else "Unbenannt"
        i=self.tabs.indexOf(editor)
        self.tabs.setTabText(i,("● " if dirty else "")+name)
    def on_edit(self,editor):
        self.set_tab_dirty(editor,True)
        self.update_status()
        if self.settings.get('live_check', True):
            QTimer.singleShot(120,self.live_check)
    def live_check(self):
        e=self.current_editor()
        if e:
            if self.language_mode == 'javascript':
                self.check_javascript()
            else:
                bad,msg=validate_lines(e.toPlainText()); self.statusBar().showMessage((f"{len(bad)} mögliche Fehler" if bad else "Syntaxprüfung: keine offensichtlichen Fehler")+f" · {estimate_runtime_ms(e.toPlainText())/1000:.1f} s geschätzte Laufzeit")
    def update_status(self,*_):
        e=self.current_editor()
        if e:
            c=e.textCursor(); self.statusBar().showMessage(f"Zeile {c.blockNumber()+1}, Spalte {c.positionInBlock()+1} · {len(e.toPlainText().splitlines())} Zeilen · {estimate_runtime_ms(e.toPlainText())/1000:.1f} s")
    def apply_theme(self):
        t=self.theme; self.setStyleSheet(f"""
        QMainWindow,QWidget {{ background:{t['bg']}; color:{t['fg']}; }}
        QMenuBar {{ background:{t['panel']}; color:{t['fg']}; padding:4px; }} QMenuBar::item {{ padding:6px 10px; background:transparent; }} QMenuBar::item:selected {{ background:{t['hover']}; color:{t['accent']}; }}
        QMenu {{ background:{t['panel']}; color:{t['fg']}; border:1px solid {t['hover']}; }} QMenu::item {{ padding:6px 28px 6px 24px; }} QMenu::item:selected {{ background:{t['hover']}; color:{t['accent']}; }}
        QToolBar,QTabWidget::pane,QStatusBar {{ background:{t['panel']}; border:0; }} QToolBar {{ spacing:5px; padding:5px; }}
        QPushButton,QToolButton {{ background:{t['btn']}; color:{t['fg']}; border:1px solid {t['hover']}; border-radius:4px; padding:5px 9px; }} QPushButton:hover,QToolButton:hover {{ background:{t['hover']}; }}
        QLineEdit,QComboBox,QSpinBox,QPlainTextEdit,QTextEdit,QTreeWidget {{ background:{t['editor']}; color:{t['fg']}; border:1px solid {t['hover']}; selection-background-color:{t['accent']}; selection-color:{t['bg']}; padding:3px; }}
        QTabBar::tab {{ background:{t['panel']}; color:{t['muted']}; padding:8px 13px; border:1px solid {t['bg']}; }} QTabBar::tab:selected {{ background:{t['editor']}; color:{t['accent']}; border-bottom:2px solid {t['accent']}; }} QTabBar::tab:hover {{ background:{t['hover']}; }}
        QTreeWidget::item {{ padding:3px; }} QTreeWidget::item:selected {{ background:{t['hover']}; color:{t['accent']}; }} QHeaderView::section {{ background:{t['panel']}; color:{t['fg']}; }} QScrollBar:vertical {{ background:{t['panel']}; width:12px; }} QScrollBar::handle:vertical {{ background:{t['hover']}; min-height:20px; }}
        """)
        for editor in self.docs: editor.set_theme()
        self.output.setStyleSheet(f"background:{t['editor']};color:{t['fg']};")
    def change_theme(self,name):
        if name not in THEMES:return
        self.theme_name=name
        self.theme=THEMES[name].copy()
        self.apply_theme()
        self.save_settings()
        if self.theme_combo.currentText()!=name: self.theme_combo.blockSignals(True); self.theme_combo.setCurrentText(name); self.theme_combo.blockSignals(False)
    def insert_palette_item(self,item,_col=0):
        cmd=item.data(0,Qt.ItemDataRole.UserRole)
        if not cmd:return
        e=self.current_editor()
        if not e:return
        cur=e.textCursor()
        text = cmd if (self.language_mode == 'javascript' and cmd.rstrip().endswith(';')) else cmd + (" " if cmd not in STANDALONE and cmd not in {"WAIT_FOR_BUTTON_PRESS"} else "")
        cur.insertText(text)
        e.setTextCursor(cur)
        e.setFocus()
    def close_tab(self,index):
        editor=self.tabs.widget(index)
        doc=self.docs.get(editor)
        if doc and doc.dirty:
            ans=QMessageBox.question(self,"Ungespeicherte Änderungen",f"{self.tabs.tabText(index).lstrip('● ')} speichern?",QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
            if ans==QMessageBox.StandardButton.Cancel:return
            if ans==QMessageBox.StandardButton.Save:
                self.tabs.setCurrentIndex(index)
                if not self.save_file():return
        self.tabs.removeTab(index)
        self.docs.pop(editor,None)
        editor.deleteLater()
        if self.tabs.count()==0:self.new_tab()
    def tab_context_menu(self,pos):
        index=self.tabs.tabBar().tabAt(pos)
        if index<0:return
        menu=QMenu(self)
        close=menu.addAction("Tab schließen")
        others=menu.addAction("Andere Tabs schließen")
        all_=menu.addAction("Alle Tabs schließen")
        chosen=menu.exec(self.tabs.tabBar().mapToGlobal(pos))
        if chosen==close:self.close_tab(index)
        elif chosen==others:
            for i in reversed(range(self.tabs.count())):
                if i!=index:self.close_tab(i)
        elif chosen==all_:
            for i in reversed(range(self.tabs.count())): self.close_tab(i)
    def open_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Payload öffnen",str(self.working_directory()),"BadUSB / JavaScript / Text (*.txt *.payload *.ducky *.dd *.js *.mjs);;Alle Dateien (*)")
        if not path:return
        try: text=Path(path).read_text(encoding='utf-8-sig')
        except Exception as ex: QMessageBox.critical(self,"Öffnen fehlgeschlagen",str(ex)); return
        self.settings['last_directory'] = str(Path(path).parent)
        self.set_language_mode(self.detect_language_mode(path, text), update_all=False)
        self.new_tab(text,path)
        self.update_working_directory()
    def save_file(self):
        d=self.current_doc()
        if not d:return False
        if not d.path:return self.save_as()
        try: d.path.write_text(d.editor.toPlainText(),encoding='utf-8',newline='\n'); self.settings['last_directory']=str(d.path.parent); self.save_settings(); self.set_tab_dirty(d.editor,False); self.statusBar().showMessage(f"Gespeichert: {d.path}"); self.update_working_directory(); return True
        except OSError as ex: QMessageBox.critical(self,"Speichern fehlgeschlagen",str(ex)); return False
    def save_as(self):
        d=self.current_doc()
        if not d:return False
        default_name = d.path if d.path else (self.working_directory() / ("payload" + self.settings.get('default_extension', '.txt')))
        path,_=QFileDialog.getSaveFileName(self,"Payload speichern unter",str(default_name),"BadUSB / JavaScript / Text (*.txt *.payload *.ducky *.js *.mjs);;Alle Dateien (*)")
        if not path:return False
        d.path=Path(path)
        self.settings['last_directory'] = str(d.path.parent)
        return self.save_file()
    def load_example(self,name): self.new_tab(EXAMPLES[name])
    def check_payload(self):
        if self.language_mode == 'javascript':
            return self.check_javascript()
        e=self.current_editor()
        if not e:return
        bad,msg=validate_lines(e.toPlainText())
        self.output.clear()
        if msg: self.output.setPlainText("\n".join(msg))
        else:self.output.setPlainText("Keine offensichtlichen Syntaxfehler gefunden. Firmwareabhängige Befehle bitte am Zielgerät testen.")
        self.statusBar().showMessage(f"Prüfung abgeschlossen: {len(bad)} mögliche Fehler")
        if bad:
            selections=[]
            for n in bad:
                block=e.document().findBlockByNumber(n-1)
                if block.isValid():
                    from PyQt6.QtWidgets import QTextEdit
                    sel=QTextEdit.ExtraSelection()
                    sel.format.setBackground(QColor(self.theme['error']))
                    sel.cursor= e.textCursor()
                    sel.cursor.setPosition(block.position())
                    sel.cursor.movePosition(sel.cursor.MoveOperation.EndOfBlock,sel.cursor.MoveMode.KeepAnchor)
                    selections.append(sel)
            e.setExtraSelections(selections)
        else:e.highlight_current_line()
    def preview(self):
        e=self.current_editor()
        if not e:return
        text=e.toPlainText()
        bad,msg=validate_lines(text)
        runtime=estimate_runtime_ms(text)
        dlg=QDialog(self)
        dlg.setWindowTitle("Payload-Vorschau")
        dlg.resize(650,500)
        lay=QVBoxLayout(dlg)
        lay.addWidget(QLabel(f"{len(text.splitlines())} Zeilen · ca. {runtime/1000:.1f} Sekunden · {len(bad)} mögliche Fehler"))
        view=QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlainText(text)
        lay.addWidget(view)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        lay.addWidget(buttons)
        dlg.exec()
    def copy_all(self):
        e=self.current_editor()
        if e: QApplication.clipboard().setText(e.toPlainText()); self.statusBar().showMessage("Payload in Zwischenablage kopiert")
    def editor_action(self,action):
        e=self.current_editor()
        if e:getattr(e,action)()
    def find_text(self):
        e=self.current_editor()
        if not e:return
        text,ok=QInputDialog.getText(self,"Suchen","Suchtext:")
        if not ok or not text:return
        if not e.find(text):
            cur=e.textCursor()
            cur.movePosition(cur.MoveOperation.Start)
            e.setTextCursor(cur)
            if not e.find(text): QMessageBox.information(self,"Suchen","Text nicht gefunden.")
    def duplicate_line(self):
        e=self.current_editor()
        if not e:return
        cur=e.textCursor()
        cur.beginEditBlock()
        cur.movePosition(cur.MoveOperation.StartOfBlock)
        cur.select(cur.SelectionType.LineUnderCursor)
        line=cur.selectedText()
        cur.movePosition(cur.MoveOperation.EndOfBlock)
        cur.insertText("\n"+line)
        cur.endEditBlock()
    def toggle_comment(self):
        e=self.current_editor()
        if not e:return
        cur=e.textCursor()
        cur.beginEditBlock()
        cur.movePosition(cur.MoveOperation.StartOfBlock)
        start=cur.blockNumber()
        cur.movePosition(cur.MoveOperation.EndOfBlock,cur.MoveMode.KeepAnchor)
        lines=cur.selectedText().split('\u2029')
        uncomment=all(not x.strip() or x.lstrip().startswith('REM ') for x in lines)
        result=[]
        for line in lines:
            if not line.strip(): result.append(line)
            elif uncomment: result.append(re.sub(r'^(\s*)REM\s?','\\1',line,flags=re.I))
            else: result.append(re.match(r'^\s*',line).group()+"REM "+line.lstrip())
        cur.insertText('\n'.join(result))
        cur.endEditBlock()
    def addon_directory(self):
        d=Path.home()/".badusb_ide_addons"
        d.mkdir(parents=True,exist_ok=True)
        return d

    def marketplace_directory(self):
        d=self.addon_directory()/"marketplace"
        d.mkdir(parents=True,exist_ok=True)
        return d

    def _plugin_files(self):
        root=self.addon_directory()
        return sorted((p for p in root.rglob("*.py") if not any(x.startswith(".") or x in {"__pycache__", ".git"} for x in p.relative_to(root).parts) and not p.name.startswith("_") and p.name != "setup.py"), key=lambda p:str(p).lower())

    def _plugin_key(self,path):
        return str(Path(path).resolve())

    def _load_enabled_addons(self):
        for path in self.settings.get("enabled_addons", []):
            try:
                if Path(path).is_file(): self._activate_addon(Path(path), show_errors=False)
            except Exception: pass

    def _activate_addon(self,path,show_errors=True):
        path=Path(path).resolve(); key=self._plugin_key(path)
        if key in self.addon_records: return True
        spec=importlib.util.spec_from_file_location("badusb_addon_"+re.sub(r"\W","_",path.stem)+"_"+str(abs(hash(key))),path)
        if not spec or not spec.loader: raise RuntimeError("Python-Modul konnte nicht geladen werden.")
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        register=getattr(module,"register",None)
        if not callable(register): raise ValueError("Plugin benötigt eine register(ide)-Funktion.")
        old_actions=set(self.addon_actions); old_docks=set(self.addon_docks)
        register(self)
        actions=[x for x in self.addon_actions if x not in old_actions]
        docks=[x for x in self.addon_docks if x not in old_docks]
        name=getattr(module,"ADDON_NAME",path.stem)
        self.addon_records[key]={"path":path,"module":module,"actions":actions,"docks":docks,"name":name}
        if module not in self.addon_modules: self.addon_modules.append(module)
        enabled=self.settings.setdefault("enabled_addons",[])
        if key not in enabled: enabled.append(key)
        self.save_settings(); self.statusBar().showMessage("Plugin aktiviert: "+name)
        return True

    def _deactivate_addon(self,path):
        key=self._plugin_key(path); rec=self.addon_records.get(key)
        if not rec: return
        module=rec["module"]
        cleanup=getattr(module,"unregister",None)
        if callable(cleanup):
            try: cleanup(self)
            except Exception as ex: QMessageBox.warning(self,"Plugin-Aufräumen",str(ex))
        for act in rec["actions"]:
            try:
                parent=act.parent()
                if isinstance(parent,QMenu): parent.removeAction(act)
                if hasattr(self,"main_toolbar"): self.main_toolbar.removeAction(act)
                act.setEnabled(False); act.deleteLater()
            except Exception: pass
            if act in self.addon_actions: self.addon_actions.remove(act)
        for dock in rec["docks"]:
            try: self.removeDockWidget(dock); dock.close(); dock.deleteLater()
            except Exception: pass
            if dock in self.addon_docks: self.addon_docks.remove(dock)
        self.addon_records.pop(key,None)
        self.addon_modules=[m for m in self.addon_modules if m is not module]
        self.settings["enabled_addons"]=[x for x in self.settings.get("enabled_addons",[]) if self._plugin_key(x)!=key]
        self.save_settings(); self.statusBar().showMessage("Plugin deaktiviert: "+rec["name"])

    def open_addon_folder(self):
        path=self.addon_directory()
        try:
            if sys.platform.startswith("win"): os.startfile(str(path))
            elif sys.platform=="darwin": subprocess.Popen(["open",str(path)])
            else: subprocess.Popen(["xdg-open",str(path)])
        except Exception as ex: QMessageBox.warning(self,"Add-on-Ordner",str(path)+"\n"+str(ex))

    def register_menu(self,name,parent="Erweiterungen"):
        parent_menu=self.extensions_menu if parent in (None,"Erweiterungen") else None
        if parent_menu is None:
            for a in self.extensions_menu.actions():
                if a.menu() and a.text()==parent: parent_menu=a.menu(); break
        if parent_menu is None: parent_menu=self.extensions_menu
        return parent_menu.addMenu(name)

    def register_menu_action(self,label,callback,menu="Erweiterungen",accelerator=None):
        target=self.extensions_menu
        for a in self.extensions_menu.actions():
            if a.menu() and a.text()==menu: target=a.menu(); break
        act=QAction(label,self); act.triggered.connect(lambda _=False,cb=callback:cb())
        if accelerator:
            try: act.setShortcut(QKeySequence(accelerator))
            except Exception: pass
        target.addAction(act); self.addon_actions.append(act); return act

    def register_toolbar_button(self,label,callback,tooltip=""):
        if not hasattr(self,"main_toolbar"): return None
        act=QAction(label,self); act.setToolTip(tooltip or label); act.triggered.connect(lambda _=False,cb=callback:cb()); self.main_toolbar.addAction(act); self.addon_actions.append(act); return act

    def register_panel(self,name,builder):
        try:
            widget=builder(self,self)
            if isinstance(widget,QWidget):
                dock=QDockWidget(name,self); dock.setObjectName("addon_dock_"+re.sub(r"\W","_",name)); dock.setWidget(widget)
                dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable|QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetClosable)
                self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,dock); self.addon_docks.append(dock); return dock
            QMessageBox.information(self,"Add-on",name+": Builder muss ein PyQt6-QWidget zurückgeben.")
        except Exception as ex: QMessageBox.warning(self,"Add-on-Panel",str(ex))

    def load_addon(self):
        path,_=QFileDialog.getOpenFileName(self,"Python-Add-on laden",str(self.addon_directory()),"Python-Dateien (*.py)")
        if not path: return
        try:
            if QMessageBox.question(self,"Plugin-Code ausführen?","Python-Plugins können Dateien, Netzwerk und andere Ressourcen mit deinen Benutzerrechten verwenden. Nur vertrauenswürdige Plugins aktivieren.\n\nFortfahren?") != QMessageBox.StandardButton.Yes: return
            self._activate_addon(Path(path))
        except Exception as ex: QMessageBox.critical(self,"Add-on fehlgeschlagen",str(ex)+"\n\n"+traceback.format_exc())

    def show_plugin_manager(self):
        dlg=QDialog(self); dlg.setWindowTitle("Plugin-Verwaltung und Git-Marktplatz"); dlg.resize(900,650); dlg.setMinimumSize(760,520)
        root=QVBoxLayout(dlg)
        warning=QLabel("Plugins können Menüs, Werkzeuge, Panels und eigene Einstellungen bereitstellen. Python-Plugins werden mit deinen Benutzerrechten ausgeführt. Installiere nur vertrauenswürdige Repositories."); warning.setWordWrap(True); root.addWidget(warning)
        tabs=QTabWidget(); root.addWidget(tabs,1)
        page=QWidget(); lay=QVBoxLayout(page)
        table=QTableWidget(0,3); table.setHorizontalHeaderLabels(["Status","Plugin","Dateipfad"]); table.horizontalHeader().setStretchLastSection(True); table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); lay.addWidget(table,1)
        row=QHBoxLayout(); buttons={}
        for label in ("Aktualisieren","Aktivieren","Deaktivieren","Einstellungen…","Datei löschen…"):
            b=QPushButton(label); row.addWidget(b); buttons[label]=b
        lay.addLayout(row); tabs.addTab(page,"Installierte Plugins")
        market=QWidget(); ml=QVBoxLayout(market); ml.addWidget(QLabel("Git-Repository als Marktplatzquelle klonen oder aktualisieren. Git muss installiert sein."))
        urlrow=QHBoxLayout(); url=QLineEdit(); url.setPlaceholderText("https://github.com/benutzer/plugin-repository.git"); install=QPushButton("Repository hinzufügen / aktualisieren"); urlrow.addWidget(url,1); urlrow.addWidget(install); ml.addLayout(urlrow)
        update=QPushButton("Alle Marktplatz-Repositories aktualisieren"); ml.addWidget(update)
        log=QPlainTextEdit(); log.setReadOnly(True); ml.addWidget(log,1); ml.addWidget(QLabel("Plugin-Dateien müssen register(ide) bereitstellen. Optional: ADDON_NAME und configure(ide) für Plugin-Einstellungen.")); tabs.addTab(market,"Git-Marktplatz")
        def selected():
            r=table.currentRow(); item=table.item(r,2) if r>=0 else None
            return Path(item.data(Qt.ItemDataRole.UserRole)) if item else None
        def fill():
            table.setRowCount(0); enabled={self._plugin_key(x) for x in self.settings.get("enabled_addons",[]) if isinstance(x,str)}
            for path in self._plugin_files():
                key=self._plugin_key(path); r=table.rowCount(); table.insertRow(r); rec=self.addon_records.get(key)
                table.setItem(r,0,QTableWidgetItem("Aktiviert" if key in enabled else "Deaktiviert")); table.setItem(r,1,QTableWidgetItem(rec["name"] if rec else path.stem)); item=QTableWidgetItem(str(path)); item.setData(Qt.ItemDataRole.UserRole,str(path)); table.setItem(r,2,item)
            table.resizeColumnsToContents()
        def activate():
            path=selected()
            if not path:return
            if QMessageBox.question(dlg,"Plugin aktivieren?","Der Python-Code wird mit deinen Benutzerrechten ausgeführt. Nur vertrauenswürdigen Code aktivieren.") != QMessageBox.StandardButton.Yes:return
            try:self._activate_addon(path); fill()
            except Exception as ex:QMessageBox.critical(dlg,"Aktivierung fehlgeschlagen",str(ex)+"\n\n"+traceback.format_exc())
        def deactivate():
            path=selected()
            if path:self._deactivate_addon(path); fill()
        def configure():
            path=selected(); rec=self.addon_records.get(self._plugin_key(path)) if path else None
            if not rec:QMessageBox.information(dlg,"Plugin-Einstellungen","Aktiviere das Plugin zuerst."); return
            fn=getattr(rec["module"],"configure",None) or getattr(rec["module"],"open_settings",None)
            if not callable(fn):QMessageBox.information(dlg,"Keine Einstellungen","Dieses Plugin stellt keine configure(ide)- oder open_settings(ide)-Funktion bereit."); return
            try:fn(self)
            except Exception as ex:QMessageBox.critical(dlg,"Einstellungen fehlgeschlagen",str(ex))
        def delete_plugin():
            path=selected()
            if not path:return
            if QMessageBox.question(dlg,"Plugin-Datei löschen?","Datei wirklich löschen?\n"+str(path)) != QMessageBox.StandardButton.Yes:return
            if self._plugin_key(path) in self.addon_records:self._deactivate_addon(path)
            try:path.unlink(); fill()
            except Exception as ex:QMessageBox.warning(dlg,"Löschen fehlgeschlagen",str(ex))
        def git_repo(repo_path):
            result=subprocess.run(["git","-C",str(repo_path),"pull","--ff-only"],capture_output=True,text=True,timeout=180) if (repo_path/".git").is_dir() else None
            if result is None:return subprocess.run(["git","clone","--depth","1",url.text().strip(),str(repo_path)],capture_output=True,text=True,timeout=240)
            return result
        def install_repo():
            repo=url.text().strip()
            if not (repo.startswith("https://") or repo.startswith("ssh://") or repo.startswith("git@")):
                QMessageBox.warning(dlg,"Repository-URL","Bitte eine HTTPS- oder SSH-Git-URL eingeben."); return
            if not shutil.which("git"):QMessageBox.warning(dlg,"Git fehlt","Installiere Git und stelle sicher, dass git im PATH liegt."); return
            name=Path(repo.rstrip("/").removesuffix(".git")).name; name=re.sub(r"[^A-Za-z0-9_.-]","_",name) or "plugin_repo"; dest=self.marketplace_directory()/name
            try:
                result=git_repo(dest); out=(result.stdout+"\n"+result.stderr).strip(); log.appendPlainText("Repository: "+repo+"\n"+out)
                if result.returncode:QMessageBox.warning(dlg,"Git fehlgeschlagen",out)
                else:QMessageBox.information(dlg,"Repository geladen","Repository wurde geladen. Prüfe seine Dateien und aktiviere vertrauenswürdige Plugins im ersten Tab.")
                fill()
            except Exception as ex:QMessageBox.warning(dlg,"Git-Fehler",str(ex))
        def update_repos():
            if not shutil.which("git"):QMessageBox.warning(dlg,"Git fehlt","Installiere Git zuerst."); return
            for repo in self.marketplace_directory().iterdir():
                if repo.is_dir() and (repo/".git").is_dir():
                    try:
                        r=subprocess.run(["git","-C",str(repo),"pull","--ff-only"],capture_output=True,text=True,timeout=180); log.appendPlainText(repo.name+": "+r.stdout+" "+r.stderr)
                    except Exception as ex:log.appendPlainText(repo.name+": "+str(ex))
            fill()
        buttons["Aktualisieren"].clicked.connect(fill); buttons["Aktivieren"].clicked.connect(activate); buttons["Deaktivieren"].clicked.connect(deactivate); buttons["Einstellungen…"].clicked.connect(configure); buttons["Datei löschen…"].clicked.connect(delete_plugin); install.clicked.connect(install_repo); update.clicked.connect(update_repos); table.cellDoubleClicked.connect(lambda *_:configure())
        fill(); bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Close); bb.rejected.connect(dlg.reject); root.addWidget(bb); dlg.exec()

    def disconnect_flipper(self):
        try:
            if self.serial_conn and self.serial_conn.is_open: self.serial_conn.close()
        except Exception as ex: QMessageBox.warning(self,'Trennen fehlgeschlagen',str(ex))
        self.serial_conn=None
        self.serial_port=None
        self.statusBar().showMessage('Flipper getrennt')
    def save_to_flipper(self):
        if not self._serial_ready(): QMessageBox.information(self,'Flipper nicht verbunden','Bitte zuerst Werkzeuge → Flipper Zero verbinden.'); return
        editor=self.current_editor()
        if not editor:return
        default='/ext/badusb/payload.txt' if self.language_mode=='badusb' else '/ext/apps/Scripts/payload.js'
        target,ok=QInputDialog.getText(self,'Auf Flipper speichern','Zielpfad (z. B. /ext/badusb/payload.txt):',text=default)
        if not ok:return
        target=target.strip()
        if not (target.startswith('/ext/') or target.startswith('/int/')) or '..' in target.split('/') or target.endswith('/'):
            QMessageBox.warning(self,'Ungültiger Pfad','Der Zielpfad muss eine Datei unter /ext/ oder /int/ sein.')
            return
        ext='.js' if self.language_mode=='javascript' else '.txt'
        if not target.lower().endswith(ext):target+=ext
        if QMessageBox.question(self,'Datei übertragen',f'{len(editor.toPlainText())} Zeichen nach {target} übertragen?\n\nDie Datei wird auf dem Flipper ersetzt, sofern die CLI-Befehle unterstützt werden.') != QMessageBox.StandardButton.Yes:return
        try:
            # Flipper CLI storage write receives file bytes until Ctrl+C. Ensure parent exists best-effort.
            parent=target.rsplit('/',1)[0]
            for part_path in ('/ext','/int'):
                if parent==part_path or parent.startswith(part_path+'/'):
                    sub=''
                    for part in parent.strip('/').split('/'):
                        sub+='/'+part
                        if sub not in ('/ext','/int'):
                            try:self._serial_command('storage mkdir '+sub,wait=.08,timeout=.35)
                            except Exception:pass
                    break
            try:self._serial_command('storage remove '+target,wait=.08,timeout=.35)
            except Exception:pass
            with self.serial_lock:
                self.serial_conn.write(f'storage write {target}\r'.encode())
                self.serial_conn.flush()
                time.sleep(.25)
                payload=editor.toPlainText().encode('utf-8')
                self.serial_conn.write(payload)
                self.serial_conn.flush()
                time.sleep(min(3.0,max(.25,len(payload)/5000)))
                self.serial_conn.write(b'\x03')
                self.serial_conn.flush()
                time.sleep(.2)
                response=self.serial_conn.read(8192).decode('utf-8','replace')
            self.statusBar().showMessage('Übertragung abgeschlossen: '+target)
            QMessageBox.information(self,'Übertragung beendet',f'Ziel: {target}\n\nCLI-Ausgabe: {response[-1200:] or "(keine Ausgabe)"}\n\nBitte kontrolliere die Datei auf dem Flipper.')
        except Exception as ex: QMessageBox.critical(self,'Übertragung fehlgeschlagen',str(ex))
    def toggle_language_mode(self):
        mode = 'javascript' if self.language_mode == 'badusb' else 'badusb'
        self.set_language_mode(mode)
    def _serial_ready(self): return self.serial_conn is not None and bool(getattr(self.serial_conn,'is_open',False))
    def connect_flipper(self):
        try:
            import serial
            from serial.tools import list_ports
        except ImportError:
            QMessageBox.warning(self,'pyserial fehlt','USB-Verbindung benötigt pyserial. Installation: py -m pip install pyserial')
            return
        ports=list(list_ports.comports())
        if not ports: QMessageBox.information(self,'Kein COM-Port','Kein serieller Port gefunden. Flipper verbinden und qFlipper schließen.'); return
        dlg=QDialog(self)
        dlg.setWindowTitle('Flipper Zero verbinden')
        form=QFormLayout(dlg)
        combo=QComboBox()
        choices=[f'{p.device} — {p.description}' for p in ports]
        combo.addItems(choices)
        form.addRow('Serieller Port:',combo)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec()!=QDialog.DialogCode.Accepted:return
        port=ports[combo.currentIndex()].device
        try:
            if self.serial_conn: self.serial_conn.close()
            self.serial_conn=serial.Serial(port,baudrate=230400,timeout=.15,write_timeout=3)
            self.serial_port=port
            time.sleep(.25)
            try: self.serial_conn.write(b'\r'); self.serial_conn.flush()
            except Exception: pass
            self.statusBar().showMessage(f'Flipper verbunden über {port}')
            QMessageBox.information(self,'Verbunden',f'Serielle Verbindung zu {port} hergestellt.')
        except Exception as ex: self.serial_conn=None; QMessageBox.critical(self,'Verbindung fehlgeschlagen',str(ex))
    def _serial_command(self,command,wait=.25,timeout=2.0):
        if not self._serial_ready(): raise RuntimeError('Kein Flipper verbunden.')
        with self.serial_lock:
            self.serial_conn.write(command.encode('utf-8')+b'\r')
            self.serial_conn.flush()
            time.sleep(wait)
            end=time.monotonic()+timeout
            chunks=[]
            while time.monotonic()<end:
                data=self.serial_conn.read(4096)
                if data: chunks.append(data)
                elif chunks: break
            return b''.join(chunks).decode('utf-8','replace')
    def show_flipper_console(self):
        """Single-field interactive Flipper CLI terminal with ANSI color support."""
        if not self._serial_ready():
            QMessageBox.information(self, 'Flipper nicht verbunden', 'Bitte zuerst Werkzeuge → Flipper Zero verbinden.')
            return

        dlg = QDialog(self)
        dlg.setWindowTitle('Flipper CLI-Terminal')
        dlg.resize(900, 600)
        lay = QVBoxLayout(dlg)
        output = QTextEdit()
        output.setAcceptRichText(False)
        output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        output.setUndoRedoEnabled(False)
        output.setFont(QFont('Consolas', 10))
        output.setStyleSheet(
            f"QTextEdit {{ background: {self.theme['editor']}; color: {self.theme['fg']}; "
            f"border: 1px solid {self.theme['accent']}; selection-background-color: {self.theme['accent']}; }}"
        )
        lay.addWidget(output, 1)

        # ANSI SGR palette. QTextEdit supports per-character foreground/background formats,
        # unlike QPlainTextEdit. Keep parser state between serial chunks.
        ansi_colors = {
            30:'#202020', 31:'#cd3131', 32:'#0dbc79', 33:'#e5e510',
            34:'#2472c8', 35:'#bc3fbc', 36:'#11a8cd', 37:'#e5e5e5',
            90:'#666666', 91:'#f14c4c', 92:'#23d18b', 93:'#f5f543',
            94:'#3b8eea', 95:'#d670d6', 96:'#29b8db', 97:'#ffffff',
        }
        ansi_bg = {code + 10: color for code, color in ansi_colors.items() if 30 <= code <= 37}
        ansi_bg.update({code + 10: color for code, color in ansi_colors.items() if 90 <= code <= 97})
        state = {
            'prompt_start': 0, 'history': [], 'history_index': 0,
            'fg': self.theme['fg'], 'bg': None, 'bold': False,
            'ansi_pending': '',
        }

        def make_format():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(state['fg']))
            if state['bg']:
                fmt.setBackground(QColor(state['bg']))
            fmt.setFontWeight(QFont.Weight.Bold if state['bold'] else QFont.Weight.Normal)
            return fmt

        def _xterm_color(index):
            # xterm 256-color palette (0-15 system colors, 16-231 cube, 232-255 gray).
            basic = ['#000000','#800000','#008000','#808000','#000080','#800080','#008080','#c0c0c0',
                     '#808080','#ff0000','#00ff00','#ffff00','#0000ff','#ff00ff','#00ffff','#ffffff']
            if index < 16:
                return basic[index]
            if index < 232:
                n = index - 16
                levels = [0, 95, 135, 175, 215, 255]
                r, g, b = levels[n // 36], levels[(n // 6) % 6], levels[n % 6]
                return f'#{r:02x}{g:02x}{b:02x}'
            gray = 8 + (index - 232) * 10
            return f'#{gray:02x}{gray:02x}{gray:02x}'

        def insert_ansi(chunk):
            """Append serial text while interpreting ANSI SGR colors and removing control codes."""
            if not chunk:
                return
            text = state['ansi_pending'] + chunk
            state['ansi_pending'] = ''
            # Normalize serial line endings. CLI output commonly uses CRLF; treating a bare
            # CR as a line break is safer than silently concatenating two terminal lines.
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            text = text.replace('\x08', '')
            cursor = output.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            i = 0
            plain_start = 0
            sgr = re.compile(r'\x1b\[([0-9;:]*)m')
            while i < len(text):
                if text[i] != '\x1b':
                    i += 1
                    continue
                # Emit printable text preceding this escape.
                if i > plain_start:
                    cursor.insertText(text[plain_start:i], make_format())
                # SGR: colors and attributes.
                m = sgr.match(text, i)
                if m:
                    raw_codes = m.group(1).replace(':', ';')
                    codes = [int(x) if x else 0 for x in raw_codes.split(';')]
                    j = 0
                    while j < len(codes):
                        code = codes[j]
                        if code == 0:
                            state.update(fg=self.theme['fg'], bg=None, bold=False)
                        elif code == 1:
                            state['bold'] = True
                        elif code in (2, 22):
                            state['bold'] = False
                        elif code == 39:
                            state['fg'] = self.theme['fg']
                        elif code == 49:
                            state['bg'] = None
                        elif code in ansi_colors:
                            state['fg'] = ansi_colors[code]
                        elif code in ansi_bg:
                            state['bg'] = ansi_bg[code]
                        elif code in (38, 48) and j + 1 < len(codes):
                            is_bg = code == 48
                            mode = codes[j + 1]
                            color = None
                            if mode == 5 and j + 2 < len(codes):
                                idx = max(0, min(255, codes[j + 2]))
                                color = _xterm_color(idx)
                                j += 2
                            elif mode == 2 and j + 4 < len(codes):
                                r, g, b = [max(0, min(255, v)) for v in codes[j + 2:j + 5]]
                                color = f'#{r:02x}{g:02x}{b:02x}'
                                j += 4
                            if color:
                                state['bg' if is_bg else 'fg'] = color
                        j += 1
                    i = m.end()
                    plain_start = i
                    continue
                # Other CSI controls (cursor, erase, device status) are not printed. If the
                # escape ends at the current chunk boundary, hold it for the next read.
                if i + 1 >= len(text):
                    state['ansi_pending'] = text[i:]
                    plain_start = len(text)
                    break
                if text[i + 1] == '[':
                    j = i + 2
                    while j < len(text) and not ('@' <= text[j] <= '~'):
                        j += 1
                    if j >= len(text):
                        state['ansi_pending'] = text[i:]
                        plain_start = len(text)
                        break
                    i = j + 1
                elif text[i + 1] == ']':
                    # OSC ends with BEL or ESC backslash.
                    j = i + 2
                    while j < len(text) and text[j] != '\x07' and text[j:j+2] != '\x1b\\':
                        j += 1
                    if j >= len(text):
                        state['ansi_pending'] = text[i:]
                        plain_start = len(text)
                        break
                    i = j + (2 if text[j:j+2] == '\x1b\\' else 1)
                else:
                    i += 2
                plain_start = i
            if plain_start < len(text):
                # Strip any stray non-SGR CSI sequences embedded in the remaining tail.
                tail = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text[plain_start:])
                if tail:
                    cursor.insertText(tail, make_format())
            output.setTextCursor(cursor)
            output.ensureCursorVisible()

        def get_current_input():
            doc = output.toPlainText()
            return doc[state['prompt_start']:] if state['prompt_start'] <= len(doc) else ''

        def put_prompt(preserve=''):
            cursor = output.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText('> ', make_format())
            state['prompt_start'] = len(output.toPlainText())
            if preserve:
                cursor.insertText(preserve, make_format())
            output.setTextCursor(cursor)
            output.ensureCursorVisible()

        # Keep an explicit reference to the IDE instance. Inside TerminalInput methods,
        # `self` refers to the QTextEdit widget, not the main window.
        ide = self

        class TerminalInput(QTextEdit):
            def keyPressEvent(self, event):
                key = event.key()
                cursor = self.textCursor()
                doc = self.toPlainText()
                start_pos = state['prompt_start']
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    command = self.toPlainText()[start_pos:].strip()
                    if command:
                        state['history'].append(command)
                        state['history_index'] = len(state['history'])
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    cursor.insertText('\n', make_format())
                    state['prompt_start'] = len(self.toPlainText())
                    self.setTextCursor(cursor)
                    if command:
                        try:
                            with ide.serial_lock:
                                if not ide._serial_ready():
                                    insert_ansi('Fehler: Flipper-Verbindung getrennt.\n')
                                else:
                                    ide.serial_conn.write(command.encode('utf-8') + b'\r')
                                    ide.serial_conn.flush()
                        except Exception as ex:
                            insert_ansi(f'\nFehler beim Senden: {ex}\n')
                        put_prompt()
                    else:
                        put_prompt()
                    return
                if key == Qt.Key.Key_Up:
                    if state['history']:
                        state['history_index'] = max(0, state['history_index'] - 1)
                        self._replace_input(state['history'][state['history_index']])
                    return
                if key == Qt.Key.Key_Down:
                    if state['history']:
                        state['history_index'] = min(len(state['history']), state['history_index'] + 1)
                        value = state['history'][state['history_index']] if state['history_index'] < len(state['history']) else ''
                        self._replace_input(value)
                    return
                if key == Qt.Key.Key_Home:
                    cursor.setPosition(start_pos)
                    self.setTextCursor(cursor)
                    return
                # Keep all edits in the active input line; don't let the cursor edit output.
                if cursor.position() < start_pos or (cursor.hasSelection() and cursor.selectionStart() < start_pos):
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.setTextCursor(cursor)
                if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Left) and self.textCursor().position() <= start_pos:
                    return
                if event.matches(QKeySequence.StandardKey.Copy):
                    super().keyPressEvent(event)
                    return
                if event.matches(QKeySequence.StandardKey.Paste):
                    cursor = self.textCursor()
                    if cursor.hasSelection() and cursor.selectionStart() < start_pos:
                        cursor.clearSelection()
                        cursor.movePosition(QTextCursor.MoveOperation.End)
                        self.setTextCursor(cursor)
                    super().keyPressEvent(event)
                    return
                super().keyPressEvent(event)

            def _replace_input(self, value):
                cursor = self.textCursor()
                cursor.setPosition(state['prompt_start'])
                cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                cursor.insertText(value, make_format())
                self.setTextCursor(cursor)

        # Keep a single terminal field: output, prompt, and command input share this widget.
        terminal = TerminalInput()
        terminal.setAcceptRichText(False)
        terminal.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        terminal.setUndoRedoEnabled(False)
        terminal.setFont(QFont('Consolas', 10))
        terminal.setStyleSheet(output.styleSheet())
        lay.removeWidget(output)
        output.deleteLater()
        output = terminal
        lay.addWidget(output, 1)

        # Replace the terminal's insert routine with one that temporarily protects typed input
        # while asynchronous serial output arrives.
        def append_terminal(data):
            """Insert device output, suppressing the Flipper's own prompt because the widget
            maintains one editable local prompt. Keep all banner/artwork and ANSI sequences."""
            if not data:
                return
            pending = get_current_input()

            # The Flipper CLI prompt is usually `>:`. If we display it as well as our own
            # editable `> ` prompt, it looks like the terminal has duplicated its prompt.
            # Normalize line endings first and remove only prompt tokens at line starts; the
            # welcome banner, ASCII art, command output and ANSI SGR sequences are untouched.
            normalized = data.replace('\r\n', '\n').replace('\r', '\n')
            normalized = re.sub(r'(?m)(?:^|\n)[ \t]*>:[ \t]*', '\n', normalized)

            cursor = output.textCursor()
            prompt_begin = max(0, state['prompt_start'] - 2)
            cursor.setPosition(prompt_begin)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            output.setTextCursor(cursor)
            insert_ansi(normalized)

            cursor = output.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            if output.toPlainText() and not output.toPlainText().endswith('\n'):
                cursor.insertText('\n', make_format())
            cursor.insertText('> ', make_format())
            state['prompt_start'] = len(output.toPlainText())
            if pending:
                cursor.insertText(pending, make_format())
            output.setTextCursor(cursor)
            output.ensureCursorVisible()

        # Initial message, then immediately poll the serial stream so startup text and colors
        # are not lost in a one-time read or swallowed by a command helper.
        insert_ansi(f'Flipper CLI-Terminal verbunden ({self.serial_port or "COM-Port"}).\n')
        put_prompt()
        timer = QTimer(dlg)
        def poll_serial():
            try:
                if not self._serial_ready():
                    return
                with self.serial_lock:
                    waiting = int(getattr(self.serial_conn, 'in_waiting', 0))
                    raw = self.serial_conn.read(min(waiting, 65536)) if waiting else b''
                if raw:
                    append_terminal(raw.decode('utf-8', 'replace'))
            except Exception as ex:
                append_terminal(f'\n[Serieller Lesefehler: {ex}]\n')
                timer.stop()
        timer.timeout.connect(poll_serial)
        timer.start(35)
        dlg.finished.connect(timer.stop)
        output.setFocus()
        dlg.exec()
    def open_flipper_filesystem(self):
        """Open a file-manager style browser for the Flipper storage CLI."""
        if not self._serial_ready():
            QMessageBox.information(
                self,
                "Flipper nicht verbunden",
                "Bitte zuerst Werkzeuge → Flipper Zero verbinden.",
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Flipper-Dateimanager")
        dlg.resize(980, 640)
        root = QVBoxLayout(dlg)

        # Navigation row, like a desktop file manager.
        nav = QHBoxLayout()
        back_btn = QPushButton("← Zurück")
        up_btn = QPushButton("↑ Übergeordnet")
        ext_btn = QPushButton("/ext")
        int_btn = QPushButton("/int")
        path_edit = QLineEdit("/ext")
        path_edit.setClearButtonEnabled(True)
        path_edit.setPlaceholderText("/ext oder /int")
        go_btn = QPushButton("Öffnen")
        refresh_btn = QPushButton("↻ Aktualisieren")
        recent_flipper_combo = QComboBox()
        recent_flipper_combo.setMinimumWidth(180)
        recent_flipper_combo.setToolTip("Zu einem zuvor besuchten Flipper-Verzeichnis springen")
        nav.addWidget(back_btn)
        nav.addWidget(up_btn)
        nav.addWidget(ext_btn)
        nav.addWidget(int_btn)
        nav.addWidget(path_edit, 1)
        nav.addWidget(go_btn)
        nav.addWidget(refresh_btn)
        nav.addWidget(QLabel("Verlauf:"))
        nav.addWidget(recent_flipper_combo)
        root.addLayout(nav)

        actions = QHBoxLayout()
        mkdir_btn = QPushButton("Neuer Ordner")
        upload_btn = QPushButton("Hochladen…")
        download_btn = QPushButton("Herunterladen…")
        rename_btn = QPushButton("Umbenennen…")
        delete_btn = QPushButton("Löschen")
        import_project_btn = QPushButton("Auswahl als Flipper-Projektordner merken")
        import_project_btn.setToolTip("Merkt den ausgewählten Ordner oder den Ordner einer ausgewählten Datei im Flipper-Verlauf")
        actions.addWidget(mkdir_btn)
        actions.addWidget(upload_btn)
        actions.addWidget(download_btn)
        actions.addWidget(rename_btn)
        actions.addWidget(delete_btn)
        actions.addWidget(import_project_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        listing = QTreeWidget()
        listing.setHeaderLabels(["Name", "Typ", "Größe", "Pfad"])
        listing.setRootIsDecorated(False)
        listing.setAlternatingRowColors(True)
        listing.setUniformRowHeights(True)
        listing.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        listing.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        listing.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        listing.setSortingEnabled(True)
        listing.sortItems(0, Qt.SortOrder.AscendingOrder)
        listing.header().setStretchLastSection(True)
        listing.setColumnWidth(0, 340)
        listing.setColumnWidth(1, 100)
        listing.setColumnWidth(2, 100)
        root.addWidget(listing, 1)

        status = QLabel("Bereit")
        status.setWordWrap(True)
        root.addWidget(status)
        history = []
        recent_flipper_folders = self.settings.get('recent_flipper_folders', [])
        if not isinstance(recent_flipper_folders, list):
            recent_flipper_folders = []

        def refresh_recent_flipper_combo(select_path=None):
            recent_flipper_combo.blockSignals(True)
            recent_flipper_combo.clear()
            for folder in recent_flipper_folders:
                recent_flipper_combo.addItem(folder, folder)
            if select_path:
                index = recent_flipper_combo.findData(select_path)
                if index >= 0:
                    recent_flipper_combo.setCurrentIndex(index)
            recent_flipper_combo.blockSignals(False)

        def remember_flipper_folder(folder):
            folder = clean_path(folder)
            recent_flipper_folders[:] = [folder] + [p for p in recent_flipper_folders if p != folder]
            del recent_flipper_folders[20:]
            self.settings['recent_flipper_folders'] = recent_flipper_folders[:]
            self.settings['recent_flipper_folder'] = folder
            self.save_settings()
            refresh_recent_flipper_combo(folder)

        def clean_path(raw):
            value = raw.strip().replace("\\", "/")
            if not value.startswith(("/ext", "/int")):
                raise ValueError("Pfad muss unter /ext oder /int liegen.")
            parts = value.split("/")
            if ".." in parts or any(part in ("", ".") for part in parts[1:-1]):
                raise ValueError("Ungültiger Pfad.")
            if value not in ("/ext", "/int"):
                value = value.rstrip("/")
            if not (value == "/ext" or value.startswith("/ext/") or value == "/int" or value.startswith("/int/")):
                raise ValueError("Pfad muss unter /ext oder /int liegen.")
            return value

        def current_path():
            return clean_path(path_edit.text())

        def parse_listing(response, base):
            """Accept common CLI listing formats across firmware versions."""
            entries = []
            seen = set()
            for raw_line in response.replace("\r", "\n").splitlines():
                line = raw_line.strip().strip("\x00")
                if not line:
                    continue
                low = line.lower()
                # The serial CLI can return buffered console/banner text together with
                # the `storage list` response. Never treat that terminal output as files.
                if low.startswith((
                    "listing files", "directory:", "path:", "storage list", "storage ",
                    "ok", "error", "failed", "welcome to flipper", "read the manual:",
                    "firmware version:", "run `help`", "run help", "usage:",
                )):
                    continue
                if line in (">:", ">", "?", "help"):
                    continue
                # Filter ASCII-art/logo lines and common CLI prompt fragments.
                if re.search(r"[\\_/|]{3,}", line) or re.fullmatch(r"[\s.:'`\-_=~()\\/|,;]+", line):
                    continue

                kind = "Datei"
                size = "—"
                name = line
                # Support common listing styles emitted by different Flipper firmwares.
                match = re.match(r"^(DIR|DIRECTORY|FILE)\s*:?\s+(.+?)\s*$", line, re.I)
                if match:
                    kind_token, name = match.groups()
                    kind = "Ordner" if kind_token.upper() in ("DIR", "DIRECTORY") else "Datei"
                else:
                    match = re.match(r"^\[([dDfF])\]\s*(.+?)\s*$", line)
                    if match:
                        kind = "Ordner" if match.group(1).lower() == "d" else "Datei"
                        name = match.group(2)
                    else:
                        match = re.match(r"^(.*?)(?:\s+\((?:DIR|DIRECTORY)\)|\s+\[(?:DIR|DIRECTORY)\])$", line, re.I)
                        if match:
                            name, kind = match.group(1).strip(), "Ordner"
                        elif line.endswith("/"):
                            name, kind = line.rstrip("/"), "Ordner"
                        else:
                            match = re.match(r"^(.*?)(?:\s{2,}|\t+)(\d+)\s*(?:bytes?)?$", line, re.I)
                            if match:
                                name, size = match.group(1).strip(), match.group(2)

                name = name.strip().strip('"').strip("'")
                # Remove common tree/list prefixes but preserve legitimate punctuation.
                name = re.sub(r"^(?:[├└│─|+`-]+\s*)+", "", name).strip()
                if not name or name in (".", "..") or "/" in name or name in seen:
                    continue
                if name.startswith("[") and name.endswith("]"):
                    continue
                seen.add(name)
                full = base.rstrip("/") + "/" + name
                entries.append((name, kind, size, full))
            return entries

        def load_directory(target=None, remember=True):
            try:
                destination = clean_path(target if target is not None else path_edit.text())
                if remember:
                    try:
                        old = clean_path(path_edit.text())
                        if not history or history[-1] != old:
                            history.append(old)
                    except ValueError:
                        pass
                path_edit.setText(destination)
                remember_flipper_folder(destination)
                listing.setSortingEnabled(False)
                listing.clear()
                response = self._serial_command("storage list " + destination, wait=0.25, timeout=2.5)
                entries = parse_listing(response, destination)
                # A CLI response that reports an error should not masquerade as an empty folder.
                if not entries and re.search(r"(?i)(error|failed|not found|invalid path|not a directory|is a file|unknown path)", response):
                    status.setText(response.strip()[-500:] or "Verzeichnis konnte nicht gelesen werden.")
                    return
                for name, kind, size, full in entries:
                    item = QTreeWidgetItem([name, kind, size, full])
                    item.setData(0, Qt.ItemDataRole.UserRole, full)
                    if kind == "Ordner":
                        item.setText(0, "📁  " + name)
                    else:
                        item.setText(0, "📄  " + name)
                    listing.addTopLevelItem(item)
                listing.setSortingEnabled(True)
                listing.sortItems(0, Qt.SortOrder.AscendingOrder)
                status.setText(f"{destination}  ·  {len(entries)} Einträge")
            except Exception as ex:
                status.setText("Fehler beim Lesen: " + str(ex))

        def selected_paths():
            return [item.data(0, Qt.ItemDataRole.UserRole) for item in listing.selectedItems()]

        def open_selected(item=None, column=0):
            item = item or (listing.currentItem())
            if not item:
                return
            if item.text(1) == "Ordner":
                load_directory(item.data(0, Qt.ItemDataRole.UserRole))

        def go_parent():
            try:
                current = current_path()
                if current in ("/ext", "/int"):
                    return
                parent = current.rsplit("/", 1)[0] or "/ext"
                load_directory(parent)
            except ValueError as ex:
                status.setText(str(ex))

        def go_back():
            if not history:
                go_parent()
                return
            previous = history.pop()
            load_directory(previous, remember=False)

        def import_selected_as_flipper_project_folder():
            item = listing.currentItem()
            if item is None:
                # No row selected: remember the directory currently being viewed.
                try:
                    folder = current_path()
                except ValueError as ex:
                    QMessageBox.warning(dlg, "Flipper-Verlauf", str(ex))
                    return
            else:
                selected_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item.text(1) == "Ordner":
                    folder = selected_path
                else:
                    folder = selected_path.rsplit("/", 1)[0] or "/ext"
            try:
                remember_flipper_folder(folder)
                status.setText(f"Im Flipper-Verlauf gespeichert: {folder}")
            except ValueError as ex:
                QMessageBox.warning(dlg, "Flipper-Verlauf", str(ex))

        def jump_to_recent_flipper_folder(index):
            if index < 0:
                return
            folder = recent_flipper_combo.itemData(index)
            if folder:
                load_directory(folder)

        def make_folder():
            try:
                base = current_path()
                name, ok = QInputDialog.getText(dlg, "Neuer Ordner", "Ordnername:")
                name = name.strip()
                if not ok or not name:
                    return
                if name in (".", "..") or "/" in name or "\\" in name:
                    QMessageBox.warning(dlg, "Ungültiger Name", "Bitte nur einen Ordnernamen ohne Pfad verwenden.")
                    return
                response = self._serial_command(f"storage mkdir {base}/{name}", wait=0.25, timeout=2.0)
                status.setText(response.strip()[-300:] or "Ordnerbefehl gesendet.")
                load_directory(base, remember=False)
            except Exception as ex:
                QMessageBox.warning(dlg, "Ordner erstellen fehlgeschlagen", str(ex))

        def upload_files():
            try:
                base = current_path()
                paths, _ = QFileDialog.getOpenFileNames(dlg, "Dateien auf den Flipper hochladen")
                if not paths:
                    return
                for local_path in paths:
                    source = Path(local_path)
                    target = base.rstrip("/") + "/" + source.name
                    if QMessageBox.question(
                        dlg,
                        "Datei hochladen",
                        f"{source.name} nach {target} übertragen?\nEine vorhandene Datei gleichen Namens kann ersetzt werden.",
                    ) != QMessageBox.StandardButton.Yes:
                        continue
                    payload = source.read_bytes()
                    # The CLI's storage write command consumes the following bytes until Ctrl+C.
                    with self.serial_lock:
                        self.serial_conn.write(f"storage write {target}\r".encode("utf-8"))
                        self.serial_conn.flush()
                        time.sleep(0.25)
                        self.serial_conn.write(payload)
                        self.serial_conn.flush()
                        time.sleep(min(4.0, max(0.3, len(payload) / 4000)))
                        self.serial_conn.write(b"\x03")
                        self.serial_conn.flush()
                        time.sleep(0.2)
                        response = self.serial_conn.read(8192).decode("utf-8", "replace")
                    status.setText(f"Übertragen: {source.name}  ·  {response.strip()[-180:]}")
                load_directory(base, remember=False)
            except Exception as ex:
                QMessageBox.critical(dlg, "Upload fehlgeschlagen", str(ex))

        def download_file():
            paths = selected_paths()
            if len(paths) != 1:
                QMessageBox.information(dlg, "Datei herunterladen", "Bitte genau eine Datei auswählen.")
                return
            item = listing.currentItem()
            if not item or item.text(1) == "Ordner":
                QMessageBox.information(dlg, "Datei herunterladen", "Bitte eine Datei auswählen.")
                return
            target, _ = QFileDialog.getSaveFileName(dlg, "Datei speichern unter", str(self.working_directory() / Path(paths[0]).name))
            if not target:
                return
            try:
                # storage read is suitable for text payloads. Binary files may not survive a CLI text stream.
                response = self._serial_command("storage read " + paths[0], wait=0.2, timeout=3.0)
                # Strip echoed command and CLI prompt only; keep the content's line breaks.
                lines = response.replace("\r", "").splitlines()
                cleaned = []
                for line in lines:
                    if line.strip() in ("storage read " + paths[0], ">:", ">"):
                        continue
                    if line.startswith("Error") or line.startswith("Failed"):
                        raise RuntimeError(line)
                    cleaned.append(line)
                imported_text = "\n".join(cleaned).rstrip("\n") + "\n"
                Path(target).write_text(imported_text, encoding="utf-8")
                imported_path = Path(target).resolve()
                imported_folder = imported_path.parent
                self.settings['last_directory'] = str(imported_folder)
                self.settings['recent_project_folder'] = str(imported_folder)
                self._update_recent_project_folders(imported_folder, refresh_combo=True)
                self.set_language_mode(self.detect_language_mode(str(imported_path), imported_text), update_all=False)
                self.new_tab(imported_text, str(imported_path))
                # Nach dem Import den lokalen Dateiexplorer direkt zum Speicherort der
                # importierten Flipper-Datei wechseln und den importierten Eintrag markieren.
                self.file_explorer_path.setText(str(imported_folder))
                self.refresh_local_file_explorer(imported_folder)
                self._select_local_explorer_path(imported_path)
                self.update_working_directory()
                self.save_settings()
                status.setText(f"Von {paths[0]} importiert → {imported_path}; Dateiexplorer geöffnet: {imported_folder}")
            except Exception as ex:
                QMessageBox.critical(dlg, "Download fehlgeschlagen", str(ex))

        def rename_entry():
            paths = selected_paths()
            if len(paths) != 1:
                QMessageBox.information(dlg, "Umbenennen", "Bitte genau einen Eintrag auswählen.")
                return
            source = paths[0]
            old_name = source.rsplit("/", 1)[-1]
            name, ok = QInputDialog.getText(dlg, "Umbenennen", "Neuer Name:", text=old_name)
            name = name.strip()
            if not ok or not name or name == old_name:
                return
            if name in (".", "..") or "/" in name or "\\" in name:
                QMessageBox.warning(dlg, "Ungültiger Name", "Bitte nur einen Namen ohne Pfad verwenden.")
                return
            destination = source.rsplit("/", 1)[0] + "/" + name
            try:
                response = self._serial_command(f"storage move {source} {destination}", wait=0.25, timeout=2.0)
                status.setText(response.strip()[-300:] or "Umbenennen-Befehl gesendet.")
                load_directory(current_path(), remember=False)
            except Exception as ex:
                QMessageBox.warning(dlg, "Umbenennen fehlgeschlagen", str(ex))

        def delete_entries():
            paths = selected_paths()
            if not paths:
                QMessageBox.information(dlg, "Löschen", "Wähle mindestens eine Datei oder einen Ordner aus.")
                return
            preview = "\n".join(paths[:8]) + ("\n…" if len(paths) > 8 else "")
            if QMessageBox.question(
                dlg,
                "Einträge löschen",
                f"{len(paths)} Eintrag/Einträge wirklich löschen?\n\n{preview}\n\nDieser Vorgang kann nicht rückgängig gemacht werden.",
            ) != QMessageBox.StandardButton.Yes:
                return
            try:
                for target in paths:
                    response = self._serial_command("storage remove " + target, wait=0.2, timeout=2.0)
                    if re.search(r"(?i)(error|failed|not found)", response):
                        status.setText(f"Fehler bei {target}: {response.strip()[-250:]}")
                        return
                load_directory(current_path(), remember=False)
                status.setText(f"{len(paths)} Eintrag/Einträge gelöscht.")
            except Exception as ex:
                QMessageBox.critical(dlg, "Löschen fehlgeschlagen", str(ex))

        go_btn.clicked.connect(lambda: load_directory())
        ext_btn.clicked.connect(lambda: load_directory("/ext"))
        int_btn.clicked.connect(lambda: load_directory("/int"))
        refresh_btn.clicked.connect(lambda: load_directory(current_path(), remember=False))
        path_edit.returnPressed.connect(lambda: load_directory())
        back_btn.clicked.connect(go_back)
        up_btn.clicked.connect(go_parent)
        mkdir_btn.clicked.connect(make_folder)
        upload_btn.clicked.connect(upload_files)
        download_btn.clicked.connect(download_file)
        rename_btn.clicked.connect(rename_entry)
        delete_btn.clicked.connect(delete_entries)
        import_project_btn.clicked.connect(import_selected_as_flipper_project_folder)
        recent_flipper_combo.activated.connect(jump_to_recent_flipper_folder)
        listing.itemDoubleClicked.connect(open_selected)
        refresh_recent_flipper_combo()
        initial_flipper_path = self.settings.get('recent_flipper_folder', '/ext')
        try:
            initial_flipper_path = clean_path(initial_flipper_path)
        except ValueError:
            initial_flipper_path = '/ext'
        load_directory(initial_flipper_path, remember=False)
        dlg.exec()

    def format_javascript(self):
        """Format the current JS/mJS editor using jsbeautifier when installed, with a safe fallback."""
        editor=self.current_editor()
        if not editor:
            return
        source=editor.toPlainText()
        if getattr(editor, "language_mode", self.language_mode) != "javascript":
            answer = QMessageBox.question(self, "JavaScript-Formatter", "Der aktuelle Tab ist nicht als JavaScript markiert. Trotzdem formatieren?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            import jsbeautifier
            opts=jsbeautifier.default_options()
            opts.indent_size=4
            opts.indent_char=" "
            opts.preserve_newlines=True
            formatted=jsbeautifier.beautify(source,opts)
        except ImportError:
            # Conservative formatter: normalizes indentation and spacing outside strings/comments.
            # It deliberately preserves statement content and only breaks at braces/semicolons.
            formatted=self._basic_js_format(source)
        if formatted != source:
            cursor=editor.textCursor(); pos=cursor.position(); anchor=cursor.anchor()
            editor.setPlainText(formatted)
            cursor=editor.textCursor(); cursor.setPosition(min(anchor,len(formatted))); cursor.setPosition(min(pos,len(formatted)),QTextCursor.MoveMode.KeepAnchor); editor.setTextCursor(cursor)
            self.statusBar().showMessage("JavaScript/mJS formatiert",4000)
        else:
            self.statusBar().showMessage("JavaScript ist bereits formatiert",3000)

    @staticmethod
    def _basic_js_format(source):
        out=[]; indent=0; line=""; quote=None; escaped=False; line_comment=False; block_comment=False; parens=0
        def emit(force=False):
            nonlocal line
            value=line.strip()
            if value or force: out.append("    "*max(indent,0)+value)
            line=""
        i=0
        while i<len(source):
            ch=source[i]; nxt=source[i+1] if i+1<len(source) else ""
            if line_comment:
                line+=ch
                if ch=="\n": emit(); line_comment=False
                i+=1; continue
            if block_comment:
                line+=ch
                if ch=="/" and i>0 and source[i-1]=="*": block_comment=False
                i+=1; continue
            if quote:
                line+=ch
                if escaped: escaped=False
                elif ch=="\\": escaped=True
                elif ch==quote: quote=None
                i+=1; continue
            if ch in ("'",'"',"`"):
                quote=ch; line+=ch
            elif ch=="/" and nxt=="/": line+="//"; line_comment=True; i+=1
            elif ch=="/" and nxt=="*": line+="/*"; block_comment=True; i+=1
            elif ch=="(": parens+=1; line+=ch
            elif ch==")": parens=max(0,parens-1); line+=ch
            elif ch=="{":
                if line.strip() and not line.rstrip().endswith((" ","\t")): line+=" "
                line+="{"; emit(); indent+=1
            elif ch=="}":
                if line.strip(): emit()
                indent=max(0,indent-1); line="}"
                if nxt in (";", ",", ")", "]", "."):
                    pass
                else:
                    emit()
            elif ch==";" and parens==0:
                line+=";"; emit()
            elif ch=="\n" or ch=="\r":
                if line.strip(): emit()
            else:
                if ch.isspace():
                    if line and not line.endswith(" "): line+=" "
                else: line+=ch
            i+=1
        if line.strip(): emit()
        return "\n".join(out).rstrip()+"\n"

    def check_javascript(self):
        e=self.current_editor()
        if not e:return
        source=e.toPlainText(); stack=[]; pairs={')':'(',']':'[','}':'{'}; quote=None; escaped=False; line=1; issues=[]; i=0; line_comment=False; block_comment=False
        while i<len(source):
            ch=source[i]
            nx=source[i+1] if i+1<len(source) else ''
            if ch=='\n': line+=1; line_comment=False; i+=1; continue
            if line_comment: i+=1; continue
            if block_comment:
                if ch=='*' and nx=='/': block_comment=False; i+=2
                else:i+=1
                continue
            if quote:
                if escaped:escaped=False
                elif ch=='\\':escaped=True
                elif ch==quote:quote=None
                i+=1
                continue
            if ch=='/' and nx=='/':line_comment=True;i+=2;continue
            if ch=='/' and nx=='*':block_comment=True;i+=2;continue
            if ch in ('"',"'",'`'):quote=ch
            elif ch in '([{':stack.append((ch,line))
            elif ch in ')]}':
                if not stack or stack[-1][0]!=pairs[ch]:issues.append(f'Zeile {line}: unerwartete schließende Klammer {ch}')
                else:stack.pop()
            i+=1
        if quote:issues.append(f'Zeile {line}: Zeichenkette nicht geschlossen')
        if block_comment:issues.append('Blockkommentar nicht geschlossen')
        issues.extend(f'Zeile {n}: {ch} wird nicht geschlossen' for ch,n in reversed(stack))
        self.output.setPlainText('\n'.join(issues) if issues else 'Keine offensichtlichen Syntax-/Klammerfehler gefunden. Dies ist kein vollständiger mJS-Parser.')
        self.statusBar().showMessage(f'JavaScript-Prüfung: {len(issues)} mögliche Fehler')
    def show_js_sandbox(self):
        """Searchable Flipper mJS/Momentum API reference with examples and insert support."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Befehlsreferenz – BadUSB / Flipper mJS")
        dlg.resize(1040, 700)
        lay = QVBoxLayout(dlg)
        active_mode = self.language_mode
        mode_label = "JavaScript / mJS" if active_mode == "javascript" else "BadUSB / DuckyScript"
        info = QLabel(
            f'Angezeigte Referenz: {mode_label}. Die Referenz wechselt automatisch mit dem Editor-Modus. '
            'Flipper-mJS ist nicht automatisch Node.js oder Browser-JavaScript. Die genaue API hängt von Firmware und Version ab. '
            'Doppelklicke einen Eintrag, um sein Beispiel in den Editor einzufügen. Die Referenz führt den Code nicht aus.'
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        links = QHBoxLayout()
        for label, url in [
            ("Offizielle Flipper-Doku", "https://developer.flipper.net/flipperzero/doxygen/js.html"),
            ("Momentum-JavaScript-Doku", "https://github.com/jamisonderek/flipper-zero-tutorials/wiki/JavaScript-%E2%80%90-Momentum"),
            ("Momentum-Firmware", "https://github.com/Next-Flip/Momentum-Firmware"),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            links.addWidget(b)
        links.addStretch(1)
        lay.addLayout(links)
        search = QLineEdit()
        search.setPlaceholderText("Suchen: require, badusb.press, storage, GPIO, BLE, Beispiel …")
        lay.addWidget(search)
        split = QSplitter(Qt.Orientation.Horizontal)
        tree = QTreeWidget()
        tree.setHeaderLabels(["API / Beispiel", "Beschreibung"])
        tree.setColumnWidth(0, 250)
        detail = QPlainTextEdit()
        detail.setReadOnly(True)
        detail.setPlaceholderText("Wähle links einen Eintrag aus, um Erklärung und Beispiel zu sehen.")
        split.addWidget(tree)
        split.addWidget(detail)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        lay.addWidget(split, 1)
        buttons = QDialogButtonBox()
        insert_btn = buttons.addButton("Beispiel in Editor einfügen", QDialogButtonBox.ButtonRole.ActionRole)
        close_btn = buttons.addButton(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(dlg.accept)
        lay.addWidget(buttons)

        # Entries are intentionally labelled as firmware-dependent where signatures vary.
        refs = {
            "Grundlagen": [
                ("require()", "Lädt ein Modul, sofern es von der installierten Firmware bereitgestellt wird.", 'let badusb = require("badusb");\nlet storage = require("storage");'),
                ("print() / delay()", "Gibt Text aus bzw. wartet eine Zeit in Millisekunden.", 'print("Hallo Flipper");\ndelay(500);'),
                ("mJS statt Node.js", "Nicht alle modernen JavaScript-Funktionen, Browser-APIs oder npm-Pakete sind verfügbar.", '// Firmware- und SDK-Unterstützung vor der Nutzung prüfen'),
                ("SDK-Features", "Momentum-Helfer zum Prüfen optionaler Firmware-Features; Verfügbarkeit prüfen.", 'if (doesSdkSupport(["widget"])) {\n  print("Widget wird unterstützt");\n}'),
                ("Skript per CLI starten", "Beispiel für die Flipper-CLI; der Befehl gehört in die Geräte-CLI, nicht in JavaScript.", 'js /ext/apps/Scripts/demo.js'),
            ],
            "badusb-Modul": [
                ("require('badusb')", "USB-HID-Modul laden.", 'let badusb = require("badusb");'),
                ("setup()", "Initialisiert USB-HID vor der Verwendung.", 'let badusb = require("badusb");\nbadusb.setup();'),
                ("isConnected()", "Prüft, ob das USB-Ziel verbunden ist.", 'if (badusb.isConnected()) {\n  badusb.println("Hello");\n}'),
                ("print() / println()", "Tippt Text; println fügt einen Zeilenabschluss bzw. Enter hinzu. Signatur firmwareabhängig.", 'badusb.print("Hallo Welt");\nbadusb.println("fertig");'),
                ("press() / hold() / release()", "Sendet bzw. hält Tasten oder Tastenkombinationen. Vor Nutzung Firmware-Signatur prüfen.", 'badusb.press("CTRL", "SHIFT", "ESC");\nbadusb.hold("CTRL", "c");\nbadusb.release();'),
                ("quit()", "Gibt USB-HID frei; Verfügbarkeit kann je nach Firmware variieren.", 'badusb.quit();'),
            ],
            "storage-Modul": [
                ("exists() / stat()", "Prüft einen Pfad bzw. fragt Dateiinformationen ab.", 'let storage = require("storage");\nprint(storage.exists("/ext/demo.txt"));'),
                ("readDirectory()", "Liest Verzeichniseinträge; genaue Rückgabeform anhand der installierten Firmware prüfen.", 'let storage = require("storage");\nlet files = storage.readDirectory("/ext/apps/Scripts");\nprint(files);'),
                ("openFile() / read()", "Datei öffnen und Inhalt lesen. Modus, Argumente und Rückgabewert sind firmwareabhängig.", 'let storage = require("storage");\nlet file = storage.openFile("/ext/demo.txt", "r");\nlet text = file.read("ascii", 1024);\nfile.close();\nprint(text);'),
                ("write() / mkdir()", "Schreibt Daten bzw. erstellt ein Verzeichnis; vor Schreiboperationen den Zielpfad prüfen.", 'let storage = require("storage");\nstorage.mkdir("/ext/mydir");'),
                ("copy() / rename() / remove()", "Dateisystemoperationen, deren Verfügbarkeit und Signaturen firmwareabhängig sein können.", 'let storage = require("storage");\n// Signatur in der Doku der installierten Firmware prüfen.'),
            ],
            "GUI / event_loop": [
                ("Module importieren", "In der aktuellen API wird event_loop vor gui und GUI-Submodulen geladen.", 'let eventLoop = require("event_loop");\nlet gui = require("gui");\nlet dialogView = require("gui/dialog");'),
                ("Dialog / Textansicht", "GUI-Ansichten werden über den Event Loop verwaltet; API und Ereignisse firmwareabhängig.", 'let eventLoop = require("event_loop");\nlet gui = require("gui");\nlet dialogView = require("gui/dialog");\n// Details der installierten SDK-Doku entnehmen.'),
                ("widget-Modul (Momentum)", "Momentum-API für Widget-Elemente; Feature-Flags und genaue Signaturen prüfen.", 'let widget = require("widget");\n// Methoden gemäß zur Firmware passender Referenz ergänzen.'),
            ],
            "Hardware / weitere Module": [
                ("gpio", "GPIO-Zugriff; Pins und elektrische Eigenschaften vor Anschluss prüfen.", 'let eventLoop = require("event_loop");\nlet gpio = require("gpio");\nlet pin = gpio.get("pc3");\npin.init({ direction: "out", outMode: "push_pull" });\npin.write(true);\ndelay(500);\npin.write(false);'),
                ("notification", "LED-, Ton- oder Vibrationssignale; Methoden unterscheiden sich je nach Firmware.", 'let notification = require("notification");\nnotification.success();'),
                ("serial", "Serielle Schnittstelle/UART; unterstützte Geräte und Signaturen prüfen.", 'let serial = require("serial");\n// Setup- und I/O-Signatur anhand der Firmware-Doku prüfen.'),
                ("i2c / spi (Momentum)", "Bus-APIs für unterstützte Hardware. Pins, Geräteparameter und Signaturen firmwareabhängig.", 'let i2c = require("i2c");\nlet spi = require("spi");'),
                ("subghz (Momentum)", "Sub-GHz-Funkfunktionen; nur im gesetzlichen Rahmen und mit unterstützten Dateien/Frequenzen nutzen.", 'let subghz = require("subghz");\n// Methoden und zulässige Parameter in der Firmware-Doku prüfen.'),
                ("blebeacon (Momentum)", "BLE-Beacon-Modul; Konfigurations- und Paketmethoden sind firmwareabhängig.", 'let blebeacon = require("blebeacon");\n// API-Signatur für deine Momentum-Version prüfen.'),
                ("usbdisk (Momentum)", "Virtuelles USB-Laufwerk; benötigt passende Firmware-Features und korrekte Bereinigung.", 'let usbdisk = require("usbdisk");\n// Unterstützung und create/start/stop-Signaturen prüfen.'),
                ("flipper / math / vgm", "Geräteinformationen, Mathematik oder Video Game Module; je nach Firmware verfügbar.", 'let flipper = require("flipper");\nlet math = require("math");\nlet vgm = require("vgm");'),
            ],
        }
        # Keep the two references separate: only the active editor mode is shown.
        refs["BadUSB-Befehle"] = [(name, desc, name) for name, desc in COMMANDS.items()]
        # Add every known global, module, and method so the reference and autocomplete share a catalogue.
        refs["Globale Begriffe"] = [(name, desc, name) for name, desc in JS_GLOBALS.items()]
        refs["Modul-Katalog"] = [(f'require("{name}")', desc, f'let {name} = require("{name}");') for name, desc in JS_MODULES.items()]
        for module, methods in JS_METHODS.items():
            refs[f"Methoden: {module}"] = [(f"{module}.{method}()", desc + " (Signatur bitte für die installierte Firmware prüfen.)", f'let {module} = require("{module}");\n// {desc}\n{module}.{method}();') for method, desc in methods.items()]

        selected = {"snippet": "", "description": ""}
        def populate(query=""):
            tree.clear()
            q = query.casefold().strip()
            for group, entries in refs.items():
                is_badusb_group = group == "BadUSB-Befehle"
                if (active_mode == "badusb" and not is_badusb_group) or (active_mode == "javascript" and is_badusb_group):
                    continue
                matches = [(name, desc, snippet) for name, desc, snippet in entries
                           if not q or q in group.casefold() or q in name.casefold() or q in desc.casefold() or q in snippet.casefold()]
                if not matches:
                    continue
                parent = QTreeWidgetItem([f"{group} ({len(matches)})", ""])
                tree.addTopLevelItem(parent)
                for name, desc, snippet in matches:
                    child = QTreeWidgetItem([name, desc])
                    child.setData(0, Qt.ItemDataRole.UserRole, (desc, snippet))
                    parent.addChild(child)
                parent.setExpanded(bool(q) or group in ("Grundlagen", "badusb-Modul"))
        def show_detail(item, column=0):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if not data:
                selected["snippet"] = ""
                detail.clear()
                return
            desc, snippet = data
            selected["snippet"] = snippet
            selected["description"] = desc
            detail.setPlainText(desc + "\n\nBeispiel / Einfügevorlage:\n\n" + snippet + "\n\nHinweis: Nicht jede Methode existiert in jeder Firmware-Version.")
        def insert_example():
            snippet = selected.get("snippet", "")
            editor = self.current_editor()
            if not snippet or editor is None:
                QMessageBox.information(dlg, "Befehlsreferenz", "Wähle zuerst einen Eintrag mit Beispiel aus und öffne einen Editor-Tab.")
                return
            cursor = editor.textCursor()
            cursor.insertText(snippet)
            editor.setTextCursor(cursor)
            editor.setFocus()
            dlg.accept()
        search.textChanged.connect(populate)
        tree.currentItemChanged.connect(lambda current, previous: show_detail(current) if current else None)
        tree.itemDoubleClicked.connect(lambda item, column: insert_example() if item.data(0, Qt.ItemDataRole.UserRole) else None)
        insert_btn.clicked.connect(insert_example)
        populate()
        dlg.exec()
    def show_help(self):
        dlg=QDialog(self)
        dlg.setWindowTitle('BadUSB / mJS Befehlsreferenz')
        dlg.resize(680,560)
        lay=QVBoxLayout(dlg)
        search=QLineEdit()
        search.setPlaceholderText('Befehl suchen …')
        lay.addWidget(search)
        table=QTableWidget(0,2)
        table.setHorizontalHeaderLabels(['Befehl','Beschreibung'])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(table,1)
        def fill(q=''):
            table.setRowCount(0)
            for name,desc in {**COMMANDS,**{k:v for k,v in JS_GLOBALS.items()},**{k:'Flipper-JS-Modul' for k in JS_MODULES}}.items():
                if q.lower() in name.lower() or q.lower() in desc.lower():
                    r=table.rowCount()
                    table.insertRow(r)
                    table.setItem(r,0,QTableWidgetItem(name))
                    table.setItem(r,1,QTableWidgetItem(desc))
        search.textChanged.connect(fill); table.cellDoubleClicked.connect(lambda r,c:self.current_editor() and self.current_editor().textCursor().insertText(table.item(r,0).text())); fill(); dlg.exec()
    def show_settings(self):
        """Tabbed, extensible settings dialog with editor, UI, files and Ollama options."""
        dlg = QDialog(self)
        dlg.setWindowTitle('Einstellungen – BadUSB IDE')
        dlg.resize(940, 790)
        dlg.setMinimumSize(820, 680)
        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)
        tabs = QTabWidget()
        outer.addWidget(tabs, 1)

        def page(title):
            w = QWidget()
            lay = QVBoxLayout(w)
            lay.setContentsMargins(18, 18, 18, 18)
            lay.setSpacing(12)
            form = QFormLayout()
            form.setHorizontalSpacing(24)
            form.setVerticalSpacing(12)
            lay.addLayout(form)
            lay.addStretch(1)
            tabs.addTab(w, title)
            return form

        def checkbox(form, label, key, default, help_text=None):
            c = QCheckBox(label)
            c.setChecked(bool(self.settings.get(key, default)))
            if help_text: c.setToolTip(help_text)
            form.addRow(c)
            return c

        def spin(form, label, key, default, minimum, maximum, suffix=''):
            c = QSpinBox(); c.setRange(minimum, maximum); c.setValue(int(self.settings.get(key, default))); c.setSuffix(suffix)
            form.addRow(label, c)
            return c

        # Appearance
        f = page('Darstellung')
        theme = QComboBox(); theme.addItems(THEMES); theme.setCurrentText(self.theme_name)
        f.addRow('Farbschema', theme)
        font_family = QComboBox(); font_family.setEditable(True)
        font_family.addItems(['Consolas', 'Cascadia Code', 'Cascadia Mono', 'JetBrains Mono', 'Fira Code', 'Source Code Pro', 'Courier New'])
        font_family.setCurrentText(self.settings.get('font_family', 'Consolas'))
        f.addRow('Editor-Schriftart', font_family)
        font_size = spin(f, 'Editor-Schriftgröße', 'font_size', 11, 7, 36, ' pt')
        ui_scale = spin(f, 'Zusätzliche UI-Schriftgröße', 'ui_font_size', 10, 8, 24, ' pt')
        remember_size = checkbox(f, 'Fenstergröße und Dock-Anordnung speichern', 'remember_window_size', True)
        show_status = checkbox(f, 'Statusleiste anzeigen', 'show_status_bar', True)
        restore_docks = checkbox(f, 'Befehle beim Start anzeigen', 'show_commands', True)
        show_ollama = checkbox(f, 'Ollama-Fenster beim Start anzeigen', 'show_ollama', False)
        show_output = checkbox(f, 'Output-/Prüffenster beim Start anzeigen', 'show_output', True)
        show_explorer = checkbox(f, 'Dateiexplorer beim Start anzeigen', 'show_file_explorer', True)

        # Editor
        f = page('Editor')
        autocomplete = checkbox(f, 'Autovervollständigung aktivieren', 'autocomplete', True)
        live = checkbox(f, 'Live-Syntaxprüfung beim Tippen', 'live_check', True)
        word_wrap = checkbox(f, 'Zeilen automatisch umbrechen', 'word_wrap', False)
        current_line = checkbox(f, 'Aktuelle Zeile hervorheben', 'highlight_current_line', True)
        spaces = spin(f, 'Tabulatorbreite', 'tab_width', 4, 1, 16, ' Leerzeichen')
        indent_spaces = checkbox(f, 'Tab-Taste als Leerzeichen einfügen', 'insert_spaces', True)
        auto_pair = checkbox(f, 'Klammern und Anführungszeichen automatisch ergänzen', 'auto_pairs', False,
                             'Wird gespeichert; automatische Ergänzung benötigt eine Editor-Erweiterung, falls sie nicht bereits aktiv ist.')
        f.addRow(QLabel('Tipp: Für sehr lange Zeilen ist automatischer Umbruch meist besser ausgeschaltet.'))

        # Output and checking
        f = page('Prüfung & Output')
        output_lines = spin(f, 'Maximale Output-Zeilen', 'output_max_blocks', 1500, 100, 50000, ' Zeilen')
        output_height = spin(f, 'Start-Höhe des Output-Fensters', 'output_height', 180, 60, 1000, ' px')
        live_debounce = spin(f, 'Verzögerung der Live-Prüfung', 'live_check_delay', 400, 100, 3000, ' ms')
        clear_output = checkbox(f, 'Output vor einer neuen Prüfung leeren', 'clear_output_before_check', False)
        f.addRow(QLabel('Die Fenstergröße kann zusätzlich jederzeit per Dock-Drag angepasst werden.'))

        # Files
        f = page('Dateien & Projekte')
        extension = QComboBox(); extension.addItems(['.txt', '.payload', '.ducky', '.js', '.mjs']); extension.setCurrentText(self.settings.get('default_extension', '.txt'))
        f.addRow('Standard-Endung für neue Dateien', extension)
        directory = QLineEdit(str(self.settings.get('last_directory') or Path.cwd()))
        browse = QPushButton('Durchsuchen…')
        row = QHBoxLayout(); row.addWidget(directory, 1); row.addWidget(browse)
        f.addRow('Standard-Arbeitsverzeichnis', row)
        browse.clicked.connect(lambda: directory.setText(QFileDialog.getExistingDirectory(dlg, 'Arbeitsverzeichnis wählen', directory.text() or str(Path.cwd())) or directory.text()))
        recent_count = spin(f, 'Anzahl zuletzt verwendeter Projektordner', 'recent_folder_limit', 20, 1, 100)
        confirm_close = checkbox(f, 'Vor dem Schließen nach ungespeicherten Änderungen fragen', 'confirm_before_close', True)
        ask_overwrite = checkbox(f, 'Vor dem Überschreiben bestehender Dateien nachfragen', 'confirm_overwrite', True)
        reopen_files = checkbox(f, 'Zuletzt verwendeten Projektordner beim Start verwenden', 'restore_project_folder', True)

        # Ollama
        f = page('Ollama / KI')
        ollama_url = QLineEdit(self.settings.get('ollama_url', 'http://localhost:11434'))
        ollama_url.setPlaceholderText('http://192.168.x.x:11434')
        f.addRow('API-Adresse', ollama_url)
        ollama_model = QLineEdit(self.settings.get('ollama_model', ''))
        ollama_model.setPlaceholderText('z. B. qwen2.5-coder:3b')
        f.addRow('Bevorzugtes Modell', ollama_model)
        ollama_include = checkbox(f, 'Editorinhalt standardmäßig mitsenden', 'ollama_include_editor', True)
        ollama_timeout = spin(f, 'Timeout für KI-Anfragen', 'ollama_timeout', 90, 5, 600, ' Sekunden')
        ollama_context = spin(f, 'Maximale Anzahl Zeichen des Editor-Kontexts', 'ollama_context_chars', 12000, 1000, 100000, ' Zeichen')
        f.addRow(QLabel('Hinweis: Bei Ollama auf einem anderen Computer die LAN-IP und den API-Port verwenden.'))

        # Device / advanced
        f = page('Gerät & Erweitert')
        serial_timeout = spin(f, 'Serieller Lese-Timeout', 'serial_timeout', 4, 1, 30, ' Sekunden')
        serial_wait = spin(f, 'Wartezeit nach CLI-Befehlen', 'serial_wait_ms', 250, 0, 2000, ' ms')
        max_file_size = spin(f, 'Warnschwelle für große Payloads', 'large_file_warning_kb', 256, 16, 10240, ' KB')
        safe_mode = checkbox(f, 'Vor dem Senden einer Payload zusätzliche Bestätigung verlangen', 'confirm_before_send', True)
        debug_log = checkbox(f, 'Zusätzliche Diagnosemeldungen aktivieren', 'debug_logging', False)
        f.addRow(QLabel('Geräte-Timeouts und Diagnoseoptionen werden gespeichert. Nicht jede Option wird von jeder Firmware unterstützt.'))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.RestoreDefaults)
        buttons.setMinimumHeight(42)
        outer.addWidget(buttons)

        def restore_defaults():
            theme.setCurrentText('Flipper Amber'); font_family.setCurrentText('Consolas'); font_size.setValue(11); ui_scale.setValue(10)
            remember_size.setChecked(True); show_status.setChecked(True); restore_docks.setChecked(True); show_ollama.setChecked(False); show_output.setChecked(True); show_explorer.setChecked(True)
            autocomplete.setChecked(True); live.setChecked(True); word_wrap.setChecked(False); current_line.setChecked(True); spaces.setValue(4); indent_spaces.setChecked(True); auto_pair.setChecked(False)
            output_lines.setValue(1500); output_height.setValue(180); live_debounce.setValue(400); clear_output.setChecked(False)
            extension.setCurrentText('.txt'); directory.setText(str(Path.cwd())); recent_count.setValue(20); confirm_close.setChecked(True); ask_overwrite.setChecked(True); reopen_files.setChecked(True)
            ollama_url.setText('http://localhost:11434'); ollama_model.clear(); ollama_include.setChecked(True); ollama_timeout.setValue(90); ollama_context.setValue(12000)
            serial_timeout.setValue(4); serial_wait.setValue(250); max_file_size.setValue(256); safe_mode.setChecked(True); debug_log.setChecked(False)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(restore_defaults)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        for w in (theme, font_family, font_size, ui_scale, spaces, output_lines, output_height, live_debounce, extension, directory, recent_count, ollama_url, ollama_model, ollama_timeout, ollama_context, serial_timeout, serial_wait, max_file_size):
            w.setMinimumHeight(32)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        chosen_directory = directory.text().strip() or str(Path.cwd())
        self.settings.update({
            'font_size': font_size.value(), 'font_family': font_family.currentText().strip() or 'Consolas', 'ui_font_size': ui_scale.value(),
            'live_check': live.isChecked(), 'autocomplete': autocomplete.isChecked(), 'word_wrap': word_wrap.isChecked(),
            'highlight_current_line': current_line.isChecked(), 'tab_width': spaces.value(), 'insert_spaces': indent_spaces.isChecked(), 'auto_pairs': auto_pair.isChecked(),
            'show_output': show_output.isChecked(), 'output_height': output_height.value(), 'output_max_blocks': output_lines.value(),
            'live_check_delay': live_debounce.value(), 'clear_output_before_check': clear_output.isChecked(),
            'confirm_before_close': confirm_close.isChecked(), 'confirm_overwrite': ask_overwrite.isChecked(), 'restore_project_folder': reopen_files.isChecked(),
            'remember_window_size': remember_size.isChecked(), 'default_extension': extension.currentText(), 'last_directory': chosen_directory,
            'recent_folder_limit': recent_count.value(), 'show_status_bar': show_status.isChecked(), 'show_commands': restore_docks.isChecked(),
            'show_ollama': show_ollama.isChecked(), 'show_file_explorer': show_explorer.isChecked(),
            'ollama_url': ollama_url.text().strip() or 'http://localhost:11434', 'ollama_model': ollama_model.text().strip(),
            'ollama_include_editor': ollama_include.isChecked(), 'ollama_timeout': ollama_timeout.value(), 'ollama_context_chars': ollama_context.value(),
            'serial_timeout': serial_timeout.value(), 'serial_wait_ms': serial_wait.value(), 'large_file_warning_kb': max_file_size.value(),
            'confirm_before_send': safe_mode.isChecked(), 'debug_logging': debug_log.isChecked(),
        })
        if Path(chosen_directory).expanduser().is_dir():
            self.settings['recent_project_folder'] = str(Path(chosen_directory).expanduser().resolve())
            self.settings['project_folder_explicit'] = True
        self.change_theme(theme.currentText())
        self.apply_preferences()
        self.save_settings()
        self.update_working_directory()

    def about(self): QMessageBox.about(self,"Über BadUSB IDE", "BadUSB IDE für Flipper Zero\nPyQt6-Port mit Befehlsvorschlägen, USB-CLI, API-Referenz und Payload-Prüfung.\n\nNur auf eigenen oder autorisierten Geräten verwenden.")
    def closeEvent(self,event):
        # Do not close tabs one by one here: close_tab() intentionally creates a
        # fresh tab when the last tab is removed, which can prevent the window
        # from ever closing. Instead, resolve unsaved documents first and only
        # then allow the main window to shut down.
        for i in reversed(range(self.tabs.count())):
            editor = self.tabs.widget(i)
            doc = self.docs.get(editor)
            if not doc or not doc.dirty:
                continue
            if not self.settings.get('confirm_before_close', True):
                continue
            tab_name = self.tabs.tabText(i).lstrip('● ')
            answer = QMessageBox.question(
                self,
                "Ungespeicherte Änderungen",
                f"Änderungen in „{tab_name}“ speichern?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Save:
                self.tabs.setCurrentIndex(i)
                if not self.save_file():
                    # Includes cancelling the Save As dialog or a write error.
                    event.ignore()
                    return
        try:
            self.save_settings()
        except Exception:
            pass
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
        except Exception:
            pass
        event.accept()

def main():
    app=QApplication(sys.argv)
    app.setApplicationName("BadUSB IDE")
    win=BadUSBIDE()
    win.show()
    sys.exit(app.exec())
if __name__=='__main__': main()
