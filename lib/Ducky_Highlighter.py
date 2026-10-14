import re

from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

COMMANDS = {
    "REM", "DELAY", "STRING", "STRINGLN", "ALTSTRING", "GUI", "CTRL", "ALT", "SHIFT",
    "ENTER", "TAB", "SPACE", "ESC", "BACKSPACE", "DELETE", "PRINTSCREEN", "CAPSLOCK",
    "DOWN", "UP", "LEFT", "RIGHT", "HOME", "END", "INSERT", "PAGEUP", "PAGEDOWN",
    "REPEAT", "WAIT_FOR_BUTTON_PRESS", "HOLD", "ALTCHAR"
}
KEYS = {
    "ENTER", "TAB", "SPACE", "ESC", "BACKSPACE", "DELETE", "PRINTSCREEN", "CAPSLOCK",
    "DOWN", "UP", "LEFT", "RIGHT", "HOME", "END", "INSERT", "PAGEUP", "PAGEDOWN",
    "NUMLOCK", *[chr(i) for i in range(65, 91)], *[str(i) for i in range(10)]
}


class DuckyHighlighter(QSyntaxHighlighter):
    def __init__(self, doc, theme):
        super().__init__(doc)
        self.theme = theme

    def set_theme(self, theme):
        self.theme = theme
        self.rehighlight()

    def highlightBlock(self, text):
        t = self.theme

        def fmt(color, bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            f.setFontWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
            return f

        if text.lstrip().startswith(("REM", "#")):
            self.setFormat(0, len(text), fmt(t["comment"]))
            return

        m = re.match(r"\s*([A-Za-z_]+)", text)
        if m:
            cmd = m.group(1).upper()
            if cmd in COMMANDS or cmd in KEYS or cmd == "ID":
                self.setFormat(m.start(1), len(m.group(1)), fmt(t["accent"] if cmd in COMMANDS else t["key"], True))

        if re.match(r"\s*ID\b", text):
            m = re.match(r"\s*ID\b", text)
            self.setFormat(m.start(), len(m.group()), fmt("#c792ea", True))

        if re.match(r"\s*(STRING|STRINGLN|ALTSTRING)\s+", text, re.I):
            m = re.match(r"\s*(STRING|STRINGLN|ALTSTRING)\s+", text, re.I)
            self.setFormat(m.end(), len(text) - m.end(), fmt(t["string"]))