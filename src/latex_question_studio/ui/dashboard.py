"""Data backed home dashboard for the question studio."""
from datetime import datetime
import math
import re

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget, QScrollArea, QToolButton,
)

from latex_question_studio.ui.icons import icon


COLORS = ('#1677d2', '#16a085', '#f39c3d', '#e05d5d')
LEVELS = (('NB', 'Nhận biết'), ('TH', 'Thông hiểu'), ('VD', 'Vận dụng'), ('VDC', 'Vận dụng cao'))


def number(value):
    return f'{int(value):,}'.replace(',', '.')


class MetricCard(QFrame):
    def __init__(self, title, accent, icon_name, parent=None):
        super().__init__(parent)
        self.setObjectName('dashboardMetric')
        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)
        mark = QLabel()
        mark.setFixedSize(36, 36)
        mark.setPixmap(icon(icon_name, accent).pixmap(QSize(25, 25)))
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet(f'background: {accent}22; border-radius: 9px;')
        outer.addWidget(mark, 0, Qt.AlignmentFlag.AlignTop)
        body = QVBoxLayout()
        body.setSpacing(1)
        self.title = QLabel(title)
        self.title.setObjectName('metricTitle')
        self.value = QLabel('0')
        self.value.setObjectName('metricValue')
        self.value.setProperty('accent', accent)
        self.detail = QLabel('')
        self.detail.setObjectName('metricDetail')
        body.addWidget(self.title)
        body.addWidget(self.value)
        body.addWidget(self.detail)
        outer.addLayout(body, 1)
        self.setMinimumHeight(92)

    def set_data(self, value, detail):
        self.value.setText(number(value))
        self.detail.setText(detail)


class BarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.setMinimumHeight(205)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(42, 12, -14, -30)
        muted = self.palette().color(self.palette().ColorRole.PlaceholderText)
        foreground = self.palette().color(self.palette().ColorRole.Text)
        grid = self.palette().color(self.palette().ColorRole.Mid)
        painter.setFont(QFont(self.font().family(), 9))
        if not self.data or not any(any(values) for _, values in self.data):
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, 'Chưa có dữ liệu theo môn học')
            return
        maximum = max(max(values) for _, values in self.data) or 1
        maximum = max(4, math.ceil(maximum / 4) * 4)
        for tick in range(5):
            value = maximum * tick / 4
            y = rect.bottom() - rect.height() * tick / 4
            painter.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))
            painter.setPen(muted)
            painter.drawText(0, int(y - 8), 36, 16, Qt.AlignmentFlag.AlignRight, number(value))
        slot = rect.width() / max(1, len(self.data))
        group_width = min(slot * .72, 92)
        bar_width = max(5, group_width / 5)
        for index, (label, values) in enumerate(self.data):
            center = rect.left() + slot * (index + .5)
            for bar, value in enumerate(values):
                height = rect.height() * value / maximum
                x = center - group_width / 2 + bar * (bar_width + 2)
                y = rect.bottom() - height
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(COLORS[bar]))
                painter.drawRoundedRect(int(x), int(y), int(bar_width), max(2, int(height)), 3, 3)
            painter.setPen(foreground)
            painter.drawText(int(center - slot / 2), rect.bottom() + 8, int(slot), 20,
                             Qt.AlignmentFlag.AlignCenter, label[:14])


class DonutChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.setMinimumSize(154, 154)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    def set_data(self, values):
        self.values = values
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = sum(value for _, value, _ in self.values)
        center = self.rect().center()
        size = min(self.width(), self.height()) - 26
        box = center.x() - size // 2, center.y() - size // 2, size, size
        painter.setPen(QPen(self.palette().color(self.palette().ColorRole.Mid), 18))
        painter.drawArc(*box, 0, 5760)
        if total:
            start = 0
            for index, (_, value, _) in enumerate(self.values):
                span = round(5760 * value / total)
                painter.setPen(QPen(QColor(COLORS[index]), 18))
                painter.drawArc(*box, start, span)
                start += span
        painter.setPen(self.palette().color(self.palette().ColorRole.Text))
        painter.setFont(QFont(self.font().family(), 16, QFont.Weight.DemiBold))
        painter.drawText(center.x() - 45, center.y() - 7, 90, 24, Qt.AlignmentFlag.AlignCenter, number(total))
        painter.setFont(QFont(self.font().family(), 8))
        painter.setPen(self.palette().color(self.palette().ColorRole.PlaceholderText))
        painter.drawText(center.x() - 45, center.y() + 14, 90, 16, Qt.AlignmentFlag.AlignCenter, 'tài nguyên')


class ActivityRow(QFrame):
    def __init__(self, timestamp, title, kind, parent=None):
        super().__init__(parent)
        self.setObjectName('dashboardActivityRow')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 7, 0, 7)
        layout.setSpacing(10)
        time = QLabel(timestamp)
        time.setObjectName('activityTime')
        time.setFixedWidth(45)
        layout.addWidget(time)
        dot = QLabel('●')
        dot.setObjectName('activityDot')
        dot.setProperty('kind', kind)
        layout.addWidget(dot)
        label = QLabel(title)
        label.setObjectName('activityLabel')
        label.setWordWrap(True)
        layout.addWidget(label, 1)


