import re

from PyQt6.QtCore import QPoint, QRect, Qt, QSize
from PyQt6.QtGui import QColor, QPainter, QTextCursor, QTextFormat
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget

from lib.shared_data import COMMANDS, JS_GLOBALS, JS_METHODS, JS_MODULES, KEYS, STANDALONE
from lib.Ducky_Highlighter import DuckyHighlighter
from lib.js_highlighter import JavaScriptHighlighter


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)


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
        self._wheel_selection_anchor=None
        self._middle_drag_active=False
        self._middle_drag_start=None
        self._middle_drag_positions=[]
        # Lightweight VS Code-style multi-cursor support.
        self._extra_cursor_positions=[]
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
        # Draw secondary cursors as narrow highlighted insertion points.
        for pos in getattr(self, '_extra_cursor_positions', []):
            try:
                extra=QTextEdit.ExtraSelection()
                extra.cursor=QTextCursor(self.document())
                extra.cursor.setPosition(max(0, min(pos, self.document().characterCount()-1)))
                extra.format.setBackground(QColor(self.theme_getter()['accent']))
                extra.format.setProperty(QTextFormat.Property.FullWidthSelection, False)
                selections.append(extra)
            except Exception:
                pass
        self.setExtraSelections(selections)

    def clear_extra_cursors(self):
        self._extra_cursor_positions=[]
        self.highlight_current_line()

    def _add_cursor_on_adjacent_line(self, direction):
        cur=self.textCursor()
        block=cur.block().next() if direction > 0 else cur.block().previous()
        if not block.isValid():
            return
        col=cur.positionInBlock()
        pos=block.position()+min(col, len(block.text()))
        if pos != cur.position() and pos not in self._extra_cursor_positions:
            self._extra_cursor_positions.append(pos)
            self._extra_cursor_positions.sort()
            self.highlight_current_line()

    def _apply_to_all_cursors(self, text=None, backspace=False, delete=False):
        positions=list(self._extra_cursor_positions)+[self.textCursor().position()]
        positions=sorted(set(positions), reverse=True)
        doc=self.document()
        cur=self.textCursor()
        original=cur.position()
        doc_cursor=QTextCursor(doc)
        doc_cursor.beginEditBlock()
        new_positions=[]
        for pos in positions:
            c=QTextCursor(doc); c.setPosition(pos)
            if backspace and pos > 0:
                c.deletePreviousChar(); new_positions.append(pos-1)
            elif delete and pos < doc.characterCount()-1:
                c.deleteChar(); new_positions.append(pos)
            elif text is not None:
                c.insertText(text); new_positions.append(pos+len(text))
            else:
                new_positions.append(pos)
        doc_cursor.endEditBlock()
        # Keep the original/main cursor active and retain the other insertion points.
        mapped=[]
        for pos in new_positions:
            shift=sum((len(text) if text is not None else (-1 if backspace else 0)) for p0 in positions if p0 < pos) if text is not None or backspace else 0
            mapped.append(max(0, min(pos+shift, doc.characterCount()-1)))
        if len(mapped) > 1:
            self._extra_cursor_positions=mapped[:-1]
        else:
            self._extra_cursor_positions=[]
        main=QTextCursor(doc); main.setPosition(max(0,min(original,doc.characterCount()-1)))
        self.setTextCursor(main)
        self.highlight_current_line()
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

    def wheelEvent(self, event):
        # Alt + mouse wheel extends a line-wise selection, useful for editing/commenting
        # several adjacent lines without losing the original anchor.
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            delta = event.angleDelta().y()
            if delta:
                cur = self.textCursor()
                if self._wheel_selection_anchor is None:
                    self._wheel_selection_anchor = cur.position()
                steps = max(1, abs(delta) // 120)
                cur.setPosition(self._wheel_selection_anchor)
                direction = QTextCursor.MoveOperation.Up if delta > 0 else QTextCursor.MoveOperation.Down
                cur.movePosition(direction, QTextCursor.MoveMode.KeepAnchor, steps)
                self.setTextCursor(cur)
                event.accept()
                return
        else:
            self._wheel_selection_anchor = None
        super().wheelEvent(event)

    def _cursor_position_at_viewport_point(self, point):
        """Return a text insertion position for a viewport-local mouse point."""
        cursor = self.cursorForPosition(point)
        return cursor.position()

    def _set_middle_drag_cursors(self, start_point, end_point):
        """Create insertion points on each line crossed by a middle-button drag.

        Keep this handler defensive: mouse events can arrive at viewport edges and
        Qt may invalidate blocks while the document is being edited.
        """
        try:
            start_cursor = self.cursorForPosition(start_point)
            end_cursor = self.cursorForPosition(end_point)
            first_line = start_cursor.blockNumber()
            last_line = end_cursor.blockNumber()
            low, high = sorted((first_line, last_line))
            x = end_point.x()
            positions = []
            for line_number in range(low, high + 1):
                block = self.document().findBlockByNumber(line_number)
                if not block.isValid():
                    continue
                probe = QTextCursor(block)
                probe.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                y = self.cursorRect(probe).center().y()
                pos = self.cursorForPosition(QPoint(x, y)).position()
                # Clamp to the actual line so the same x-coordinate never
                # accidentally resolves to an adjacent line at a wrapped edge.
                pos = max(block.position(), min(pos, block.position() + len(block.text())))
                if pos not in positions:
                    positions.append(pos)
            if not positions:
                return
            # The main cursor is a real Qt cursor; the remaining cursors are
            # painted as extra selections and applied together while typing.
            main = QTextCursor(self.document())
            main.setPosition(positions[-1])
            self.setTextCursor(main)
            self._extra_cursor_positions = sorted(set(positions[:-1]))
            self._middle_drag_positions = positions
            self.highlight_current_line()
        except (RuntimeError, TypeError, ValueError, AttributeError):
            # Never let a transient mouse-coordinate/document state crash the IDE.
            self._middle_drag_active = False
            self._extra_cursor_positions = []
            self.highlight_current_line()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            # Do not invoke QPlainTextEdit's default middle-click paste behavior.
            self._middle_drag_active = True
            self._middle_drag_start = event.position().toPoint()
            self._middle_drag_positions = []
            event.accept()
            return
        if not (event.modifiers() & Qt.KeyboardModifier.AltModifier):
            self._extra_cursor_positions = []
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._middle_drag_active and (event.buttons() & Qt.MouseButton.MiddleButton):
            self._set_middle_drag_cursors(self._middle_drag_start, event.position().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton and self._middle_drag_active:
            end_point = event.position().toPoint()
            if end_point != self._middle_drag_start:
                self._set_middle_drag_cursors(self._middle_drag_start, end_point)
            else:
                # A plain middle click should only move the caret; it should not
                # create a multi-cursor or paste the clipboard.
                try:
                    cursor = self.cursorForPosition(end_point)
                    self.setTextCursor(cursor)
                    self._extra_cursor_positions = []
                    self.highlight_current_line()
                except (RuntimeError, TypeError, ValueError, AttributeError):
                    pass
            self._middle_drag_active = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Alt:
            self._wheel_selection_anchor = None
        super().keyReleaseEvent(event)

    def keyPressEvent(self, event):
        # Ctrl+Alt+Up/Down adds a cursor on the neighbouring line (VS Code convention).
        mods=event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier and mods & Qt.KeyboardModifier.AltModifier and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self._add_cursor_on_adjacent_line(-1 if event.key() == Qt.Key.Key_Up else 1)
            event.accept(); return
        if event.key() == Qt.Key.Key_Escape and self._extra_cursor_positions:
            self.clear_extra_cursors(); event.accept(); return
        if self._extra_cursor_positions and not (mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)):
            if event.key() == Qt.Key.Key_Backspace:
                self._apply_to_all_cursors(backspace=True); event.accept(); return
            if event.key() == Qt.Key.Key_Delete:
                self._apply_to_all_cursors(delete=True); event.accept(); return
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._apply_to_all_cursors(text='\n'); event.accept(); return
            if event.text() and event.text().isprintable():
                self._apply_to_all_cursors(text=event.text()); event.accept(); return
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