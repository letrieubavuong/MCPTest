"""Application shell shared by all workspaces."""
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QListWidget,QStackedWidget,QToolButton
from latex_question_studio.ui.icons import icon

class ApplicationShell(QWidget):
    home_clicked = Signal()
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName('applicationShell')
        layout=QHBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.activity=QWidget();self.activity.setObjectName('activityBar');self.activity.setFixedWidth(64)
        box=QVBoxLayout(self.activity);box.setContentsMargins(4,6,4,6);box.setSpacing(6)
        self.toggle=QToolButton();self.toggle.setObjectName('shellTool');self.toggle.setIcon(icon('chapter','#6d8aa6'));self.toggle.setToolTip('Thu / mở cây điều hướng');box.addWidget(self.toggle)
        self.home=QToolButton();self.home.setObjectName('shellTool');self.home.setCheckable(True);self.home.setIcon(icon('home','#6d8aa6'));self.home.setToolTip('Trang chủ Dashboard');self.home.clicked.connect(self.home_clicked.emit);box.addWidget(self.home)
        self.navigation=QListWidget();self.navigation.setObjectName('pageNavigation');self.navigation.setIconSize(QSize(25,25));self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for title,name in [('CSDL (Ctrl+1)','bank'),('Nhập câu hỏi (Ctrl+I)','import'),('Ra đề thi','exam'),('Cài đặt','settings'),('Bài giảng (Ctrl+L / Ctrl+4)','lesson'),('Câu hỏi trùng (Ctrl+D)','dedup'),('Thu thập từ Web (Ctrl+W)','web')]:
            self.navigation.addItem('');item=self.navigation.item(self.navigation.count()-1);item.setIcon(icon(name,'#6d8aa6'));item.setToolTip(title);item.setData(Qt.ItemDataRole.AccessibleTextRole,title);item.setSizeHint(QSize(52,48))
        box.addWidget(self.navigation,1)
        self.pages=QStackedWidget();self.pages.setObjectName('pageContent');layout.addWidget(self.activity);layout.addWidget(self.pages,1)

    def set_navigation_icons(self, theme, active_index=None, home_active=False):
        colors = {'light': ('#1677d2', '#6d8aa6'), 'dark': ('#58a6ff', '#a6b4c3')}
        active, muted = colors.get(theme, colors['light'])
        names = ('bank', 'import', 'exam', 'settings', 'lesson', 'dedup', 'web')
        for index, name in enumerate(names):
            if index < self.navigation.count():
                self.navigation.item(index).setIcon(icon(name, active if index == active_index else muted))
        self.home.setIcon(icon('home', active if home_active else muted))
        self.toggle.setIcon(icon('chapter', muted))
