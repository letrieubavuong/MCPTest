"""Theme tokens and application styling, kept outside page orchestration."""
from PySide6.QtGui import QPalette,QColor,QFont
from PySide6.QtWidgets import QApplication
TOKENS={
 'dark':dict(bg='#1e1e1e',panel='#252526',fg='#dedede',border='#3d3d40',muted='#a7a7ad',hover='#323237'),
 'light':dict(bg='#ffffff',panel='#f3f3f3',fg='#242424',border='#d6d6d9',muted='#606069',hover='#e5edf6')}
def apply(theme):
    t=TOKENS[theme];app=QApplication.instance();app.setStyle('Fusion');palette=QPalette()
    for role,color in [(QPalette.ColorRole.Window,t['bg']),(QPalette.ColorRole.Base,t['bg']),(QPalette.ColorRole.AlternateBase,t['panel']),(QPalette.ColorRole.Text,t['fg']),(QPalette.ColorRole.WindowText,t['fg']),(QPalette.ColorRole.Button,t['panel']),(QPalette.ColorRole.ButtonText,t['fg']),(QPalette.ColorRole.Highlight,'#007acc'),(QPalette.ColorRole.HighlightedText,'#ffffff')]:palette.setColor(role,QColor(color))
    palette.setColor(QPalette.ColorRole.PlaceholderText,QColor(t['muted']))
    palette.setColor(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Text,QColor(t['muted']));app.setPalette(palette);app.setFont(QFont('Segoe UI',10))
    app.setStyleSheet("""
      QToolBar {spacing:4px;padding:4px;border:0; background:PANEL;}
      QToolButton {padding:5px;border:1px solid transparent;border-radius:3px;}
      QToolButton:hover {background:HOVER;border-color:BORDER;}
      QToolButton[primary='true'], QPushButton[primary='true'] {background:#007acc;color:white;border:0;}
      QPushButton {padding:5px 10px;border:1px solid BORDER;border-radius:3px;background:PANEL;}
      QPushButton:disabled {color:MUTED;}
      QLineEdit,QComboBox,QSpinBox {padding:4px;min-height:20px;border:1px solid BORDER;}
      QPlainTextEdit {font-family:Consolas;font-size:14px;}
      QTreeView,QTableView,QListView {border:0;}
      QTreeView::item {height:25px;}
      QHeaderView::section {background:PANEL;padding:5px;border:0;border-bottom:1px solid BORDER;}
      QTabBar::tab {padding:7px 12px;background:PANEL;border-top:2px solid transparent;}
      QTabBar::tab:selected {border-top:2px solid #007acc;}
      QWidget#panelHeader,QWidget#activityBar {background:PANEL;}
      QListWidget#pageNavigation {background:PANEL;}
      QListWidget#pageNavigation::item {border-left:2px solid transparent;padding-left:7px;}
      QListWidget#pageNavigation::item:selected {background:HOVER;border-left:2px solid #007acc;}
      QStatusBar {background:#007acc;color:white;}
      QSplitter::handle {background:BORDER;}
    """.replace('PANEL',t['panel']).replace('HOVER',t['hover']).replace('BORDER',t['border']).replace('MUTED',t['muted']))
