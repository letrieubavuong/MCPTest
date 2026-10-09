from PySide6.QtCore import Qt, QRect, QSize, QStringListModel
from PySide6.QtGui import QSyntaxHighlighter,QTextCharFormat,QColor,QPainter,QTextCursor
from PySide6.QtWidgets import QPlainTextEdit,QWidget,QCompleter,QInputDialog,QHBoxLayout,QLineEdit,QToolButton,QLabel
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
        self.theme='dark';self.findbar=QWidget(self);self.findbar.hide()
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
        self.completer=QCompleter(['\\choice','\\choiceTF','\\choiceTFt','\\shortans','\\loigiai','\\includegraphics','\\begin{ex}','\\end{ex}','\\True'],self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self.complete_macro)

    def gutter_width(self):return 16+self.fontMetrics().horizontalAdvance('9')*len(str(max(1,self.blockCount())))
    def update_gutter_width(self,*args):self.setViewportMargins(self.gutter_width(),38 if self.findbar.isVisible() else 0,0,0)
    def update_gutter(self,rect,dy):
        if dy:self.gutter.scroll(0,dy)
        else:self.gutter.update(0,rect.y(),self.gutter.width(),rect.height())
        if rect.contains(self.viewport().rect()):self.update_gutter_width()
    def resizeEvent(self,event):
        super().resizeEvent(event);rect=self.contentsRect();self.gutter.setGeometry(QRect(rect.left(),rect.top()+self.viewportMargins().top(),self.gutter_width(),rect.height()-self.viewportMargins().top()));self.findbar.setGeometry(0,0,self.width(),38)
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
        if event.key()==Qt.Key.Key_Space and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            cursor=self.textCursor();cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            self.completer.setCompletionPrefix('\\'+cursor.selectedText());self.completer.complete(self.cursorRect());return
        if event.key()==Qt.Key.Key_Tab:
            self.insertPlainText('    ');return
        indent=re.match(r'\s*',self.textCursor().block().text()).group(0) if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) else ''
        super().keyPressEvent(event)
        if indent:self.insertPlainText(indent)

    def set_theme(self,theme):
        self.theme=theme;self.gutter.update()
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
