from PySide6.QtCore import Qt, QRect, QSize, QStringListModel
from PySide6.QtGui import QSyntaxHighlighter,QTextCharFormat,QColor,QPainter,QTextCursor
from PySide6.QtWidgets import (QPlainTextEdit,QWidget,QCompleter,QInputDialog,QHBoxLayout,
                             QLineEdit,QToolButton,QLabel,QFrame,QMenu)
import re

class Highlighter(QSyntaxHighlighter):
    def highlightBlock(self,text):
        colors=('#569cd6','#6a9955','#ce9178','#dcdcaa') if getattr(self,'theme','dark')=='dark' else ('#005ca9','#38752a','#994a14','#7a5500')
        formats=list(zip([r'\\[A-Za-z@]+',r'(?<!\\)%.*',r'\$[^$]*\$',r'[{}]'],colors))
        for pattern,color in formats:
            style=QTextCharFormat();style.setForeground(QColor(color))
            for match in re.finditer(pattern,text):self.setFormat(match.start(),match.end()-match.start(),style)

class Gutter(QWidget):
    def __init__(self,editor):super().__init__(editor);self.editor=editor
    def sizeHint(self):return QSize(self.editor.gutter_width(),0)
    def paintEvent(self,event):self.editor.paint_gutter(event)

class LatexEditor(QPlainTextEdit):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.theme='dark'

        # 1. Edit toolbar with common LaTeX question authoring tools
        self.edit_toolbar = QWidget(self)
        self.edit_toolbar.setObjectName('latexEditorToolbar')
        tb_layout = QHBoxLayout(self.edit_toolbar)
        tb_layout.setContentsMargins(4, 2, 4, 2)
        tb_layout.setSpacing(2)

        def add_btn(text, tooltip, callback, bold=False, italic=False):
            b = QToolButton(self.edit_toolbar)
            b.setText(text)
            b.setToolTip(tooltip)
            font = b.font()
            if bold: font.setBold(True)
            if italic: font.setItalic(True)
            b.setFont(font)
            b.clicked.connect(callback)
            tb_layout.addWidget(b)
            return b

        def add_sep():
            line = QFrame(self.edit_toolbar)
            line.setFrameShape(QFrame.Shape.VLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            line.setStyleSheet("color: #4b5563; margin: 3px 2px;")
            tb_layout.addWidget(line)

        # Formatting
        add_btn('B', 'In đậm (\\textbf{}) · Ctrl+B', lambda: self.wrap_selection(r'\textbf{', '}'), bold=True)
        add_btn('I', 'In nghiêng (\\textit{}) · Ctrl+I', lambda: self.wrap_selection(r'\textit{', '}'), italic=True)
        add_btn('U', 'Gạch chân (\\underline{}) · Ctrl+U', lambda: self.wrap_selection(r'\underline{', '}'))
        add_btn('$', 'Công thức toán inline ($...$)', lambda: self.wrap_selection('$', '$'))

        add_sep()

        # Math formulas
        add_btn('a/b', 'Phân số (\\dfrac{}{})', lambda: self.wrap_selection(r'\dfrac{', '}{}'))
        add_btn('√x', 'Căn thức (\\sqrt{})', lambda: self.wrap_selection(r'\sqrt{', '}'))
        add_btn('°C', 'Ký hiệu độ (^{\\circ}C)', lambda: self.insert_template(r'^{\circ}\text{C}'))

        add_sep()

        # Question structure
        add_btn('[A/B/C/D]', 'Chèn 4 phương án trắc nghiệm (\\choice)', lambda: self.insert_template(
            "\\choice\n{Phương án A}\n{Phương án B}\n{Phương án C}\n{Phương án D}"
        ))
        add_btn('✓ True', 'Đánh dấu phương án đúng (\\True)', lambda: self.insert_template(r'\True '))
        add_btn('[Đúng/Sai]', 'Chèn 4 ý Đúng / Sai (\\choiceTF)', lambda: self.insert_template(
            "\\choiceTF\n{Ý a}\n{Ý b}\n{Ý c}\n{Ý d}"
        ))
        add_btn('[Đáp số]', 'Đáp án trả lời ngắn (\\shortans{})', lambda: self.wrap_selection(r'\shortans{', '}'))
        add_btn('💡 Lời giải', 'Chèn lời giải chi tiết (\\loigiai{})', lambda: self.wrap_selection(r'\loigiai{' + '\n', '\n}'))

        add_sep()

        # More environments menu
        more_btn = QToolButton(self.edit_toolbar)
        more_btn.setText('Môi trường ▾')
        more_btn.setToolTip('Chèn môi trường LaTeX hay dùng')
        env_menu = QMenu(more_btn)
        env_menu.addAction('Môi trường câu hỏi (ex)', lambda: self.wrap_selection("\\begin{ex}\n", "\n\\loigiai{}\n\\end{ex}"))
        env_menu.addAction('Danh sách gạch đầu dòng (itemize)', lambda: self.wrap_selection("\\begin{itemize}\n\\item ", "\n\\end{itemize}"))
        env_menu.addAction('Danh sách đánh số (enumerate)', lambda: self.wrap_selection("\\begin{enumerate}\n\\item ", "\n\\end{enumerate}"))
        env_menu.addAction('Véc tơ (\\vec{})', lambda: self.wrap_selection(r'\vec{', '}'))
        env_menu.addAction('Góc (\\widehat{})', lambda: self.wrap_selection(r'\widehat{', '}'))
        env_menu.addAction('Chèn hình ảnh (\\includegraphics{})', lambda: self.wrap_selection(r'\includegraphics[width=0.5\linewidth]{', '}'))
        more_btn.setMenu(env_menu)
        more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        tb_layout.addWidget(more_btn)

        add_sep()

        # Undo, Redo, Find
        add_btn('↶', 'Hoàn tác (Ctrl+Z)', self.undo)
        add_btn('↷', 'Làm lại (Ctrl+Y)', self.redo)
        add_btn('🔍', 'Tìm kiếm & Thay thế (Ctrl+F)', self.find_text)

        tb_layout.addStretch(1)

        # 2. Find and replace bar
        self.findbar=QWidget(self);self.findbar.hide()
        row=QHBoxLayout(self.findbar);row.setContentsMargins(4,2,4,2)
        self.find_input=QLineEdit();self.find_input.setPlaceholderText('Tìm nội dung');row.addWidget(self.find_input)
        self.replace_input=QLineEdit();self.replace_input.setPlaceholderText('Thay bằng');row.addWidget(self.replace_input)
        self.find_feedback=QLabel();row.addWidget(self.find_feedback)
        for text,tip,callback in [('↓','Tìm tiếp',self.find_next),('Thay','Thay một kết quả',self.replace_one),('Tất cả','Thay tất cả',self.replace_all),('×','Đóng tìm kiếm',self.hide_find)]:
            button=QToolButton();button.setText(text);button.setToolTip(tip);button.clicked.connect(callback);row.addWidget(button)
        self.find_input.returnPressed.connect(self.find_next)
        self.highlighter=Highlighter(self.document())
        self.gutter=Gutter(self)
        self.blockCountChanged.connect(self.update_gutter_width)
        self.updateRequest.connect(self.update_gutter)
        self.update_gutter_width()
        self.update_toolbar_style()
        self.completer=QCompleter(['\\choice','\\choiceTF','\\choiceTFt','\\shortans','\\loigiai','\\includegraphics','\\begin{ex}','\\end{ex}','\\True'],self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self.complete_macro)

    def wrap_selection(self, prefix, suffix=""):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            cursor.insertText(prefix + selected + suffix)
        else:
            pos = cursor.position()
            cursor.insertText(prefix + suffix)
            cursor.setPosition(pos + len(prefix))
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.setFocus()

    def insert_template(self, text):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.insertText(text)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.setFocus()

    def update_toolbar_style(self):
        if not hasattr(self, 'edit_toolbar'): return
        if self.theme == 'dark':
            self.edit_toolbar.setStyleSheet("""
                QWidget#latexEditorToolbar {
                    background-color: #1e1e24;
                    border-bottom: 1px solid #2d2d38;
                }
                QToolButton {
                    background: transparent;
                    color: #cbd5e1;
                    border: 1px solid transparent;
                    border-radius: 3px;
                    padding: 2px 5px;
                    font-size: 11px;
                }
                QToolButton:hover {
                    background: #2d3748;
                    border-color: #4b5563;
                    color: #f8fafc;
                }
                QToolButton:pressed {
                    background: #4a5568;
                }
            """)
        else:
            self.edit_toolbar.setStyleSheet("""
                QWidget#latexEditorToolbar {
                    background-color: #f1f5f9;
                    border-bottom: 1px solid #cbd5e1;
                }
                QToolButton {
                    background: transparent;
                    color: #334155;
                    border: 1px solid transparent;
                    border-radius: 3px;
                    padding: 2px 5px;
                    font-size: 11px;
                }
                QToolButton:hover {
                    background: #e2e8f0;
                    border-color: #94a3b8;
                    color: #0f172a;
                }
                QToolButton:pressed {
                    background: #cbd5e1;
                }
            """)

    def gutter_width(self):return 16+self.fontMetrics().horizontalAdvance('9')*len(str(max(1,self.blockCount())))
    def update_gutter_width(self,*args):
        tb_h = 32 if hasattr(self, 'edit_toolbar') and self.edit_toolbar.isVisible() else 0
        fb_h = 36 if hasattr(self, 'findbar') and self.findbar.isVisible() else 0
        self.setViewportMargins(self.gutter_width(), tb_h + fb_h, 0, 0)

    def update_gutter(self,rect,dy):
        if dy:self.gutter.scroll(0,dy)
        else:self.gutter.update(0,rect.y(),self.gutter.width(),rect.height())
        if rect.contains(self.viewport().rect()):self.update_gutter_width()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        rect=self.contentsRect()
        tb_h = 32 if hasattr(self, 'edit_toolbar') and self.edit_toolbar.isVisible() else 0
        fb_h = 36 if hasattr(self, 'findbar') and self.findbar.isVisible() else 0
        if hasattr(self, 'edit_toolbar'):
            self.edit_toolbar.setGeometry(0, 0, self.width(), tb_h)
        if hasattr(self, 'findbar'):
            self.findbar.setGeometry(0, tb_h, self.width(), fb_h)
        top_offset = tb_h + fb_h
        self.gutter.setGeometry(QRect(rect.left(), rect.top() + top_offset, self.gutter_width(), rect.height() - top_offset))

    def paint_gutter(self,event):
        painter=QPainter(self.gutter);painter.fillRect(event.rect(),QColor('#252526' if self.theme=='dark' else '#f3f3f3'));painter.setPen(QColor('#858585' if self.theme=='dark' else '#606069'))
        block=self.firstVisibleBlock();number=block.blockNumber();top=int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        while block.isValid() and top<=event.rect().bottom():
            height=int(self.blockBoundingRect(block).height())
            if block.isVisible():painter.drawText(0,top,self.gutter.width()-6,self.fontMetrics().height(),Qt.AlignmentFlag.AlignRight,str(number+1))
            top+=height;block=block.next();number+=1
    def complete_macro(self,value):
        cursor=self.textCursor();cursor.movePosition(QTextCursor.MoveOperation.StartOfWord,QTextCursor.MoveMode.KeepAnchor)
        if cursor.position()>0 and self.toPlainText()[cursor.position()-1:cursor.position()]=='\\':cursor.movePosition(QTextCursor.MoveOperation.Left,QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(value);self.setTextCursor(cursor)
    def keyPressEvent(self,event):
        if self.completer.popup().isVisible() and event.key() in (Qt.Key.Key_Enter,Qt.Key.Key_Return,Qt.Key.Key_Escape,Qt.Key.Key_Tab):event.ignore();return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key()==Qt.Key.Key_B:
                self.wrap_selection(r'\textbf{', '}');return
            if event.key()==Qt.Key.Key_I:
                self.wrap_selection(r'\textit{', '}');return
            if event.key()==Qt.Key.Key_U:
                self.wrap_selection(r'\underline{', '}');return
            if event.key()==Qt.Key.Key_Space:
                cursor=self.textCursor();cursor.select(QTextCursor.SelectionType.WordUnderCursor)
                self.completer.setCompletionPrefix('\\'+cursor.selectedText());self.completer.complete(self.cursorRect());return
        if event.key()==Qt.Key.Key_Tab:
            self.insertPlainText('    ');return
        indent=re.match(r'\s*',self.textCursor().block().text()).group(0) if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) else ''
        super().keyPressEvent(event)
        if indent:self.insertPlainText(indent)

    def set_theme(self,theme):
        self.theme=theme;self.gutter.update()
        self.update_toolbar_style()
        modified=self.document().isModified();previous=self.blockSignals(True)
        self.highlighter.theme=theme;self.highlighter.rehighlight();self.document().setModified(modified);self.blockSignals(previous)
    def find_text(self):
        self.findbar.show();self.replace_input.hide();self.update_gutter_width();self.findbar.setGeometry(0,0,self.width(),38);self.find_input.setFocus()
    def replace_text(self):
        self.find_text();self.replace_input.show()
    def hide_find(self):
        self.findbar.hide();self.update_gutter_width();self.setFocus()
    def find_next(self):
        text=self.find_input.text()
        if not text:return False
        found=self.find(text)
        if not found:self.moveCursor(QTextCursor.MoveOperation.Start);found=self.find(text)
        self.find_feedback.setText('' if found else 'Không thấy');return found
    def replace_one(self):
        cursor=self.textCursor()
        if cursor.selectedText()!=self.find_input.text() and not self.find_next():return
        cursor=self.textCursor();cursor.insertText(self.replace_input.text());self.find_next()
    def replace_all(self):
        text=self.find_input.text()
        if not text:return
        source=self.toPlainText();count=source.count(text);cursor=self.textCursor();cursor.beginEditBlock();cursor.select(QTextCursor.SelectionType.Document);cursor.insertText(source.replace(text,self.replace_input.text()));cursor.endEditBlock();self.find_feedback.setText(f'{count} kết quả')
