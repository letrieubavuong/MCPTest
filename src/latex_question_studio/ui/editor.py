from PySide6.QtCore import Qt, QRect, QSize, QStringListModel
from PySide6.QtGui import QSyntaxHighlighter,QTextCharFormat,QColor,QPainter,QTextCursor
from PySide6.QtWidgets import QPlainTextEdit,QWidget,QCompleter,QInputDialog
import re

class Highlighter(QSyntaxHighlighter):
    def highlightBlock(self,text):
        formats=[(r'\\[A-Za-z@]+','#569cd6'),(r'(?<!\\)%.*','#6a9955'),(r'\$[^$]*\$','#ce9178'),(r'[{}]','#dcdcaa')]
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
    def update_gutter_width(self,*args):self.setViewportMargins(self.gutter_width(),0,0,0)
    def update_gutter(self,rect,dy):
        if dy:self.gutter.scroll(0,dy)
        else:self.gutter.update(0,rect.y(),self.gutter.width(),rect.height())
        if rect.contains(self.viewport().rect()):self.update_gutter_width()
    def resizeEvent(self,event):
        super().resizeEvent(event);rect=self.contentsRect();self.gutter.setGeometry(QRect(rect.left(),rect.top(),self.gutter_width(),rect.height()))
    def paint_gutter(self,event):
        painter=QPainter(self.gutter);painter.fillRect(event.rect(),QColor('#252526'));painter.setPen(QColor('#858585'))
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
        super().keyPressEvent(event)

    def find_text(self):
        text,ok=QInputDialog.getText(self,'Tìm trong câu','Nội dung:')
        if ok and text:
            if not self.find(text):self.moveCursor(QTextCursor.MoveOperation.Start);self.find(text)
    def replace_text(self):
        before,ok=QInputDialog.getText(self,'Thay thế','Tìm:')
        if not ok or not before:return
        after,ok=QInputDialog.getText(self,'Thay thế','Thay bằng:')
        if ok:
            cursor=self.textCursor();cursor.beginEditBlock();cursor.select(QTextCursor.SelectionType.Document);cursor.insertText(self.toPlainText().replace(before,after));cursor.endEditBlock()
