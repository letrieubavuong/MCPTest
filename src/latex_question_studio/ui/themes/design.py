"""Theme tokens and application styling, kept outside page orchestration."""
from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtWidgets import QApplication

TOKENS = {
    'dark': dict(
        bg='#18181b',
        panel='#202024',
        card='#27272a',
        fg='#f4f4f5',
        border='#38383e',
        muted='#909098',
        hover='#2e2e34',
        accent='#3b82f6',
        accent_hover='#2563eb',
        status_bg='#18181b',
        status_fg='#a1a1aa',
        nb_bg='#064e3b', nb_fg='#34d399',
        th_bg='#1e3a8a', th_fg='#60a5fa',
        vd_bg='#713f12', vd_fg='#facc15',
        vdc_bg='#7f1d1d', vdc_fg='#f87171',
    ),
    'light': dict(
        bg='#f8fafc',
        panel='#f1f5f9',
        card='#ffffff',
        fg='#0f172a',
        border='#e2e8f0',
        muted='#64748b',
        hover='#e2e8f0',
        accent='#2563eb',
        accent_hover='#1d4ed8',
        status_bg='#f1f5f9',
        status_fg='#475569',
        nb_bg='#d1fae5', nb_fg='#065f46',
        th_bg='#dbeafe', th_fg='#1e40af',
        vd_bg='#fef3c7', vd_fg='#854d0e',
        vdc_bg='#fee2e2', vdc_fg='#991b1b',
    ),
}