class DashboardPage(QWidget):
    def __init__(self, services, callbacks=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.callbacks = callbacks or {}
        self.setObjectName('dashboardPage')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName('dashboardScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        intro = QVBoxLayout()
        eyebrow = QLabel('TỔNG QUAN HỆ THỐNG')
        eyebrow.setObjectName('dashboardEyebrow')
        title = QLabel('Chào mừng đến với MCPTest')
        title.setObjectName('dashboardTitle')
        subtitle = QLabel('Theo dõi ngân hàng câu hỏi và bắt đầu công việc hôm nay.')
        subtitle.setObjectName('dashboardSubtitle')
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        header.addLayout(intro, 1)
        status = QVBoxLayout()
        self.clock = QLabel()
        self.clock.setObjectName('dashboardClock')
        self.clock.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.refresh_button = QToolButton()
        self.refresh_button.setIcon(icon('preview', '#1677d2'))
        self.refresh_button.setToolTip('Làm mới số liệu')
        self.refresh_button.clicked.connect(self.refresh)
        status_row = QHBoxLayout()
        status_row.addStretch()
        status_row.addWidget(self.refresh_button)
        status.addWidget(self.clock)
        status.addLayout(status_row)
        header.addLayout(status)
        layout.addLayout(header)

        self.metrics = QGridLayout()
        self.metrics.setHorizontalSpacing(12)
        self.metrics.setVerticalSpacing(12)
        self.cards = [
            MetricCard('Tổng câu hỏi', COLORS[0], 'bank'),
            MetricCard('Đang sử dụng', COLORS[1], 'lesson'),
            MetricCard('Cần kiểm tra', COLORS[3], 'import'),
            MetricCard('Thiếu tài nguyên', COLORS[2], 'settings'),
        ]
        for index, card in enumerate(self.cards):
            self.metrics.addWidget(card, 0, index)
        layout.addLayout(self.metrics)

        charts = QGridLayout()
        charts.setHorizontalSpacing(12)
        charts.setVerticalSpacing(12)
        self.chart_panel = self._panel('Phân bố câu hỏi theo môn', 'Mức độ nhận thức')
        chart_layout = self.chart_panel.layout()
        self.chart = BarChart()
        chart_layout.addWidget(self.chart, 1)
        self.chart_legend = QLabel()
        self.chart_legend.setObjectName('chartLegend')
        chart_layout.addWidget(self.chart_legend)
        charts.addWidget(self.chart_panel, 0, 0)
        self.asset_panel = self._panel('Tình trạng tài nguyên', 'Kiểm tra trước khi tạo đề')
        self.asset_panel.setMinimumHeight(248)
        asset_layout = self.asset_panel.layout()
        asset_row = QHBoxLayout()
        asset_row.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.donut = DonutChart()
        asset_row.addWidget(self.donut, 0, Qt.AlignmentFlag.AlignCenter)
        self.asset_labels = QVBoxLayout()
        self.asset_labels.setContentsMargins(4, 8, 0, 0)
        self.asset_labels.setSpacing(8)
        asset_row.addLayout(self.asset_labels, 1)
        asset_layout.addLayout(asset_row, 1)
        charts.addWidget(self.asset_panel, 0, 1)
        charts.setColumnStretch(0, 3)
        charts.setColumnStretch(1, 2)
        layout.addLayout(charts)

        bottom = QGridLayout()
        bottom.setHorizontalSpacing(12)
        self.activity_panel = self._panel('Hoạt động gần đây', 'Các thay đổi mới nhất trong ngân hàng')
        self.activity_body = QVBoxLayout()
        self.activity_body.setSpacing(0)
        self.activity_panel.layout().addLayout(self.activity_body)
        bottom.addWidget(self.activity_panel, 0, 0)
        quick = self._panel('Bắt đầu nhanh', 'Các thao tác thường dùng')
        quick_layout = quick.layout()
        actions = [('Nhập câu hỏi', 'import', 'import'), ('Tạo đề thi', 'exam', 'exam'),
                   ('Soạn bài giảng', 'lesson', 'lesson'),
                   ('Mở ngân hàng', 'bank', 'library'), ('Quản lý tài nguyên', 'settings', 'settings')]
        for label, icon_name, key in actions:
            button = QPushButton(label)
            button.setIcon(icon(icon_name, '#1677d2'))
            button.setIconSize(QSize(18, 18))
            button.setProperty('dashboardAction', True)
            button.clicked.connect(lambda checked=False, k=key: self.callbacks.get(k, lambda: None)())
            quick_layout.addWidget(button)
        bottom.addWidget(quick, 0, 1)
        bottom.setColumnStretch(0, 3)
        bottom.setColumnStretch(1, 2)
        layout.addLayout(bottom)
        layout.addStretch(1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(30000)
        self.update_clock()
        self.refresh()

    @staticmethod
    def _panel(title, subtitle=''):
        panel = QFrame()
        panel.setObjectName('dashboardPanel')
        box = QVBoxLayout(panel)
        box.setContentsMargins(14, 12, 14, 12)
        box.setSpacing(4)
        label = QLabel(title)
        label.setObjectName('panelTitle')
        box.addWidget(label)
        if subtitle:
            hint = QLabel(subtitle)
            hint.setObjectName('panelSubtitle')
            box.addWidget(hint)
        return panel

    def resizeEvent(self, event):
        super().resizeEvent(event)
        columns = 2 if self.width() < 1120 else 4
        for index, card in enumerate(self.cards):
            self.metrics.addWidget(card, index // columns, index % columns)

    def update_clock(self):
        self.clock.setText(datetime.now().strftime('%A, %d/%m/%Y\n%H:%M'))

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                DashboardPage._clear_layout(item.layout())

    def refresh(self):
        try:
            with self.services.database.connect() as connection:
                total = connection.execute('SELECT count(*) FROM questions').fetchone()[0]
                active = connection.execute("SELECT count(*) FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id WHERE coalesce(json_extract(m.data_json,'$.archived'),0)=0").fetchone()[0]
                invalid = connection.execute("SELECT count(*) FROM question_analysis WHERE valid=0").fetchone()[0]
                missing = connection.execute("SELECT count(*) FROM question_assets WHERE resolution_status<>'RESOLVED'").fetchone()[0]
                asset_total = connection.execute('SELECT count(*) FROM question_assets').fetchone()[0]
                asset_ready = connection.execute("SELECT count(*) FROM question_assets WHERE resolution_status='RESOLVED'").fetchone()[0]
                asset_missing = connection.execute("SELECT count(*) FROM question_assets WHERE resolution_status LIKE '%MISSING%' OR resolution_status LIKE '%AMBIGUOUS%'").fetchone()[0]
                asset_other = max(0, asset_total - asset_ready - asset_missing)
                levels = [(row['subject'] or 'Khác', row['cognitive_level'] or 'Chưa gán', row['count']) for row in connection.execute("SELECT json_extract(m.data_json,'$.subject') AS subject, q.cognitive_level, count(*) AS count FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id GROUP BY subject,q.cognitive_level ORDER BY subject,count DESC")]
                recent = [(row['updated_at'], row['latex_source'], row['valid']) for row in connection.execute('SELECT q.updated_at,q.latex_source,coalesce(a.valid,1) AS valid FROM questions q LEFT JOIN question_analysis a ON a.question_id=q.id ORDER BY q.updated_at DESC LIMIT 6')]
            self.cards[0].set_data(total, 'Câu hỏi trong ngân hàng')
            self.cards[1].set_data(active, f'{number(active / total * 100) if total else 0}% đang hoạt động')
            self.cards[2].set_data(invalid, 'Source cần kiểm tra')
            self.cards[3].set_data(missing, 'Liên kết cần xử lý')
            subject_data = {}
            for subject, level, value in levels:
                subject_data.setdefault(subject, {key: 0 for key, _ in LEVELS})
                if level in subject_data[subject]:
                    subject_data[subject][level] += value
            chart_data = [(subject, [values[key] for key, _ in LEVELS]) for subject, values in list(subject_data.items())[:5] if any(values.values())]
            self.chart.set_data(chart_data)
            self.chart_legend.setText('   '.join(f'<span style="color:{color}">■</span> {label}' for (_, label), color in zip(LEVELS, COLORS)))
        except Exception:
            return
        status = [('Sẵn sàng', asset_ready, COLORS[1]), ('Thiếu/hỏng', asset_missing, COLORS[2]), ('Chưa kiểm tra', asset_other, COLORS[3]), ('Không có tài nguyên', max(0, asset_total - asset_ready - asset_missing - asset_other), '#7b61c9')]
        self.donut.set_data(status)
        self._clear_layout(self.asset_labels)
        asset_count = sum(value for _, value, _ in status)
        asset_total = asset_count or 1
        if asset_count:
            for label, value, color in status:
                row = QHBoxLayout()
                swatch = QLabel('●')
                swatch.setStyleSheet(f'color: {color};')
                text = QLabel(f'{label}\n{number(value)}  ·  {value / asset_total:.0%}')
                text.setObjectName('assetLegend')
                text.setMinimumHeight(30)
                row.addWidget(swatch)
                row.addWidget(text, 1)
                self.asset_labels.addLayout(row)
        else:
            empty = QLabel('Chưa có tài nguyên được liên kết')
            empty.setObjectName('dashboardEmpty')
            self.asset_labels.addWidget(empty)
        self._clear_layout(self.activity_body)
        if not recent:
            empty = QLabel('Chưa có hoạt động. Hãy nhập câu hỏi hoặc tạo câu mới để bắt đầu.')
            empty.setObjectName('dashboardEmpty')
            self.activity_body.addWidget(empty)
        else:
            for timestamp, source, valid in recent:
                stamp = str(timestamp).replace('T', ' ')[11:16]
                title = re.sub(r'\\(?:begin|end)\{[^}]*\}|\\[A-Za-z]+(?:\[[^]]*\])?', '', source)
                title = title.replace('{', '').replace('}', '').replace('$', '').replace('\n', ' ').strip()[:82]
                self.activity_body.addWidget(ActivityRow(stamp, title or 'Câu hỏi mới', 'ok' if valid else 'error'))
        self.activity_body.addStretch(1)
