"""Resizable, reusable desktop panels; no business logic."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QSplitter, QToolBar
from latex_question_studio.ui.icons import icon

class Panel(QWidget):
    def __init__(self, title, name, content, parent=None):
        super().__init__(parent); self.setObjectName(name)
        self.setMinimumWidth(0)
        box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0);box.setSpacing(0)
        header=QWidget();header.setObjectName('panelHeader');row=QHBoxLayout(header);row.setContentsMargins(10,5,6,5)
        row.addWidget(QLabel(title),1)
        close=QToolButton();close.setIcon(icon('close','#579bd4'));close.setToolTip('Ẩn '+title);close.clicked.connect(self.hide);row.addWidget(close)
        box.addWidget(header);box.addWidget(content,1)
        self.action=QAction(title,self);self.action.setCheckable(True);self.action.setChecked(True);self.action.triggered.connect(self.setVisible)
    def toggleViewAction(self):return self.action
    def isFloating(self):return False
    def showEvent(self,event):self.action.setChecked(True);super().showEvent(event)
    def hideEvent(self,event):self.action.setChecked(False);super().hideEvent(event)

class Workspace(QSplitter):
    def __init__(self,name,parent=None):
        super().__init__(Qt.Orientation.Horizontal,parent);self.setObjectName(name);self.setChildrenCollapsible(False);self.setHandleWidth(5)
    def state(self):return {'sizes':self.sizes(),'hidden':[w.isHidden() for w in (self.widget(i) for i in range(self.count()))]}
    def restore(self,state):
        sizes=state.get('sizes',[])
        if len(sizes)==self.count():self.setSizes(sizes)
        for i,hidden in enumerate(state.get('hidden',[])[:self.count()]):self.widget(i).setVisible(not hidden)

class CommandToolbar(QToolBar):
    def __init__(self,title,parent=None):
        super().__init__(title,parent);self.setObjectName('commandToolbar');self.setMovable(False);self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    def command(self,name,text,callback,primary=False):
        action=self.addAction(icon(name,'#579bd4'),text);action.setToolTip(text);action.triggered.connect(callback)
        if primary:
            button=self.widgetForAction(action);button.setProperty('primary',True);button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return action
