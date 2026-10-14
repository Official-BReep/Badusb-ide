import re

from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class JavaScriptHighlighter(QSyntaxHighlighter):
    """Expanded syntax highlighting for JavaScript and Flipper mJS."""
    KEYWORDS = set("let const var function return if else for while do break continue switch case default try catch finally throw new delete typeof void in of this true false null undefined async await class extends import export from as yield instanceof static super".split())
    BUILTINS = set("print delay require parseInt parseFloat JSON Math Object Array String Number Boolean Promise Date Error RegExp Map Set Symbol BigInt checkSdkFeatures doesSdkSupport load".split())
    MODULES = set("badusb storage event_loop flipper gpio gui math notification serial i2c spi subghz blebeacon vgm widget usbdisk".split())

    def __init__(self, doc, theme):
        super().__init__(doc)
        self.theme = theme

    def set_theme(self, theme):
        self.theme = theme
        self.rehighlight()

    def highlightBlock(self, text):
        t = self.theme

        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            if italic:
                f.setFontItalic(True)
            return f

        comment = fmt(t.get("comment", "#6a9955"), italic=True)
        string_fmt = fmt(t.get("string", "#ce9178"))
        keyword_fmt = fmt("#c792ea", True)
        builtin_fmt = fmt(t.get("accent", "#ffb454"), True)
        module_fmt = fmt("#82aaff", True)
        number_fmt = fmt("#b5cea8")
        operator_fmt = fmt("#89ddff")
        in_block = self.previousBlockState() == 1
        i = 0
        while i < len(text):
            if in_block:
                end = text.find("*/", i)
                if end < 0:
                    self.setFormat(i, len(text) - i, comment)
                    self.setCurrentBlockState(1)
                    return
                self.setFormat(i, end + 2 - i, comment)
                i = end + 2
                in_block = False
                continue
            if text.startswith("//", i):
                self.setFormat(i, len(text) - i, comment)
                break
            if text.startswith("/*", i):
                end = text.find("*/", i + 2)
                if end < 0:
                    self.setFormat(i, len(text) - i, comment)
                    in_block = True
                    self.setCurrentBlockState(1)
                    break
                self.setFormat(i, end + 2 - i, comment)
                i = end + 2
                continue
            if text[i] in "\"'`":
                quote = text[i]
                j = i + 1
                escaped = False
                while j < len(text):
                    ch = text[j]
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == quote:
                        j += 1
                        break
                    j += 1
                self.setFormat(i, j - i, string_fmt)
                i = j
                continue
            number = re.match(r"(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", text[i:])
            if number:
                self.setFormat(i, len(number.group()), number_fmt)
                i += len(number.group())
                continue
            ident = re.match(r"[A-Za-z_$][\w$]*", text[i:])
            if ident:
                word = ident.group()
                end = i + len(word)
                if word in self.KEYWORDS:
                    self.setFormat(i, len(word), keyword_fmt)
                elif word in self.BUILTINS:
                    self.setFormat(i, len(word), builtin_fmt)
                elif word in self.MODULES:
                    self.setFormat(i, len(word), module_fmt)
                elif re.match(r"\s*\(", text[end:]):
                    self.setFormat(i, len(word), fmt("#82aaff"))
                i = end
                continue
            if text[i] in "=+-*/%<>!&|^~?:":
                self.setFormat(i, 1, operator_fmt)
            elif text[i] in "(){}[];.,":
                self.setFormat(i, 1, fmt("#89ddff", True))
            i += 1
        self.setCurrentBlockState(1 if in_block else 0)