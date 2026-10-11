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
      QToolButton#shellTool {min-width:40px;max-width:40px;min-height:40px;max-height:40px;padding:7px;border-radius:7px;}
      QToolButton#shellTool:checked {background:#dceffc;border:1px solid #a8d2f2;}
      QToolButton:checked {background:#dceffc;border-left:2px solid #1688d8;}
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
      QListWidget#pageNavigation::item {border-left:3px solid transparent;padding-left:8px;padding-right:8px;border-radius:7px;margin:1px 4px;}
      QListWidget#pageNavigation::item:selected {background:HOVER;border-left:3px solid #1677d2;}
      QStatusBar {background:#007acc;color:white;}
      QSplitter::handle {background:BORDER;}
      QFrame#dashboardMetric,QFrame#dashboardPanel {background:PANEL;border:1px solid BORDER;border-radius:5px;}
      QFrame#dashboardMetric {border-left:3px solid #1677d2;}
      QLabel#dashboardTitle {font-size:20px;font-weight:600;}
      QLabel#dashboardEyebrow {font-size:10px;font-weight:700;color:#1677d2;letter-spacing:1px;}
      QLabel#dashboardSubtitle,QLabel#metricDetail,QLabel#chartLegend {color:MUTED;}
      QLabel#dashboardClock {color:MUTED;font-size:11px;}
      QLabel#metricTitle {color:MUTED;font-size:11px;}
      QLabel#metricValue {font-size:24px;font-weight:600;color:#1688d8;}
      QLabel#panelTitle {font-size:13px;font-weight:600;color:FG;}
      QLabel#panelSubtitle {color:MUTED;font-size:10px;}
      QLabel#assetLegend {color:FG;font-size:11px;}
      QLabel#dashboardEmpty {color:MUTED;padding:28px 8px;}
      QLabel#activityTime {color:MUTED;font-size:11px;}
      QLabel#activityLabel {color:FG;font-size:11px;}
      QLabel#activityDot {color:#16a085;font-size:13px;}
      QFrame#dashboardActivityRow {border-bottom:1px solid BORDER;}
      QPushButton[dashboardAction='true'] {text-align:left;padding:8px 10px;min-height:30px;}
      QScrollArea#dashboardScroll {background:BASE;}
      QFrame#dashboardPanel QListWidget {border:0;background:transparent;}
      QListWidget#importSteps {background:PANEL;border:1px solid BORDER;border-radius:5px;padding:4px;}
      QListWidget#importSteps::item {padding:10px 6px;margin:2px 0;border-radius:4px;color:MUTED;}
      QListWidget#importSteps::item:selected {background:#dceffc;color:#123b5d;border-left:3px solid #1688d8;}
      QLabel#importSourcePath {padding:10px;border:1px solid BORDER;background:PANEL;}
      QFrame#importStat {background:PANEL;border:1px solid BORDER;border-radius:4px;}
      QLabel#importStatValue {font-size:20px;font-weight:600;color:#1688d8;}
      QLabel#importStatLabel {color:MUTED;font-size:10px;}
      QListWidget#questionCards {background:BASE;border:0;}
      QFrame#questionCard {background:PANEL;border:1px solid BORDER;border-radius:5px;}
      QFrame#questionCard:hover {border:1px solid #1688d8;}
      QLabel#cardTitle {font-weight:600;color:FG;}
      QLabel#cardBadge {color:#1688d8;font-size:10px;}
      QLabel#cardPreview {color:FG;padding:4px;}
      QLabel#cardFooter {color:MUTED;font-size:9px;}
      QTabWidget#lessonTabs::pane {border:1px solid BORDER;}
      QTabWidget#lessonTabs QPlainTextEdit {background:BASE;}
      QTextEdit#wysiwygEditor {background:BASE;color:FG;border:1px solid BORDER;}
      QListWidget#examSteps {background:PANEL;border:1px solid BORDER;border-radius:5px;padding:4px;}
      QListWidget#examSteps::item {padding:12px 6px;margin:2px 0;border-radius:4px;color:MUTED;}
      QListWidget#examSteps::item:selected {background:#dceffc;color:#123b5d;border-left:3px solid #1688d8;}
    """.replace('PANEL',t['panel']).replace('BASE',t['bg']).replace('HOVER',t['hover']).replace('BORDER',t['border']).replace('MUTED',t['muted']).replace('FG',t['fg']))
