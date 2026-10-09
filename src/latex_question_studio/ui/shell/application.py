"""Application shell shared by all workspaces."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QListWidget,QStackedWidget,QToolButton
from latex_question_studio.ui.icons import icon

class ApplicationShell(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName('applicationShell')
        layout=QHBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.activity=QWidget();self.activity.setObjectName('activityBar');self.activity.setFixedWidth(64)
        box=QVBoxLayout(self.activity);box.setContentsMargins(4,6,4,6);box.setSpacing(6)
        self.toggle=QToolButton();self.toggle.setIcon(icon('chapter','#579bd4'));self.toggle.setToolTip('Thu / mở cây điều hướng');box.addWidget(self.toggle)
        self.navigation=QListWidget();self.navigation.setObjectName('pageNavigation');self.navigation.setIconSize(QSize(25,25));self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for title,name in [('CSDL','bank'),('Nhập câu hỏi','import'),('Ra đề thi','exam'),('Cài đặt','settings'),('Bài giảng','lesson')]:
            self.navigation.addItem('');item=self.navigation.item(self.navigation.count()-1);item.setIcon(icon(name,'#579bd4'));item.setToolTip(title);item.setData(Qt.ItemDataRole.AccessibleTextRole,title);item.setSizeHint(QSize(48,50))
        box.addWidget(self.navigation,1)
        self.pages=QStackedWidget();self.pages.setObjectName('pageContent');layout.addWidget(self.activity);layout.addWidget(self.pages,1)