def apply(theme):
    t = TOKENS[theme]
    app = QApplication.instance()
    app.setStyle('Fusion')
    palette = QPalette()
    for role, color in [
        (QPalette.ColorRole.Window, t['bg']),
        (QPalette.ColorRole.Base, t['card']),
        (QPalette.ColorRole.AlternateBase, t['panel']),
        (QPalette.ColorRole.Text, t['fg']),
        (QPalette.ColorRole.WindowText, t['fg']),
        (QPalette.ColorRole.Button, t['panel']),
        (QPalette.ColorRole.ButtonText, t['fg']),
        (QPalette.ColorRole.Highlight, t['accent']),
        (QPalette.ColorRole.HighlightedText, '#ffffff'),
    ]:
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(t['muted']))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t['muted']))
    app.setPalette(palette)
    app.setFont(QFont('Segoe UI', 10))

    css = """
      /* Base controls */
      QToolBar { spacing: 4px; padding: 4px 6px; border: 0; background: PANEL; }
      QToolBar#commandToolbar { border-bottom: 1px solid BORDER; }
      QToolButton { padding: 5px 8px; border: 1px solid transparent; border-radius: 4px; color: FG; font-weight: 500; }
      QToolButton:hover { background: HOVER; border-color: BORDER; }
      QToolButton#shellTool { min-width: 38px; max-width: 38px; min-height: 38px; max-height: 38px; padding: 6px; border-radius: 6px; border: 1px solid transparent; }
      QToolButton#shellTool:hover { background: HOVER; }
      QToolButton#shellTool:checked { background: CARD; border: 1px solid BORDER; }
      QToolButton:checked { background: HOVER; border-left: 2px solid ACCENT; }
      QToolButton[primary='true'], QPushButton[primary='true'] { background: ACCENT; color: #ffffff; border: 1px solid ACCENT; border-radius: 4px; font-weight: 600; }
      QToolButton[primary='true']:hover, QPushButton[primary='true']:hover { background: ACCENT_HOVER; border-color: ACCENT_HOVER; }
      QPushButton { padding: 5px 12px; border: 1px solid BORDER; border-radius: 4px; background: CARD; color: FG; font-weight: 500; }
      QPushButton:hover { background: HOVER; border-color: BORDER; }
      QPushButton:disabled { color: MUTED; background: PANEL; border-color: BORDER; }
      QLineEdit, QComboBox, QSpinBox { padding: 4px 8px; min-height: 22px; border: 1px solid BORDER; border-radius: 4px; background: CARD; color: FG; }
      QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid ACCENT; }
      QComboBox QAbstractItemView { border: 1px solid BORDER; background: CARD; color: FG; selection-background-color: HOVER; selection-color: FG; padding: 2px; }
      QPlainTextEdit { font-family: Consolas, monospace; font-size: 13px; background: CARD; color: FG; border: 1px solid BORDER; }

      /* Views and trees */
      QTreeView, QTableView, QListView { border: 0; background: BASE; }
      QTreeView::item, QTableView::item { height: 28px; padding: 2px 4px; }
      QTreeView::item:hover, QTableView::item:hover { background: HOVER; }
      QTreeView::item:selected, QTableView::item:selected { background: HOVER; color: FG; }
      QHeaderView::section { background: PANEL; padding: 5px 8px; border: 0; border-bottom: 1px solid BORDER; font-weight: 600; font-size: 11px; color: MUTED; }

      /* Tabs and Docks */
      QTabBar::tab { padding: 6px 14px; background: transparent; color: MUTED; border-bottom: 2px solid transparent; font-weight: 500; }
      QTabBar::tab:selected { color: FG; border-bottom: 2px solid ACCENT; font-weight: 600; }
      QTabBar::tab:hover:!selected { color: FG; }
      QTabWidget::pane { border: 1px solid BORDER; }
      QWidget#panelHeader, QWidget#activityBar { background: PANEL; }
      QWidget#panelHeader { border-bottom: 1px solid BORDER; }
      QListWidget#pageNavigation { background: PANEL; border: 0; }
      QListWidget#pageNavigation::item { border-left: 3px solid transparent; padding: 6px 8px; border-radius: 6px; margin: 1px 4px; }
      QListWidget#pageNavigation::item:selected { background: HOVER; border-left: 3px solid ACCENT; }

      /* Status bar and splitters */
      QStatusBar { background: STATUS_BG; color: STATUS_FG; border-top: 1px solid BORDER; font-size: 11px; }
      QStatusBar QLabel { color: STATUS_FG; }
      QSplitter::handle { background: BORDER; }

      /* Question cards */
      QListWidget#questionCards { background: BASE; border: 0; padding: 6px; }
      QListWidget#questionCards::item { border: 0; padding: 0; margin: 2px 0; }
      QListWidget#questionCards::item:selected { background: transparent; }
      QFrame#questionCard { background: CARD; border: 1px solid BORDER; border-radius: 6px; }
      QFrame#questionCard:hover { border: 1px solid ACCENT; }
      QFrame#questionCard[expanded='true'] { border: 1px solid ACCENT; background: CARD; }
      QToolButton#expanderToggle { background: transparent; border: 0; font-size: 13px; font-weight: bold; color: MUTED; min-width: 22px; min-height: 22px; border-radius: 3px; }
      QToolButton#expanderToggle:hover { color: ACCENT; background: HOVER; }
      QToolButton#expandAllToggle { font-size: 11px; padding: 4px 8px; border-radius: 4px; background: PANEL; border: 1px solid BORDER; color: MUTED; }
      QToolButton#expandAllToggle:hover { color: FG; background: HOVER; border-color: ACCENT; }
      QLabel#cardLevelBadge[level='NB'] { background: NB_BG; color: NB_FG; border-radius: 3px; font-weight: 600; font-size: 10px; padding: 1px 5px; }
      QLabel#cardLevelBadge[level='TH'] { background: TH_BG; color: TH_FG; border-radius: 3px; font-weight: 600; font-size: 10px; padding: 1px 5px; }
      QLabel#cardLevelBadge[level='VD'] { background: VD_BG; color: VD_FG; border-radius: 3px; font-weight: 600; font-size: 10px; padding: 1px 5px; }
      QLabel#cardLevelBadge[level='VDC'] { background: VDC_BG; color: VDC_FG; border-radius: 3px; font-weight: 600; font-size: 10px; padding: 1px 5px; }
      QLabel#cardLevelBadge[level='NONE'] { background: HOVER; color: MUTED; border-radius: 3px; font-weight: 500; font-size: 10px; padding: 1px 5px; }
      QLabel#cardTypeBadge { background: HOVER; color: MUTED; border-radius: 3px; font-size: 10px; padding: 1px 5px; }
      QLabel#cardIdLabel { color: MUTED; font-size: 10px; font-family: Consolas, monospace; }
      QLabel#cardTaxonomyLabel { color: MUTED; font-size: 10.5px; }
      QLabel#cardStemSummary { color: FG; font-size: 12px; font-weight: 500; }
      QLabel#cardStemFull { color: FG; font-size: 13px; padding: 2px 0; }
      QFrame#cardOptionGrid { background: PANEL; border-radius: 4px; border: 1px solid BORDER; }
      QLabel#cardOptionText { color: FG; font-size: 11.5px; padding: 4px 8px; border-radius: 3px; }
      QLabel#cardOptionText[correct='true'] { color: #16a34a; font-weight: 600; background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.3); }
      QLabel#cardSolutionText { color: MUTED; font-size: 11.5px; background: PANEL; padding: 6px 10px; border-left: 3px solid ACCENT; border-radius: 3px; }
      QPushButton#cardActionBtn { font-size: 11px; padding: 3px 10px; border-radius: 4px; min-height: 22px; background: PANEL; border: 1px solid BORDER; color: FG; }
      QPushButton#cardActionBtn:hover { background: HOVER; border-color: ACCENT; }
      QLabel#cardFooter { color: MUTED; font-size: 10px; border-top: 1px solid BORDER; padding-top: 3px; }
      QLabel#scopeBreadcrumb { font-size: 13px; font-weight: 600; color: FG; padding: 2px 0; }

      /* Dashboard components */
      QFrame#dashboardMetric, QFrame#dashboardPanel { background: PANEL; border: 1px solid BORDER; border-radius: 5px; }
      QFrame#dashboardMetric { border-left: 3px solid ACCENT; }
      QLabel#dashboardTitle { font-size: 20px; font-weight: 600; }
      QLabel#dashboardEyebrow { font-size: 10px; font-weight: 700; color: ACCENT; letter-spacing: 1px; }
      QLabel#dashboardSubtitle, QLabel#metricDetail, QLabel#chartLegend { color: MUTED; }
      QLabel#dashboardClock { color: MUTED; font-size: 11px; }
      QLabel#metricTitle { color: MUTED; font-size: 11px; }
      QLabel#metricValue { font-size: 24px; font-weight: 600; color: ACCENT; }
      QLabel#panelTitle { font-size: 13px; font-weight: 600; color: FG; }
      QLabel#panelSubtitle { color: MUTED; font-size: 10px; }
      QLabel#assetLegend { color: FG; font-size: 11px; }
      QLabel#dashboardEmpty { color: MUTED; padding: 28px 8px; }
      QLabel#activityTime { color: MUTED; font-size: 11px; }
      QLabel#activityLabel { color: FG; font-size: 11px; }
      QLabel#activityDot { color: #16a085; font-size: 13px; }
      QFrame#dashboardActivityRow { border-bottom: 1px solid BORDER; }
      QPushButton[dashboardAction='true'] { text-align: left; padding: 8px 10px; min-height: 30px; }
      QScrollArea#dashboardScroll { background: BASE; }
      QFrame#dashboardPanel QListWidget { border: 0; background: transparent; }

      /* Import components */
      QListWidget#importSteps { background: PANEL; border: 1px solid BORDER; border-radius: 5px; padding: 4px; }
      QListWidget#importSteps::item { padding: 10px 6px; margin: 2px 0; border-radius: 4px; color: MUTED; }
      QListWidget#importSteps::item:selected { background: HOVER; color: FG; border-left: 3px solid ACCENT; }
      QLabel#importSourcePath { padding: 10px; border: 1px solid BORDER; background: PANEL; }
      QFrame#importStat { background: PANEL; border: 1px solid BORDER; border-radius: 4px; }
      QLabel#importStatValue { font-size: 20px; font-weight: 600; color: ACCENT; }
      QLabel#importStatLabel { color: MUTED; font-size: 10px; }

      /* Lessons & Exams */
      QTabWidget#lessonTabs::pane { border: 1px solid BORDER; }
      QTabWidget#lessonTabs QPlainTextEdit { background: BASE; }
      QTextEdit#wysiwygEditor { background: BASE; color: FG; border: 1px solid BORDER; }
      QListWidget#examSteps { background: PANEL; border: 1px solid BORDER; border-radius: 5px; padding: 4px; }
      QListWidget#examSteps::item { padding: 12px 6px; margin: 2px 0; border-radius: 4px; color: MUTED; }
      QListWidget#examSteps::item:selected { background: HOVER; color: FG; border-left: 3px solid ACCENT; }
    """
    for key, val in [
        ('ACCENT_HOVER', t['accent_hover']), ('ACCENT', t['accent']),
        ('PANEL', t['panel']), ('BASE', t['bg']), ('CARD', t['card']),
        ('HOVER', t['hover']), ('BORDER', t['border']), ('MUTED', t['muted']),
        ('FG', t['fg']),
        ('STATUS_BG', t['status_bg']), ('STATUS_FG', t['status_fg']),
        ('NB_BG', t['nb_bg']), ('NB_FG', t['nb_fg']),
        ('TH_BG', t['th_bg']), ('TH_FG', t['th_fg']),
        ('VD_BG', t['vd_bg']), ('VD_FG', t['vd_fg']),
        ('VDC_BG', t['vdc_bg']), ('VDC_FG', t['vdc_fg']),
    ]:
        css = css.replace(key, val)
    app.setStyleSheet(css)
