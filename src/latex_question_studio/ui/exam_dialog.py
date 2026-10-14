import os
import re
import json
import random
from pathlib import Path
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QSplitter,
    QTreeWidget, QTreeWidgetItem, QHBoxLayout, QComboBox, QTabBar,
    QStackedWidget, QListWidget, QListWidgetItem, QHeaderView, QGroupBox, QFrame,
    QRadioButton, QButtonGroup, QFileDialog, QMessageBox, QProgressBar
)
from latex_question_studio.ui.icons import icon
from latex_question_studio.preview.compiler import MAPCLASS_PREAMBLE

# Mapping helper dictionaries
QTYPE_CODE_MAP = {
    'mcq': 'mcq', 'Trắc nghiệm': 'mcq', 'trắc nghiệm': 'mcq', 'Trắc nghiệm (4 PA)': 'mcq',
    'true_false': 'true_false', 'Đúng / Sai': 'true_false', 'Đúng / sai': 'true_false', 'đúng sai': 'true_false',
    'short_answer': 'short_answer', 'Trả lời ngắn': 'short_answer', 'trả lời ngắn': 'short_answer',
    'essay': 'essay', 'Tự luận': 'essay', 'tự luận': 'essay',
    '': ''
}

QTYPE_LABEL_MAP = {
    'mcq': 'Trắc nghiệm',
    'true_false': 'Đúng / sai',
    'short_answer': 'Trả lời ngắn',
    'essay': 'Tự luận'
}

LEVEL_LABEL_MAP = {
    'NB': 'Nhận biết',
    'TH': 'Thông hiểu',
    'VD': 'Vận dụng',
    'VDC': 'Vận dụng cao'
}

LEVEL_CODE_MAP = {
    'NB': 'NB', 'Nhận biết': 'NB',
    'TH': 'TH', 'Thông hiểu': 'TH',
    'VD': 'VD', 'Vận dụng': 'VD',
    'VDC': 'VDC', 'Vận dụng cao': 'VDC',
    '': ''
}


class TieudeTPreviewCard(QFrame):
    r"""Visual preview replicating the \TieudeT side-by-side header from MAPClass."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tieudeTPreviewCard")
        self.setStyleSheet("""
            QFrame#tieudeTPreviewCard {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-top: 3px solid #0284c7;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(14)

        # Cột trái: Đơn vị / Trường, Đề luyện tập số ..., Mã đề
        left_box = QVBoxLayout()
        left_box.setSpacing(3)
        self.lbl_school = QLabel("TRƯỜNG THPT CHUYÊN")
        self.lbl_school.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_school.setStyleSheet("font-weight: bold; font-size: 11px; color: #475569;")
        left_box.addWidget(self.lbl_school)

        self.lbl_subtitle = QLabel("ĐỀ LUYỆN TẬP SỐ ①")
        self.lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_subtitle.setStyleSheet("font-weight: bold; font-size: 13px; color: #0f172a;")
        left_box.addWidget(self.lbl_subtitle)

        self.lbl_code = QLabel("(Mã đề thi: 101)")
        self.lbl_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_code.setStyleSheet("font-size: 11px; font-weight: bold; color: #0284c7;")
        left_box.addWidget(self.lbl_code)
        layout.addLayout(left_box, 38)

        # Đường phân cách dọc
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #cbd5e1;")
        layout.addWidget(line)

        # Cột phải: Tiêu đề đề thi, Môn học, Thời gian
        right_box = QVBoxLayout()
        right_box.setSpacing(3)
        self.lbl_title = QLabel("ĐỀ KIỂM TRA ĐỊNH KỲ")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #0369a1;")
        self.lbl_title.setWordWrap(True)
        right_box.addWidget(self.lbl_title)

        self.lbl_subject = QLabel("Môn: TOÁN 12")
        self.lbl_subject.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_subject.setStyleSheet("font-weight: bold; font-size: 12px; color: #0f172a;")
        right_box.addWidget(self.lbl_subject)

        self.lbl_duration = QLabel("Thời gian làm bài: 90 phút (không tính thời gian giao đề)")
        self.lbl_duration.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_duration.setStyleSheet("font-style: italic; font-size: 11px; color: #64748b;")
        right_box.addWidget(self.lbl_duration)
        layout.addLayout(right_box, 62)

    def update_header(self, title, subject, grade, duration, school, exam_code):
        title_str = (title or "ĐỀ KIỂM TRA").strip().upper()
        self.lbl_title.setText(title_str)

        school_str = (school or "TRƯỜNG THPT").strip().upper()
        self.lbl_school.setText(school_str)

        code_str = (exam_code or "101").strip()
        self.lbl_code.setText(f"(Mã đề thi: {code_str})")
        self.lbl_subtitle.setText("ĐỀ THI / KIỂM TRA")

        subj_display = (subject or "TOÁN").strip().upper()
        if grade and grade not in subj_display:
            subj_display += f" - {grade}"
        self.lbl_subject.setText(f"Môn: {subj_display}")

        dur_str = (duration or "90 phút").strip()
        self.lbl_duration.setText(f"Thời gian làm bài: {dur_str} (không tính thời gian giao đề)")


class ExamDialog(QWidget):
    submitted = Signal()
    use_selection = Signal()
    export_requested = Signal()

    def __init__(self, manual_ids, parent=None, services=None, run_job=None):
        super().__init__(parent)
        self.manual_ids = list(manual_ids)
        self.services = services
        self.scope = None
        self.run_job = run_job
        self.stats_generation = 0
        self.stats_job = None
        self.available = None
        self.matrix_available = None
        self.snapshot = None

        from latex_question_studio.ui.components.workspace import Workspace, CommandToolbar
        from latex_question_studio.ui.panels.question_preview import QuestionPreview

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        main_layout.addWidget(QLabel('RA ĐỀ THI'))

        # Header Modes: Từ CSDL hoặc Trộn TeX
        self.modes = QTabBar()
        self.modes.addTab('Từ ngân hàng câu hỏi')
        self.modes.addTab('Trộn từ file TeX')
        main_layout.addWidget(self.modes)

        # Body: Cột trái (5 bước wizard) + Stack trang bên phải
        body = QHBoxLayout()
        body.setSpacing(10)
        self.exam_steps = QListWidget()
        self.exam_steps.setObjectName('examSteps')
        self.exam_steps.setFixedWidth(190)
        labels = [
            ('Thông tin đề', 'Tên, seed, tiêu đề \\TieudeT'),
            ('Chọn câu hỏi', 'Cây CSDL & ma trận đặc tả'),
            ('Cấu hình', 'Xáo câu, đáp án & sinh đề'),
            ('Xem trước', 'Kiểm tra đề đã tạo'),
            ('Xuất đề', 'TeX, PDF, đáp án')
        ]
        for index, (title, detail) in enumerate(labels):
            item = QListWidgetItem(f'{index+1}  {title}\n     {detail}')
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.exam_steps.addItem(item)
        body.addWidget(self.exam_steps)

        self.mode_stack = QStackedWidget()
        body.addWidget(self.mode_stack, 1)
        main_layout.addLayout(body, 1)

        # Trang chế độ ngân hàng (bank_page)
        bank_page = QWidget()
        self.mode_stack.addWidget(bank_page)
        self.bank_layout = QVBoxLayout(bank_page)
        self.bank_layout.setContentsMargins(0, 0, 0, 0)
        self.bank_layout.setSpacing(6)

        # Stack quản lý 5 bước của quy trình ra đề
        self.bank_step_stack = QStackedWidget()
        self.bank_layout.addWidget(self.bank_step_stack, 1)

        # =========================================================================
        # ------------------ BƯỚC 1: THÔNG TIN ĐỀ & TIÊU ĐỀ \TieudeT --------------
        # =========================================================================
        page_info = QWidget()
        p0_box = QVBoxLayout(page_info)
        p0_box.setContentsMargins(14, 14, 14, 14)
        p0_box.setSpacing(12)

        info_header = QLabel('BƯỚC 1: THIẾT LẬP THÔNG TIN ĐỀ THI (HỌC LỆNH \\TieudeT MAPCLASS)')
        info_header.setStyleSheet('font-weight: bold; font-size: 14px; color: #4ba3eb;')
        p0_box.addWidget(info_header)
        p0_hint = QLabel('Đặt tên đề bài kiểm tra, cấu hình tiêu đề 2 cột side-by-side chuẩn Mapclass (lệnh \\TieudeT) và chọn mã seed ngẫu nhiên.')
        p0_hint.setWordWrap(True)
        p0_box.addWidget(p0_hint)

        info_split = QHBoxLayout()
        info_split.setSpacing(16)

        # Cột nhập thông tin bên trái
        inputs_container = QWidget()
        in_box = QVBoxLayout(inputs_container)
        in_box.setContentsMargins(0, 0, 0, 0)
        in_box.setSpacing(10)

        info_group = QGroupBox('Thông tin cơ bản của đề thi')
        info_form = QFormLayout(info_group)
        info_form.setSpacing(8)

        self.title = QLineEdit('Đề kiểm tra')
        self.title.setPlaceholderText('Nhập tên đề kiểm tra (ví dụ: Đề kiểm tra 1 tiết Toán 12...)')
        info_form.addRow('Tên đề thi:', self.title)

        quick_titles = QHBoxLayout()
        for tname in ('Kiểm tra 15 phút', 'Kiểm tra 1 tiết', 'Thi giữa học kỳ', 'Thi cuối học kỳ', 'Thi thử tốt nghiệp'):
            btn = QPushButton(tname)
            btn.clicked.connect(lambda checked=False, text=tname: self.title.setText(text))
            quick_titles.addWidget(btn)
        quick_titles.addStretch()
        info_form.addRow('Gợi ý tên:', quick_titles)

        # Các trường bổ sung theo chuẩn lệnh \TieudeT trong Mapclass
        tieude_sub_box = QHBoxLayout()
        self.school_input = QLineEdit('TRƯỜNG THPT CHUYÊN')
        self.school_input.setPlaceholderText('Tên trường / Sở GD&ĐT / Trung tâm')
        tieude_sub_box.addWidget(self.school_input, 2)

        self.exam_code_input = QLineEdit('101')
        self.exam_code_input.setPlaceholderText('Mã đề (101, 102...)')
        tieude_sub_box.addWidget(self.exam_code_input, 1)
        info_form.addRow('Trường / Mã đề:', tieude_sub_box)

        subj_grade_box = QHBoxLayout()
        self.subject_input = QComboBox()
        self.subject_input.setEditable(True)
        for s in ('TOÁN', 'KHOA HỌC TỰ NHIÊN', 'VẬT LÍ', 'HÓA HỌC', 'SINH HỌC', 'TIN HỌC', 'LỊCH SỬ', 'ĐỊA LÍ', 'TIẾNG ANH'):
            self.subject_input.addItem(s)
        subj_grade_box.addWidget(self.subject_input, 2)

        self.grade_input = QComboBox()
        self.grade_input.setEditable(True)
        for g in ('Lớp 12', 'Lớp 11', 'Lớp 10', 'Lớp 9', 'Lớp 8', 'Lớp 7', 'Lớp 6'):
            self.grade_input.addItem(g)
        subj_grade_box.addWidget(self.grade_input, 1)

        self.duration_input = QComboBox()
        self.duration_input.setEditable(True)
        for d in ('90 phút', '45 phút', '50 phút', '60 phút', '120 phút', '15 phút'):
            self.duration_input.addItem(d)
        subj_grade_box.addWidget(self.duration_input, 1)
        info_form.addRow('Môn / Lớp / Thời gian:', subj_grade_box)

        seed_box = QHBoxLayout()
        self.seed = QSpinBox()
        self.seed.setRange(0, 2_000_000_000)
        self.seed.setValue(2027)
        self.seed.setToolTip('Seed để tái lập lựa chọn')
        seed_box.addWidget(self.seed)
        btn_rand_seed = QPushButton('🎲 Tạo seed ngẫu nhiên')
        btn_rand_seed.clicked.connect(lambda: self.seed.setValue(random.randint(1000, 999999)))
        seed_box.addWidget(btn_rand_seed)
        seed_box.addStretch()
        info_form.addRow('Mã seed tái lập:', seed_box)

        in_box.addWidget(info_group)
        info_split.addWidget(inputs_container, 3)

        # Cột xem trước tiêu đề bên phải
        preview_container = QWidget()
        pv_box = QVBoxLayout(preview_container)
        pv_box.setContentsMargins(0, 0, 0, 0)
        pv_box.setSpacing(6)

        pv_lbl = QLabel('XEM TRƯỚC TIÊU ĐỀ (CHUẨN LỆNH \\TieudeT MAPCLASS)')
        pv_lbl.setStyleSheet('font-weight: bold; font-size: 11px; color: #38bdf8;')
        pv_box.addWidget(pv_lbl)

        self.tieudet_preview = TieudeTPreviewCard()
        pv_box.addWidget(self.tieudet_preview)

        pv_note = QLabel('Tiêu đề này sẽ được chèn ở đầu đề thi khi xuất TeX/PDF. Trong MAPClass, lệnh \\TieudeT tự động tạo khung 2 cột viền màu với logo và số đề.')
        pv_note.setStyleSheet('font-size: 11px; color: #94a3b8;')
        pv_note.setWordWrap(True)
        pv_box.addWidget(pv_note)
        pv_box.addStretch()

        info_split.addWidget(preview_container, 2)
        p0_box.addLayout(info_split)
        p0_box.addStretch()

        # Kết nối sự kiện cập nhật trực tiếp khung xem trước tiêu đề
        self.title.textChanged.connect(self._sync_header_preview)
        self.school_input.textChanged.connect(self._sync_header_preview)
        self.exam_code_input.textChanged.connect(self._sync_header_preview)
        self.subject_input.currentTextChanged.connect(self._sync_header_preview)
        self.grade_input.currentTextChanged.connect(self._sync_header_preview)
        self.duration_input.currentTextChanged.connect(self._sync_header_preview)
        self._sync_header_preview()

        nav_box_0 = QHBoxLayout()
        nav_box_0.addStretch()
        btn_to_step1 = QPushButton('Tiếp tục: Chọn câu hỏi & Ma trận ›')
        btn_to_step1.setProperty('primary', True)
        btn_to_step1.clicked.connect(lambda: self.set_exam_step(1))
        nav_box_0.addWidget(btn_to_step1)
        p0_box.addLayout(nav_box_0)

        self.bank_step_stack.addWidget(page_info)

        # =========================================================================
        # ------------------ BƯỚC 2: CHỌN CÂU HỎI & MA TRẬN ĐỀ THI -----------------
        # =========================================================================
        page_select = QWidget()
        p1_box = QVBoxLayout(page_select)
        p1_box.setContentsMargins(0, 0, 0, 0)
        p1_box.setSpacing(6)

        self.toolbar = CommandToolbar('Ra đề thi', self)
        p1_box.addWidget(self.toolbar)
        self.generate_action = self.toolbar.command('exam', 'Tạo đề', self.submitted.emit, True)
        self.select_action = self.toolbar.command('bank', 'Lấy câu đang chọn từ CSDL', self.use_selection.emit)
        self.toolbar.addSeparator()
        self.tree_toggle_action = self.toolbar.command('subject', 'Hiện / ẩn Cây CSDL', self.toggle_tree_panel)
        self.scope_action = self.toolbar.command('chapter', 'Thêm phạm vi và số câu vào ma trận', self.add_scope_rows)
        self.scope_action.setEnabled(bool(services))
        self.add_action = self.toolbar.command('topic', 'Thêm hàng ma trận', self.add_row)
        self.remove_action = self.toolbar.command('close', 'Xóa hàng ma trận đang chọn', self.remove_row)
        self.refresh_action = self.toolbar.command('preview', 'Cập nhật thống kê nguồn', self.refresh_statistics)
        self.refresh_action.setEnabled(bool(services))

        self.selection_label = QLabel()
        self.selection_label.setWordWrap(True)
        p1_box.addWidget(self.selection_label)

        # Workspace 3 cột
        self.workspace = Workspace('examSplit')
        p1_box.addWidget(self.workspace, 1)

        # ------------------ CỘT TRÁI: CÂY CSDL THEO MÔN ------------------
        left = QWidget()
        left.setObjectName('examTreePanel')
        left.setMinimumWidth(240)
        self.tree_panel = left
        lb = QVBoxLayout(left)
        lb.setContentsMargins(0, 0, 0, 0)
        lb.setSpacing(6)

        left_hdr_box = QHBoxLayout()
        left_hdr = QLabel('CÂY CSDL THEO MÔN HỌC')
        left_hdr.setStyleSheet('font-weight: bold; font-size: 11px; color: #4ba3eb;')
        left_hdr_box.addWidget(left_hdr)
        left_hdr_box.addStretch()

        btn_collapse_all = QPushButton('Thu gọn')
        btn_collapse_all.setFixedHeight(22)
        btn_collapse_all.setStyleSheet('font-size: 10px; padding: 2px 6px;')
        btn_collapse_all.clicked.connect(self._collapse_tree_all)
        left_hdr_box.addWidget(btn_collapse_all)

        btn_expand_all = QPushButton('Mở rộng')
        btn_expand_all.setFixedHeight(22)
        btn_expand_all.setStyleSheet('font-size: 10px; padding: 2px 6px;')
        btn_expand_all.clicked.connect(self._expand_tree_all)
        left_hdr_box.addWidget(btn_expand_all)

        lb.addLayout(left_hdr_box)

        # Bộ lọc theo Môn học trên đỉnh cây
        self.subject_filter = QComboBox()
        self.subject_filter.addItem('Tất cả môn học', '')
        for sname in ('TOÁN', 'KHTN', 'VẬT LÍ', 'HÓA HỌC', 'SINH HỌC', 'TIN HỌC', 'LỊCH SỬ', 'ĐỊA LÍ'):
            self.subject_filter.addItem(sname, sname)
        self.subject_filter.currentIndexChanged.connect(self._filter_tree_by_subject)
        lb.addWidget(self.subject_filter)

        # Ô tìm kiếm nhanh trên cây CSDL
        self.tree_search = QLineEdit()
        self.tree_search.setPlaceholderText('🔍 Tìm bài, dạng...')
        self.tree_search.textChanged.connect(self._filter_tree_search)
        lb.addWidget(self.tree_search)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel('MÔN › BÀI › DẠNG TOÁN')
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.itemClicked.connect(self.select_scope)
        lb.addWidget(self.tree, 1)
        self.workspace.addWidget(left)

        # ------------------ CỘT GIỮA: KHUNG THỐNG KÊ 4x4 & MA TRẬN ĐỀ -----
        center = QWidget()
        box = QVBoxLayout(center)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(6)
        self.workspace.addWidget(center)

        # Breadcrumb phạm vi đang chọn
        self.scope_label = QLabel('📍 Toàn ngân hàng')
        self.scope_label.setStyleSheet('font-weight: bold; font-size: 12px; color: #38bdf8;')
        self.scope_label.setWordWrap(True)
        box.addWidget(self.scope_label)

        # Hộp thống kê & chọn câu (Ma trận đặc tả 4 loại x 4 mức độ)
        grid_box = QGroupBox('Khung thống kê sẵn có & Chọn số câu theo 4 mức độ')
        grid_layout = QVBoxLayout(grid_box)
        grid_layout.setContentsMargins(6, 6, 6, 6)
        grid_layout.setSpacing(4)

        self.matrix_grid = QTableWidget(4, 6)
        self.matrix_grid.setHorizontalHeaderLabels([
            'Định dạng câu hỏi', 'Nhận biết (NB)', 'Thông hiểu (TH)', 'Vận dụng (VD)', 'Vận dụng cao (VDC)', 'Tổng chọn'
        ])
        self.matrix_grid.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for c in range(1, 5):
            self.matrix_grid.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        self.matrix_grid.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.matrix_grid.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.matrix_grid.verticalHeader().setDefaultSectionSize(34)
        self.matrix_grid.setMaximumHeight(180)

        self.grid_spins = {}       # (qtype, level) -> QSpinBox
        self.grid_avail_lbls = {}  # (qtype, level) -> QLabel
        self.grid_row_totals = {}  # qtype -> QLabel

        types_list = [
            ('mcq', 'Trắc nghiệm (4 PA)'),
            ('true_false', 'Đúng / sai'),
            ('short_answer', 'Trả lời ngắn'),
            ('essay', 'Tự luận')
        ]
        levels_list = [('NB', 'Nhận biết'), ('TH', 'Thông hiểu'), ('VD', 'Vận dụng'), ('VDC', 'Vận dụng cao')]

        for row_idx, (qtype, qname) in enumerate(types_list):
            item_name = QTableWidgetItem(qname)
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.matrix_grid.setItem(row_idx, 0, item_name)

            for col_idx, (lvl, _) in enumerate(levels_list, 1):
                cell_widget = QWidget()
                c_lay = QHBoxLayout(cell_widget)
                c_lay.setContentsMargins(4, 2, 4, 2)
                c_lay.setSpacing(4)
                c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

                lbl_prefix = QLabel('chọn')
                lbl_prefix.setFixedWidth(30)
                lbl_prefix.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                lbl_prefix.setStyleSheet('font-size: 11px; color: #64748b; font-weight: 500;')
                c_lay.addWidget(lbl_prefix)

                spin = QSpinBox()
                spin.setObjectName('matrixSpin')
                spin.setRange(0, 500)
                spin.setValue(0)
                spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
                spin.setFixedWidth(46)
                spin.setFixedHeight(24)
                spin.valueChanged.connect(self._update_grid_selection_summary)
                self.grid_spins[(qtype, lvl)] = spin
                c_lay.addWidget(spin)
                c_lay.addSpacing(8)

                avail_badge = QLabel('[0]')
                avail_badge.setObjectName('matrixAvailBadge')
                avail_badge.setFixedWidth(40)
                avail_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                avail_badge.setStyleSheet('font-size: 11px; color: #94a3b8; font-weight: 600; padding: 1px 2px;')
                self.grid_avail_lbls[(qtype, lvl)] = avail_badge
                c_lay.addWidget(avail_badge)

                unit_lbl = QLabel('câu')
                unit_lbl.setFixedWidth(24)
                unit_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                unit_lbl.setStyleSheet('font-size: 11px; color: #64748b;')
                c_lay.addWidget(unit_lbl)

                self.matrix_grid.setCellWidget(row_idx, col_idx, cell_widget)

            row_total = QLabel('0 câu')
            row_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_total.setStyleSheet('font-weight: bold; font-size: 11px; color: #94a3b8;')
            self.grid_row_totals[qtype] = row_total
            self.matrix_grid.setCellWidget(row_idx, 5, row_total)

        grid_layout.addWidget(self.matrix_grid)

        # Thanh hành động lưu vào ma trận đề
        grid_action_bar = QHBoxLayout()
        self.grid_summary_lbl = QLabel('🎯 Đang chọn: 0 câu cho phạm vi này')
        self.grid_summary_lbl.setStyleSheet('font-weight: bold; color: #0284c7; font-size: 12px;')
        grid_action_bar.addWidget(self.grid_summary_lbl, 1)

        self.btn_save_grid = QPushButton('➕ Lưu vào bảng ma trận đề')
        self.btn_save_grid.setProperty('primary', True)
        self.btn_save_grid.setIcon(icon('chapter', '#ffffff'))
        self.btn_save_grid.clicked.connect(self.save_grid_to_matrix)
        grid_action_bar.addWidget(self.btn_save_grid)

        btn_reset_grid = QPushButton('🧹 Đặt lại (0)')
        btn_reset_grid.clicked.connect(self.reset_grid_spins)
        grid_action_bar.addWidget(btn_reset_grid)
        grid_layout.addLayout(grid_action_bar)

        box.addWidget(grid_box)

        # Backward compatibility widgets for existing tests
        self.question_type = QComboBox()
        for text, value in [('Tất cả loại', ''), ('Trắc nghiệm', 'mcq'), ('Đúng / sai', 'true_false'), ('Trả lời ngắn', 'short_answer'), ('Tự luận', 'essay')]:
            self.question_type.addItem(text, value)
        self.question_type.hide()

        self.stats = QTableWidget(4, 3)
        self.stats.setHorizontalHeaderLabels(['Mức độ', 'Có thể lấy', 'Cần lấy'])
        self.targets = {}
        for i, (level, label) in enumerate(levels_list):
            self.stats.setItem(i, 0, QTableWidgetItem(label))
            spin = QSpinBox()
            spin.setRange(0, 500)
            self.targets[level] = spin
            self.stats.setCellWidget(i, 2, spin)
            spin.valueChanged.connect(self.update_shortage)
        self.stats.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stats.hide()

        self.stats_note = QLabel()
        self.stats_note.setWordWrap(True)
        box.addWidget(self.stats_note)

        self.shortage = QLabel()
        self.shortage.setWordWrap(True)
        box.addWidget(self.shortage)

        # Bảng ma trận đề thi chính
        matrix_header_box = QHBoxLayout()
        matrix_title = QLabel('BẢNG MA TRẬN ĐẶC TẢ ĐỀ THI')
        matrix_title.setStyleSheet('font-weight: bold; font-size: 11px; color: #4ba3eb;')
        matrix_header_box.addWidget(matrix_title, 1)

        btn_clear_matrix = QPushButton('🧹 Xóa toàn bộ ma trận')
        btn_clear_matrix.clicked.connect(self.clear_matrix)
        matrix_header_box.addWidget(btn_clear_matrix)
        box.addLayout(matrix_header_box)

        self.matrix = QTableWidget(0, 7)
        self.matrix.setHorizontalHeaderLabels(['Môn', 'Khối', 'Loại', 'Mức độ', 'Số câu', 'Phạm vi CSDL (Bài/Dạng)', 'Sẵn có'])
        self.matrix.horizontalHeader().setMinimumSectionSize(45)
        self.matrix.setColumnWidth(5, 180)
        for i in (0, 1, 2, 3, 4, 6):
            self.matrix.setColumnWidth(i, 75)
        self.matrix.horizontalHeader().setStretchLastSection(True)
        box.addWidget(self.matrix, 1)

        self.matrix_summary = QLabel('Ma trận: 0 câu')
        self.matrix_summary.setWordWrap(True)
        box.addWidget(self.matrix_summary)
        self.matrix.itemChanged.connect(self.update_matrix_summary)

        # ------------------ CỘT PHẢI: CÂU ĐÃ CHỌN & XEM TRƯỚC ------------
        right = QWidget()
        rb = QVBoxLayout(right)
        rb.setContentsMargins(0, 0, 0, 0)
        rb.addWidget(QLabel('CÂU ĐÃ CHỌN THỦ CÔNG'))
        self.chosen = QListWidget()
        self.chosen.setMinimumWidth(220)
        self.chosen.setMaximumHeight(240)
        rb.addWidget(self.chosen)

        self.preview = QuestionPreview(services, run_job)
        rb.addWidget(self.preview, 1)
        self.workspace.addWidget(right)
        self.workspace.setSizes([230, 760, 360])
        self.chosen.currentRowChanged.connect(self.preview_selected)

        nav_box_1 = QHBoxLayout()
        btn_back_step0 = QPushButton('‹ Quay lại: Thông tin đề')
        btn_back_step0.clicked.connect(lambda: self.set_exam_step(0))
        nav_box_1.addWidget(btn_back_step0)
        nav_box_1.addStretch()
        btn_to_step2 = QPushButton('Tiếp tục: Cấu hình xáo đề ›')
        btn_to_step2.setProperty('primary', True)
        btn_to_step2.clicked.connect(lambda: self.set_exam_step(2))
        nav_box_1.addWidget(btn_to_step2)
        p1_box.addLayout(nav_box_1)

        self.bank_step_stack.addWidget(page_select)

        # =========================================================================
        # ------------------ BƯỚC 3: CẤU HÌNH & TẠO ĐỀ THI -----------------------
        # =========================================================================
        page_config = QWidget()
        p2_box = QVBoxLayout(page_config)
        p2_box.setContentsMargins(16, 16, 16, 16)
        p2_box.setSpacing(14)

        config_header = QLabel('BƯỚC 3: CẤU HÌNH XÁO TRỘN & BẮT ĐẦU TẠO ĐỀ (RÚT NGẪU NHIÊN THEO MA TRẬN)')
        config_header.setStyleSheet('font-weight: bold; font-size: 14px; color: #4ba3eb;')
        p2_box.addWidget(config_header)

        shuffle_group = QGroupBox('Tùy chọn xáo trộn đề thi (Chuẩn hóa 4 phần Phase K)')
        shuffle_layout = QVBoxLayout(shuffle_group)
        self.shuffle_questions = QCheckBox('Xáo trộn thứ tự các câu hỏi độc lập trong từng phần')
        self.shuffle_questions.setChecked(True)
        shuffle_layout.addWidget(self.shuffle_questions)
        self.shuffle_options = QCheckBox('Xáo trộn các phương án A, B, C, D ở Phần I (tự động giữ đúng đáp án \\True)')
        self.shuffle_options.setToolTip('Giữ đúng đáp án khi xáo')
        self.shuffle_options.setChecked(True)
        shuffle_layout.addWidget(self.shuffle_options)
        note_lbl = QLabel('📌 Bất biến cấu trúc: Phần II (Đúng/Sai) giữ nguyên 4 mệnh đề a, b, c, d; Phần IV (Tự luận) giữ nguyên thứ tự câu; Câu hỏi không bao giờ nhảy giữa các phần.')
        note_lbl.setStyleSheet('color: #64748b; font-size: 11px; font-style: italic;')
        note_lbl.setWordWrap(True)
        shuffle_layout.addWidget(note_lbl)
        p2_box.addWidget(shuffle_group)

        summary_group = QGroupBox('Tóm tắt cấu trúc đề thi sẽ tạo')
        sum_form = QFormLayout(summary_group)
        self.sum_title_lbl = QLabel()
        sum_form.addRow('Tên đề:', self.sum_title_lbl)
        self.sum_header_lbl = QLabel()
        sum_form.addRow('Tiêu đề \\TieudeT:', self.sum_header_lbl)
        self.sum_seed_lbl = QLabel()
        sum_form.addRow('Mã seed tái lập:', self.sum_seed_lbl)
        self.sum_count_lbl = QLabel()
        sum_form.addRow('Số lượng câu hỏi:', self.sum_count_lbl)
        self.sum_matrix_detail_lbl = QLabel()
        self.sum_matrix_detail_lbl.setWordWrap(True)
        sum_form.addRow('Chi tiết ma trận:', self.sum_matrix_detail_lbl)
        p2_box.addWidget(summary_group)

        generate_card = QFrame()
        generate_card.setObjectName('generateCard')
        generate_card.setStyleSheet('background-color: rgba(75, 163, 235, 0.08); border-radius: 8px; padding: 14px;')
        gc_layout = QVBoxLayout(generate_card)
        self.big_generate_btn = QPushButton('🚀 BẮT ĐẦU TẠO ĐỀ THI (RÚT NGẪU NHIÊN THEO MA TRẬN)')
        self.big_generate_btn.setStyleSheet('font-size: 14px; font-weight: bold; padding: 12px 24px;')
        self.big_generate_btn.setProperty('primary', True)
        self.big_generate_btn.clicked.connect(self.submitted.emit)
        gc_layout.addWidget(self.big_generate_btn)
        self.generate_status_lbl = QLabel('Hệ thống sẽ dựa vào bảng ma trận đề để lấy ngẫu nhiên số câu hỏi tương ứng theo từng bài, dạng, định dạng câu và mức độ.')
        self.generate_status_lbl.setWordWrap(True)
        gc_layout.addWidget(self.generate_status_lbl)
        p2_box.addWidget(generate_card)
        p2_box.addStretch()

        nav_box_2 = QHBoxLayout()
        btn_back_step1 = QPushButton('‹ Quay lại: Chọn câu hỏi & Ma trận')
        btn_back_step1.clicked.connect(lambda: self.set_exam_step(1))
        nav_box_2.addWidget(btn_back_step1)
        nav_box_2.addStretch()
        self.btn_to_step3 = QPushButton('Tiếp tục: Xem trước đề thi ›')
        self.btn_to_step3.setProperty('primary', True)
        self.btn_to_step3.clicked.connect(lambda: self.set_exam_step(3))
        nav_box_2.addWidget(self.btn_to_step3)
        p2_box.addLayout(nav_box_2)

        self.bank_step_stack.addWidget(page_config)

        # =========================================================================
        # ------------------ BƯỚC 4: XEM TRƯỚC ĐỀ THI ----------------------------
        # =========================================================================
        page_preview = QWidget()
        p3_box = QVBoxLayout(page_preview)
        p3_box.setContentsMargins(10, 10, 10, 10)
        p3_box.setSpacing(8)

        prev_header = QLabel('BƯỚC 4: XEM TRƯỚC VÀ KIỂM TRA ĐỀ THI ĐÃ TẠO')
        prev_header.setStyleSheet('font-weight: bold; font-size: 14px; color: #4ba3eb;')
        p3_box.addWidget(prev_header)

        self.preview_desc_lbl = QLabel('Chưa có đề thi nào được tạo. Vui lòng bấm Bắt đầu tạo đề thi ở Bước 3.')
        self.preview_desc_lbl.setWordWrap(True)
        p3_box.addWidget(self.preview_desc_lbl)

        preview_split = QSplitter(Qt.Orientation.Horizontal)
        p3_left = QWidget()
        p3l_box = QVBoxLayout(p3_left)
        p3l_box.setContentsMargins(0, 0, 0, 0)
        p3l_box.addWidget(QLabel('Danh sách câu hỏi đã rút từ ma trận:'))
        self.snapshot_chosen = QListWidget()
        self.snapshot_chosen.currentRowChanged.connect(self._preview_snapshot_item)
        p3l_box.addWidget(self.snapshot_chosen, 1)
        self.duplicate_warning_lbl = QLabel()
        self.duplicate_warning_lbl.setWordWrap(True)
        p3l_box.addWidget(self.duplicate_warning_lbl)
        preview_split.addWidget(p3_left)

        p3_right = QWidget()
        p3r_box = QVBoxLayout(p3_right)
        p3r_box.setContentsMargins(0, 0, 0, 0)
        p3r_box.addWidget(QLabel('Xem trước chi tiết câu:'))
        self.snapshot_preview = QuestionPreview(services, run_job)
        p3r_box.addWidget(self.snapshot_preview, 1)
        preview_split.addWidget(p3_right)
        preview_split.setSizes([400, 600])
        p3_box.addWidget(preview_split, 1)

        nav_box_3 = QHBoxLayout()
        btn_back_step2 = QPushButton('‹ Quay lại: Cấu hình xáo đề')
        btn_back_step2.clicked.connect(lambda: self.set_exam_step(2))
        nav_box_3.addWidget(btn_back_step2)
        nav_box_3.addStretch()
        btn_to_step4 = QPushButton('Tiếp tục: Xuất đề thi ›')
        btn_to_step4.setProperty('primary', True)
        btn_to_step4.clicked.connect(lambda: self.set_exam_step(4))
        nav_box_3.addWidget(btn_to_step4)
        p3_box.addLayout(nav_box_3)

        self.bank_step_stack.addWidget(page_preview)

        # =========================================================================
        # ------------------ BƯỚC 5: XUẤT ĐỀ THI & BIÊN DỊCH ---------------------
        # =========================================================================
        page_export = QWidget()
        p4_box = QVBoxLayout(page_export)
        p4_box.setContentsMargins(16, 14, 16, 14)
        p4_box.setSpacing(10)

        exp_header = QLabel('BƯỚC 5: XUẤT BẢN VÀ BIÊN DỊCH ĐỀ THI (PDF SẴN SÀNG IN / GÓI TỰ TRỊ)')
        exp_header.setStyleSheet('font-weight: bold; font-size: 15px; color: #4ba3eb;')
        p4_box.addWidget(exp_header)
        exp_subtitle = QLabel('Biên dịch trực tiếp ra PDF in ngay hoặc đóng gói trọn gói TeX + MAPClass.cls + ex_test.sty + Assets để biên dịch 100% thành công trên mọi máy tính.')
        exp_subtitle.setStyleSheet('color: #94a3b8; font-size: 12px;')
        exp_subtitle.setWordWrap(True)
        p4_box.addWidget(exp_subtitle)

        # Khung thông tin đề thi
        exp_group = QGroupBox('Thông tin đề thi sẵn sàng xuất')
        exp_form = QFormLayout(exp_group)
        exp_form.setContentsMargins(12, 8, 12, 8)
        exp_form.setVerticalSpacing(4)
        self.export_info_title = QLabel()
        self.export_info_title.setStyleSheet('font-weight: bold; color: #38bdf8;')
        exp_form.addRow('Tên đề thi:', self.export_info_title)
        self.export_info_count = QLabel()
        exp_form.addRow('Tổng số câu:', self.export_info_count)
        self.export_info_seed = QLabel()
        exp_form.addRow('Mã seed tái lập:', self.export_info_seed)
        self.export_info_header = QLabel()
        exp_form.addRow('Tiêu đề chuẩn:', self.export_info_header)
        p4_box.addWidget(exp_group)

        # Hai cột: Cột 1 chọn tài liệu, Cột 2 chọn định dạng & phương thức
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(12)

        # Cột 1: Chọn tài liệu cần xuất
        doc_group = QGroupBox('1. Chọn tài liệu cần xuất')
        doc_layout = QVBoxLayout(doc_group)
        doc_layout.setSpacing(6)
        self.chk_exp_student = QCheckBox('Đề thi học sinh (Ẩn lời giải và đáp án)')
        self.chk_exp_student.setChecked(True)
        doc_layout.addWidget(self.chk_exp_student)
        self.chk_exp_teacher = QCheckBox('Đề thi giáo viên (Hiện lời giải và đáp án)')
        self.chk_exp_teacher.setChecked(True)
        doc_layout.addWidget(self.chk_exp_teacher)
        self.chk_exp_answers = QCheckBox('Bảng tra cứu đáp án trắc nghiệm')
        self.chk_exp_answers.setChecked(True)
        doc_layout.addWidget(self.chk_exp_answers)
        lbl_hint = QLabel('💡 Có thể chọn đồng thời để xuất cùng lúc nhiều bản.')
        lbl_hint.setStyleSheet('color: #64748b; font-size: 11px; font-style: italic;')
        doc_layout.addWidget(lbl_hint)
        doc_layout.addStretch()
        columns_layout.addWidget(doc_group, 1)

        # Cột 2: Chọn định dạng & Phương thức
        fmt_group = QGroupBox('2. Định dạng và Phương thức xuất')
        fmt_layout = QVBoxLayout(fmt_group)
        fmt_layout.setSpacing(6)
        self.rad_fmt_pdf = QRadioButton('📄 Xuất PDF hoàn chỉnh (Khuyên dùng - In ấn ngay)')
        self.rad_fmt_pdf.setToolTip('Phần mềm tự gọi pdfLaTeX biên dịch ra file PDF chất lượng cao, sẵn sàng in hoặc gửi học sinh.')
        self.rad_fmt_pdf.setChecked(True)
        fmt_layout.addWidget(self.rad_fmt_pdf)

        self.rad_fmt_bundle = QRadioButton('📁 Xuất Thư mục Trọn Gói tự trị (Khuyên dùng để lưu trữ và sửa TeX)')
        self.rad_fmt_bundle.setToolTip('Tạo thư mục đầy đủ gồm file PDF + file TeX + MAPClass.cls + ex_test.sty + Assets + file bat tự biên dịch.')
        fmt_layout.addWidget(self.rad_fmt_bundle)

        self.rad_fmt_zip = QRadioButton('🗜 Xuất Gói ZIP Portable (Tải lên Overleaf hoặc chia sẻ)')
        self.rad_fmt_zip.setToolTip('Nén toàn bộ thư mục bundle thành file .zip để kéo thả lên Overleaf hoặc gửi đồng nghiệp.')
        fmt_layout.addWidget(self.rad_fmt_zip)

        self.rad_fmt_tex = QRadioButton('📝 Xuất File TeX Độc Lập (.tex Standalone)')
        self.rad_fmt_tex.setToolTip('File .tex đơn lẻ kèm Preamble siêu tương thích mọi máy tính.')
        fmt_layout.addWidget(self.rad_fmt_tex)
        columns_layout.addWidget(fmt_group, 1)

        p4_box.addLayout(columns_layout)

        # Khung phong cách LaTeX
        style_group = QGroupBox('3. Phong cách giao diện LaTeX')
        style_layout = QHBoxLayout(style_group)
        style_layout.setContentsMargins(12, 6, 12, 6)
        self.rad_style_mapclass = QRadioButton('Chuẩn Bộ GD&ĐT (Lớp MAPClass, tiêu đề \\TieudeT - Tự động đóng gói kèm file class)')
        self.rad_style_mapclass.setChecked(True)
        style_layout.addWidget(self.rad_style_mapclass)
        self.rad_style_article = QRadioButton('Chuẩn Độc Lập (Lớp Article - Siêu tương thích, tự chứa mọi macro)')
        style_layout.addWidget(self.rad_style_article)
        p4_box.addWidget(style_group)

        # Nút hành động chính
        export_btn_row = QHBoxLayout()
        self.big_export_btn = QPushButton('🚀 TIẾN HÀNH XUẤT VÀ BIÊN DỊCH')
        self.big_export_btn.setStyleSheet('font-size: 14px; font-weight: bold; padding: 10px 20px;')
        self.big_export_btn.setProperty('primary', True)
        self.big_export_btn.clicked.connect(self.start_export_process)
        export_btn_row.addWidget(self.big_export_btn, 3)

        self.btn_cancel_export = QPushButton('⛔ Hủy thao tác xuất')
        self.btn_cancel_export.setStyleSheet('font-size: 13px; padding: 10px 16px;')
        self.btn_cancel_export.setVisible(False)
        self.btn_cancel_export.clicked.connect(self._cancel_export_process)
        export_btn_row.addWidget(self.btn_cancel_export, 1)
        p4_box.addLayout(export_btn_row)

        # Khung Kết quả & Thao tác sau khi xuất
        self.export_result_card = QFrame()
        self.export_result_card.setStyleSheet('background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;')
        res_layout = QVBoxLayout(self.export_result_card)
        res_layout.setContentsMargins(10, 8, 10, 8)
        res_layout.setSpacing(6)

        self.export_status_lbl = QLabel('Sẵn sàng xuất đề thi. Chọn các tùy chọn trên và nhấn nút để bắt đầu.')
        self.export_status_lbl.setStyleSheet('color: #334155; font-size: 12px;')
        res_layout.addWidget(self.export_status_lbl)

        self.export_progress_bar = QProgressBar()
        self.export_progress_bar.setVisible(False)
        self.export_progress_bar.setFixedHeight(8)
        res_layout.addWidget(self.export_progress_bar)

        self.export_path_lbl = QLabel()
        self.export_path_lbl.setWordWrap(True)
        self.export_path_lbl.setVisible(False)
        res_layout.addWidget(self.export_path_lbl)

        actions_row = QHBoxLayout()
        self.btn_open_pdf = QPushButton('📄 Mở file PDF ngay')
        self.btn_open_pdf.setProperty('primary', True)
        self.btn_open_pdf.setVisible(False)
        self.btn_open_pdf.clicked.connect(self._open_exported_pdf)
        actions_row.addWidget(self.btn_open_pdf)

        self.btn_open_folder = QPushButton('📁 Mở thư mục chứa')
        self.btn_open_folder.setVisible(False)
        self.btn_open_folder.clicked.connect(self._open_exported_folder)
        actions_row.addWidget(self.btn_open_folder)

        self.btn_open_tex = QPushButton('📝 Mở file TeX')
        self.btn_open_tex.setVisible(False)
        self.btn_open_tex.clicked.connect(self._open_exported_tex)
        actions_row.addWidget(self.btn_open_tex)

        self.btn_view_log = QPushButton('🔍 Xem chi tiết lỗi (Log)')
        self.btn_view_log.setVisible(False)
        self.btn_view_log.clicked.connect(self._view_export_log)
        actions_row.addWidget(self.btn_view_log)
        actions_row.addStretch()

        res_layout.addLayout(actions_row)
        p4_box.addWidget(self.export_result_card)

        # Điều hướng dưới cùng
        nav_box_4 = QHBoxLayout()
        btn_back_step3 = QPushButton('‹ Quay lại: Xem trước đề thi')
        btn_back_step3.clicked.connect(lambda: self.set_exam_step(3))
        nav_box_4.addWidget(btn_back_step3)
        nav_box_4.addStretch()
        btn_restart = QPushButton('🔄 Tạo đề thi mới từ đầu')
        btn_restart.clicked.connect(lambda: self.set_exam_step(0))
        nav_box_4.addWidget(btn_restart)
        p4_box.addLayout(nav_box_4)

        self.bank_step_stack.addWidget(page_export)

        # ------------------ KHỞI TẠO DỮ LIỆU CÂY CSDL ---------------------------
        self.nodes = []
        self.tree_items = {}
        if services:
            from latex_question_studio.application.library import LibraryService
            self.nodes = LibraryService(services).taxonomy()
            self._build_tree()

        self.set_manual_ids(manual_ids)
        if services:
            self.refresh_statistics()

        from latex_question_studio.ui.tex_exam_page import TexExamPage
        self.tex_page = TexExamPage(services, run_job, self)
        self.mode_stack.addWidget(self.tex_page)
        self.modes.currentChanged.connect(self._handle_mode_change)

        self.exam_steps.currentRowChanged.connect(self.set_exam_step)
        self.set_exam_step(0)

    # -------------------------------------------------------------------------
    # HÀM XÂY DỰNG VÀ LỌC CÂY CSDL
    # -------------------------------------------------------------------------
    def _build_tree(self):
        self.tree.clear()
        self.tree_items = {}
        items = {n['id']: QTreeWidgetItem([n['name'] + (f" ({n.get('count', n.get('question_count', 0))})" if n.get('count', n.get('question_count', 0)) else '')]) for n in self.nodes}
        all_item = QTreeWidgetItem(['Toàn ngân hàng'])
        self.tree.addTopLevelItem(all_item)

        kind_icons = {
            'subject': ('subject', '#4ba3eb'),
            'grade': ('subject', '#4ba3eb'),
            'chapter': ('chapter', '#e7ad4b'),
            'lesson': ('topic', '#55bca3'),
            'topic': ('topic', '#55bca3'),
            'method': ('topic', '#55bca3')
        }

        for n in self.nodes:
            item = items[n['id']]
            item.setData(0, Qt.ItemDataRole.UserRole, n['id'])
            ic_name, ic_color = kind_icons.get(n['kind'], ('topic', '#579bd4'))
            item.setIcon(0, icon(ic_name, ic_color))
            items.get(n['parent_id'], all_item).addChild(item)
            if n.get('count', n.get('question_count', 0)) > 0 and n.get('kind') in ('subject', 'grade', 'chapter'):
                item.setExpanded(True)

        all_item.setExpanded(True)
        self.tree_items = items

    def toggle_tree_panel(self):
        if not hasattr(self, 'tree_panel'):
            return
        if self.tree_panel.isVisible():
            self.tree_panel.setVisible(False)
        else:
            self.ensure_tree_visible()

    def ensure_tree_visible(self):
        if hasattr(self, 'tree_panel'):
            self.tree_panel.setVisible(True)
            sizes = self.workspace.sizes()
            if len(sizes) == 3 and sizes[0] < 200:
                total = sum(sizes) if sum(sizes) > 600 else 1280
                self.workspace.setSizes([230, max(600, total - 590), 360])

    def _collapse_tree_all(self):
        all_item = self.tree.topLevelItem(0)
        if all_item:
            for i in range(all_item.childCount()):
                all_item.child(i).setExpanded(False)

    def _expand_tree_all(self):
        all_item = self.tree.topLevelItem(0)
        if all_item:
            all_item.setExpanded(True)
            for i in range(all_item.childCount()):
                child = all_item.child(i)
                child.setExpanded(True)
                for j in range(child.childCount()):
                    child.child(j).setExpanded(True)

    def _sync_tree_to_current_subject(self):
        if not hasattr(self, 'subject_input') or not hasattr(self, 'tree'):
            return
        subj = self.subject_input.currentText().strip()
        all_item = self.tree.topLevelItem(0)
        if not all_item:
            return
        all_item.setExpanded(True)
        if subj:
            for i in range(all_item.childCount()):
                child = all_item.child(i)
                txt = child.text(0).upper()
                if subj.upper() in txt:
                    child.setExpanded(True)
                    for j in range(child.childCount()):
                        grandchild = child.child(j)
                        if grandchild.childCount() > 0:
                            grandchild.setExpanded(True)

    def showEvent(self, event):
        super().showEvent(event)
        self.ensure_tree_visible()

    def _filter_tree_by_subject(self, index):
        subj = self.subject_filter.currentData()
        all_item = self.tree.topLevelItem(0)
        if not all_item:
            return
        for i in range(all_item.childCount()):
            child = all_item.child(i)
            if not subj:
                child.setHidden(False)
            else:
                txt = child.text(0).upper()
                child.setHidden(subj.upper() not in txt)

    def _filter_tree_search(self, text):
        query = text.strip().lower()
        all_item = self.tree.topLevelItem(0)
        if not all_item:
            return

        def filter_item(item):
            match = query in item.text(0).lower() if query else True
            child_matches = False
            for i in range(item.childCount()):
                if filter_item(item.child(i)):
                    child_matches = True
            is_visible = match or child_matches
            item.setHidden(not is_visible)
            if query and child_matches:
                item.setExpanded(True)
            return is_visible

        for i in range(all_item.childCount()):
            filter_item(all_item.child(i))

    def _sync_header_preview(self):
        self.tieudet_preview.update_header(
            self.title.text(),
            self.subject_input.currentText(),
            self.grade_input.currentText(),
            self.duration_input.currentText(),
            self.school_input.text(),
            self.exam_code_input.text()
        )
        self.update_step_summaries()

    def _handle_mode_change(self, index):
        self.mode_stack.setCurrentIndex(index)
        self.exam_steps.setVisible(index == 0)

    def set_exam_step(self, index):
        index = max(0, min(index, self.bank_step_stack.count() - 1))
        self.exam_steps.blockSignals(True)
        self.exam_steps.setCurrentRow(index)
        self.exam_steps.blockSignals(False)
        self.bank_step_stack.setCurrentIndex(index)
        self.update_step_summaries()
        if index == 1:
            self.ensure_tree_visible()
            self._sync_tree_to_current_subject()

    def update_step_summaries(self):
        title = self.title.text() or 'Đề kiểm tra'
        seed_val = str(self.seed.value())
        manual_count = len(self.manual_ids)
        matrix_count = 0
        if hasattr(self, 'matrix'):
            matrix_count = sum(int(self.matrix.item(i, 4).text() or 0) for i in range(self.matrix.rowCount()) if self.matrix.item(i, 4))
        total_count = manual_count + matrix_count

        subj = self.subject_input.currentText() if hasattr(self, 'subject_input') else 'TOÁN'
        grd = self.grade_input.currentText() if hasattr(self, 'grade_input') else ''
        dur = self.duration_input.currentText() if hasattr(self, 'duration_input') else '90 phút'
        sch = self.school_input.text() if hasattr(self, 'school_input') else ''
        code = self.exam_code_input.text() if hasattr(self, 'exam_code_input') else '101'

        if hasattr(self, 'sum_title_lbl'):
            self.sum_title_lbl.setText(title)
            self.sum_header_lbl.setText(f"{sch} • Môn: {subj} ({grd}) • Thời gian: {dur} • Mã đề: {code}")
            self.sum_seed_lbl.setText(seed_val)
            self.sum_count_lbl.setText(f'{total_count} câu ({manual_count} câu chọn thủ công + {matrix_count} câu theo ma trận)')
            self.sum_matrix_detail_lbl.setText(self.matrix_summary.text() if hasattr(self, 'matrix_summary') else '')

        if hasattr(self, 'export_info_title'):
            self.export_info_title.setText(title)
            self.export_info_count.setText(f'{len(self.snapshot["questions"]) if self.snapshot else total_count} câu hỏi')
            self.export_info_seed.setText(seed_val)
            self.export_info_header.setText(f"{sch} • {subj} • Mã đề: {code}")

    # -------------------------------------------------------------------------
    # KHUNG THỐNG KÊ 4x4 VÀ LƯU VÀO MA TRẬN
    # -------------------------------------------------------------------------
    def _update_grid_selection_summary(self):
        types = ('mcq', 'true_false', 'short_answer', 'essay')
        levels = ('NB', 'TH', 'VD', 'VDC')
        counts_by_type = {}
        total = 0

        for t in types:
            t_sum = sum(self.grid_spins.get((t, lvl), QSpinBox()).value() for lvl in levels)
            counts_by_type[t] = t_sum
            total += t_sum
            if t in self.grid_row_totals:
                self.grid_row_totals[t].setText(f'{t_sum} câu')
                self.grid_row_totals[t].setStyleSheet('font-weight: bold; font-size: 11px; color: #38bdf8;' if t_sum else 'font-size: 11px; color: #94a3b8;')

        details = [f"{QTYPE_LABEL_MAP[t]}: {counts_by_type[t]}" for t in types if counts_by_type[t]]
        desc = f"🎯 Đang chọn: {total} câu" + (f" ({' · '.join(details)})" if details else "")
        self.grid_summary_lbl.setText(desc)
        self.btn_save_grid.setText(f"➕ Lưu {total} câu vào bảng ma trận đề" if total else "➕ Lưu vào bảng ma trận đề")

    def reset_grid_spins(self):
        for spin in self.grid_spins.values():
            spin.blockSignals(True)
            spin.setValue(0)
            spin.blockSignals(False)
        self._update_grid_selection_summary()

    def save_grid_to_matrix(self):
        """Lưu toàn bộ các ô đã chọn trong lưới 4x4 vào Bảng ma trận đề."""
        from latex_question_studio.domain.curriculum import classification, breadcrumb
        values = classification(self.nodes, self.scope)
        subj = values.get('subject', self.subject_input.currentText())
        grd = values.get('grade', self.grade_input.currentText())
        scope_title = breadcrumb(self.nodes, self.scope) or 'Toàn ngân hàng'

        added = 0
        types = [('mcq', 'Trắc nghiệm'), ('true_false', 'Đúng / sai'), ('short_answer', 'Trả lời ngắn'), ('essay', 'Tự luận')]
        levels = [('NB', 'NB'), ('TH', 'TH'), ('VD', 'VD'), ('VDC', 'VDC')]

        for qtype, qname in types:
            for lvl, lvl_name in levels:
                spin = self.grid_spins.get((qtype, lvl))
                if not spin or spin.value() <= 0:
                    continue
                count = spin.value()
                avail = 0
                if self.matrix_available and qtype in self.matrix_available.get('matrix', {}):
                    avail = self.matrix_available['matrix'][qtype].get(lvl, 0)

                # Kiểm tra hàng trùng cùng scope + qtype + lvl trong matrix để cập nhật
                found_row = None
                for r in range(self.matrix.rowCount()):
                    r_scope_id = self.matrix.item(r, 5).data(Qt.ItemDataRole.UserRole) if self.matrix.item(r, 5) else None
                    r_type = self.matrix.item(r, 2).text() if self.matrix.item(r, 2) else ''
                    r_lvl = self.matrix.item(r, 3).text() if self.matrix.item(r, 3) else ''
                    if r_scope_id == self.scope and r_type == qname and r_lvl == lvl:
                        found_row = r
                        break

                if found_row is not None:
                    # Cộng dồn
                    cur = int(self.matrix.item(found_row, 4).text() or 0)
                    self.matrix.item(found_row, 4).setText(str(cur + count))
                else:
                    self.add_row()
                    row_idx = self.matrix.rowCount() - 1
                    texts = [subj, grd, qname, lvl, str(count), scope_title, str(avail)]
                    for col_idx, txt in enumerate(texts):
                        self.matrix.item(row_idx, col_idx).setText(txt)
                        self.matrix.item(row_idx, col_idx).setToolTip(txt)
                    self.matrix.item(row_idx, 5).setData(Qt.ItemDataRole.UserRole, self.scope)
                    self.matrix.item(row_idx, 5).setFlags(self.matrix.item(row_idx, 5).flags() & ~Qt.ItemFlag.ItemIsEditable)

                added += count

        self.reset_grid_spins()
        self.update_matrix_summary()

    def clear_matrix(self):
        self.matrix.setRowCount(0)
        self.update_matrix_summary()

    def update_shortage(self, *args):
        if not self.available:
            return
        missing = [f'{level}: thiếu {spin.value() - self.available["counts"][level]}' for level, spin in self.targets.items() if spin.value() > self.available['counts'][level]]
        self.shortage.setText(' · '.join(missing) if missing else 'Nguồn đáp ứng số lượng đang chọn trong phạm vi này.')
        self.shortage.setStyleSheet('color:#d88a37' if missing else '')

    def show_snapshot(self, snapshot):
        from latex_question_studio.ui.pages.library import readable
        self.snapshot = snapshot
        self.chosen.blockSignals(True)
        self.chosen.clear()
        self.snapshot_chosen.blockSignals(True)
        self.snapshot_chosen.clear()
        part_counts = {'mcq': 0, 'true_false': 0, 'short_answer': 0, 'essay': 0}
        for i, q in enumerate(snapshot['questions'], 1):
            q_type = q.get('question_type')
            if not q_type:
                ans = q.get('answer', {})
                if 'correct_letter' in ans: q_type = 'mcq'
                elif 'truth' in ans: q_type = 'true_false'
                elif 'value' in ans: q_type = 'short_answer'
                else: q_type = 'essay'
            part_counts[q_type] = part_counts.get(q_type, 0) + 1
            part_prefix = {
                'mcq': '[Phần I - MCQ] ',
                'true_false': '[Phần II - Đúng/Sai] ',
                'short_answer': '[Phần III - TL Ngắn] ',
                'essay': '[Phần IV - Tự luận] '
            }.get(q_type, '')
            text = f'{part_prefix}Câu {i}. ' + readable(q['source'])[:90]
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, i - 1)
            self.chosen.addItem(text)
            self.snapshot_chosen.addItem(item)
        self.chosen.blockSignals(False)
        self.snapshot_chosen.blockSignals(False)

        warnings = snapshot.get('duplicate_warnings', [])
        if warnings:
            self.duplicate_warning_lbl.setText(f"⚠️ Phát hiện {len(warnings)} cặp câu hỏi trùng/gần trùng cần kiểm tra.")
            self.duplicate_warning_lbl.setStyleSheet('color: #d88a37; font-weight: bold;')
        else:
            self.duplicate_warning_lbl.setText('✓ Không có cảnh báo trùng lặp nào.')
            self.duplicate_warning_lbl.setStyleSheet('color: #55bca3;')

        details = []
        if part_counts.get('mcq'): details.append(f"Phần I: {part_counts['mcq']} câu")
        if part_counts.get('true_false'): details.append(f"Phần II: {part_counts['true_false']} câu")
        if part_counts.get('short_answer'): details.append(f"Phần III: {part_counts['short_answer']} câu")
        if part_counts.get('essay'): details.append(f"Phần IV: {part_counts['essay']} câu")
        details_str = f" ({', '.join(details)})" if details else ""
        self.preview_desc_lbl.setText(f"Đề thi: {snapshot.get('title', 'Đề kiểm tra')} • Tổng {len(snapshot['questions'])} câu hỏi{details_str}.")
        if self.chosen.count():
            self.chosen.setCurrentRow(0)
        if self.snapshot_chosen.count():
            self.snapshot_chosen.setCurrentRow(0)
        self.update_step_summaries()

    def _preview_snapshot_item(self, index):
        if index < 0 or not self.snapshot or index >= len(self.snapshot['questions']):
            self.snapshot_preview.set_source('')
            return
        item = self.snapshot_chosen.item(index)
        real_idx = item.data(Qt.ItemDataRole.UserRole) if item else index
        if real_idx is None or real_idx >= len(self.snapshot['questions']):
            real_idx = index
        q = self.snapshot['questions'][real_idx]
        self.snapshot_preview.set_source(q['source'], self.snapshot.get('assets', {}))

    def preview_selected(self, index):
        if index < 0:
            self.preview.set_source('')
            return
        if self.snapshot:
            q = self.snapshot['questions'][index]
            self.preview.set_source(q['source'], self.snapshot.get('assets', {}))
            return
        if not self.services or index >= len(self.manual_ids):
            return
        q = self.services.questions.get(self.manual_ids[index])
        if not q:
            return
        with self.services.database.connect() as c:
            assets = {r['original_reference']: self.services.config.data_dir / r['relative_path'] for r in c.execute('SELECT qa.original_reference, a.relative_path FROM question_assets qa JOIN assets a ON a.id=qa.asset_id WHERE qa.question_id=?', (q.id,))}
        self.preview.set_source(q.latex_source, assets)

    def set_manual_ids(self, ids):
        self.manual_ids = list(ids)
        self.snapshot = None
        if hasattr(self, 'chosen'):
            from latex_question_studio.ui.pages.library import readable
            self.chosen.blockSignals(True)
            self.chosen.clear()
            if self.services:
                for i, qid in enumerate(ids, 1):
                    q = self.services.questions.get(qid)
                    if q:
                        self.chosen.addItem(f'{i}. ' + readable(q.latex_source)[:100])
            self.chosen.blockSignals(False)
            self.preview.set_source('')
        self.selection_label.setText(f'Đã chọn {len(ids)} câu thủ công; các hàng ma trận bên dưới sẽ rút thêm câu không trùng.')
        if hasattr(self, 'stats'):
            self.refresh_statistics()
        self.update_step_summaries()

    def add_row(self):
        i = self.matrix.rowCount()
        self.matrix.insertRow(i)
        for j in range(7):
            self.matrix.setItem(i, j, QTableWidgetItem('1' if j == 4 else ''))
        self.update_matrix_summary()

    def values(self):
        rows = []
        for i in range(self.matrix.rowCount()):
            raw_vals = [self.matrix.item(i, j).text().strip() if self.matrix.item(i, j) else '' for j in range(5)]
            tax_item = self.matrix.item(i, 5)
            tax_id = tax_item.data(Qt.ItemDataRole.UserRole) if tax_item else None
            count_val = int(raw_vals[4]) if raw_vals[4].isdigit() else 1

            # Chuẩn hóa mã câu hỏi & mức độ nhận biết
            qtype_code = QTYPE_CODE_MAP.get(raw_vals[2], raw_vals[2])
            level_code = LEVEL_CODE_MAP.get(raw_vals[3], raw_vals[3])

            rows.append({
                'filters': {
                    'subject': raw_vals[0],
                    'grade': raw_vals[1],
                    'question_type': qtype_code,
                    'cognitive_level': level_code
                },
                'count': count_val,
                'taxonomy_id': tax_id,
                'scope_name': tax_item.text() if tax_item else ''
            })

        return dict(
            title=self.title.text(),
            subject=self.subject_input.currentText(),
            grade=self.grade_input.currentText(),
            duration=self.duration_input.currentText(),
            school=self.school_input.text(),
            exam_code=self.exam_code_input.text(),
            manual_ids=self.manual_ids,
            matrix=rows,
            seed=self.seed.value(),
            shuffle_questions=self.shuffle_questions.isChecked(),
            shuffle_options=self.shuffle_options.isChecked()
        )

    def select_scope(self, item, *args):
        self.scope = item.data(0, Qt.ItemDataRole.UserRole)
        from latex_question_studio.domain.curriculum import breadcrumb
        bc = breadcrumb(self.nodes, self.scope)
        self.scope_label.setText('📍 ' + (bc or 'Toàn ngân hàng'))
        self.refresh_statistics()

    def cancel_statistics(self):
        self.stats_generation += 1
        if self.stats_job:
            self.stats_job.cancelled.set()
        self.stats_job = None

    def refresh_statistics(self, *args):
        if not self.services:
            return
        from latex_question_studio.application.exams import ExamService
        self.cancel_statistics()
        generation = self.stats_generation
        scope = self.scope
        kind = self.question_type.currentData()
        manual = list(self.manual_ids)

        def fetch_data(cancelled):
            exam_svc = ExamService(self.services)
            stat_res = exam_svc.statistics(scope, kind, manual, cancelled)
            mat_res = None
            try:
                mat_res = exam_svc.matrix_statistics(scope, manual, cancelled)
            except Exception:
                pass
            return stat_res, mat_res

        def apply(payload):
            if generation != self.stats_generation:
                return
            self.stats_job = None
            stat_res, mat_res = payload
            self.available = stat_res
            self.scope_action.setEnabled(True)
            for i, level in enumerate(('NB', 'TH', 'VD', 'VDC')):
                self.stats.setItem(i, 1, QTableWidgetItem(str(stat_res['counts'][level])))
            self.update_shortage()
            self.stats_note.setText(f"Tổng {stat_res['total']} câu hợp lệ • {stat_res['counts']['unclassified']} chưa gán mức độ • {stat_res['invalid']} source lỗi không tính. Đã loại câu chọn thủ công.")

            if mat_res:
                self.matrix_available = mat_res
                mat = mat_res.get('matrix', {})
                types = ('mcq', 'true_false', 'short_answer', 'essay')
                levels = ('NB', 'TH', 'VD', 'VDC')
                for t in types:
                    t_data = mat.get(t, {})
                    for lvl in levels:
                        cnt = t_data.get(lvl, 0)
                        lbl = self.grid_avail_lbls.get((t, lvl))
                        spin = self.grid_spins.get((t, lvl))
                        if lbl:
                            lbl.setText(f"[{cnt}]")
                            if cnt > 0:
                                lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #0284c7; background: rgba(2, 132, 199, 0.08); border-radius: 3px; padding: 1px 2px;")
                                lbl.setToolTip(f"Có sẵn {cnt} câu trong CSDL. Bấm vào để chọn nhanh.")
                                lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                                if spin:
                                    lbl.mousePressEvent = (lambda s, c: lambda e: s.setValue(c if s.value() == 0 else 0))(spin, cnt)
                            else:
                                lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
                                lbl.setToolTip("Không có câu hỏi nào trong phạm vi này.")
                                lbl.setCursor(Qt.CursorShape.ArrowCursor)
                                lbl.mousePressEvent = None
            else:
                for t in ('mcq', 'true_false', 'short_answer', 'essay'):
                    for lvl in ('NB', 'TH', 'VD', 'VDC'):
                        cnt = stat_res['counts'].get(lvl, 0) if t == (kind or 'mcq') else 0
                        lbl = self.grid_avail_lbls.get((t, lvl))
                        spin = self.grid_spins.get((t, lvl))
                        if lbl:
                            lbl.setText(f"[{cnt}]")
                            if cnt > 0:
                                lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #0284c7; background: rgba(2, 132, 199, 0.08); border-radius: 3px; padding: 1px 2px;")
                                lbl.setToolTip(f"Có sẵn {cnt} câu trong CSDL. Bấm vào để chọn nhanh.")
                                lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                                if spin:
                                    lbl.mousePressEvent = (lambda s, c: lambda e: s.setValue(c if s.value() == 0 else 0))(spin, cnt)
                            else:
                                lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
                                lbl.setToolTip("Không có câu hỏi nào trong phạm vi này.")
                                lbl.setCursor(Qt.CursorShape.ArrowCursor)
                                lbl.mousePressEvent = None

        if not self.run_job:
            apply(fetch_data(lambda: False))
            return

        self.available = None
        self.matrix_available = None
        self.scope_action.setEnabled(False)
        self.stats_note.setText('Đang thống kê nguồn câu hỏi…')
        from latex_question_studio.ui.jobs import Job
        job = Job(lambda cancelled, progress: fetch_data(cancelled))
        self.stats_job = job
        job.signals.completed.connect(apply)

        def failed(message):
            if generation != self.stats_generation:
                return
            self.stats_job = None
            self.stats_note.setText('Thống kê đã dừng: ' + message)

        job.signals.failed.connect(failed)
        self.run_job(job)

    def closeEvent(self, event):
        self.cancel_statistics()
        self.preview.cancel()
        if hasattr(self, 'snapshot_preview'):
            self.snapshot_preview.cancel()
        self.tex_page.cancel_all()
        super().closeEvent(event)

    def add_scope_rows(self):
        from latex_question_studio.domain.curriculum import classification, breadcrumb
        values = classification(self.nodes, self.scope)
        if not self.run_job:
            self.refresh_statistics()
        if self.available is None:
            return
        for level, count in ((level, spin.value()) for level, spin in self.targets.items()):
            if not count:
                continue
            self.add_row()
            i = self.matrix.rowCount() - 1
            texts = [values.get('subject', ''), values.get('grade', ''), self.question_type.currentData(), level, str(count), breadcrumb(self.nodes, self.scope) or 'Toàn ngân hàng', str(self.available['counts'][level])]
            for j, text in enumerate(texts):
                self.matrix.item(i, j).setText(text)
                self.matrix.item(i, j).setToolTip(text)
            self.matrix.item(i, 5).setData(Qt.ItemDataRole.UserRole, self.scope)
            self.matrix.item(i, 5).setFlags(self.matrix.item(i, 5).flags() & ~Qt.ItemFlag.ItemIsEditable)
        for spin in self.targets.values():
            spin.setValue(0)
        self.update_matrix_summary()

    def update_matrix_summary(self, *args):
        totals = {level: 0 for level in ('NB', 'TH', 'VD', 'VDC')}
        type_totals = {'mcq': 0, 'true_false': 0, 'short_answer': 0, 'essay': 0}
        total = 0
        for i in range(self.matrix.rowCount()):
            count_item = self.matrix.item(i, 4)
            level_item = self.matrix.item(i, 3)
            type_item = self.matrix.item(i, 2)
            try:
                count = int(count_item.text()) if count_item else 0
            except ValueError:
                count = 0
            total += count

            lvl = LEVEL_CODE_MAP.get(level_item.text(), level_item.text()) if level_item else ''
            if lvl in totals:
                totals[lvl] += count

            tcode = QTYPE_CODE_MAP.get(type_item.text(), type_item.text()) if type_item else ''
            if tcode in type_totals:
                type_totals[tcode] += count

        type_str = f"TN: {type_totals['mcq']} · Đ/S: {type_totals['true_false']} · TLN: {type_totals['short_answer']} · TL: {type_totals['essay']}"
        lvl_str = f"NB: {totals['NB']} · TH: {totals['TH']} · VD: {totals['VD']} · VDC: {totals['VDC']}"
        self.matrix_summary.setText(f'Ma trận: {total} câu ({type_str} | {lvl_str})')
        self.update_step_summaries()

    def remove_row(self):
        if self.matrix.currentRow() >= 0:
            self.matrix.removeRow(self.matrix.currentRow())
            self.update_matrix_summary()

    def start_export_process(self):
        if not self.snapshot:
            QMessageBox.warning(self, "Chưa tạo đề", "Vui lòng hoàn thành Bước 2 hoặc Bước 3 để tạo đề thi trước khi xuất.")
            return

        export_student = self.chk_exp_student.isChecked()
        export_teacher = self.chk_exp_teacher.isChecked()
        export_answers = self.chk_exp_answers.isChecked()

        if not (export_student or export_teacher or export_answers):
            QMessageBox.warning(self, "Chưa chọn tài liệu", "Vui lòng chọn ít nhất một loại tài liệu cần xuất (Đề học sinh, Đề giáo viên hoặc Bảng đáp án).")
            return

        style = 'mapclass' if self.rad_style_mapclass.isChecked() else 'article'
        exam_code = str(self.snapshot.get('exam_code', '101')).strip()
        title_slug = re.sub(r'[^\w\-]+', '_', self.snapshot.get('title', 'de_kiem_tra')).strip('_')

        # Xác định định dạng & đường dẫn xuất
        if self.rad_fmt_pdf.isChecked():
            fmt = 'pdf'
            default_name = f"{title_slug}_{exam_code}.pdf"
            path, _ = QFileDialog.getSaveFileName(self, "Lưu file PDF đề thi", default_name, "File PDF (*.pdf)")
            if not path:
                return
            target_path = Path(path)
        elif self.rad_fmt_bundle.isChecked():
            fmt = 'bundle'
            folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu bộ đề thi trọn gói", "")
            if not folder:
                return
            target_path = Path(folder) / f"{title_slug}_{exam_code}"
        elif self.rad_fmt_zip.isChecked():
            fmt = 'zip'
            default_name = f"{title_slug}_{exam_code}.zip"
            path, _ = QFileDialog.getSaveFileName(self, "Lưu gói đề thi portable ZIP", default_name, "File ZIP (*.zip)")
            if not path:
                return
            target_path = Path(path)
        else:
            fmt = 'tex'
            default_name = f"{title_slug}_{exam_code}.tex"
            path, _ = QFileDialog.getSaveFileName(self, "Lưu file TeX đề thi", default_name, "LaTeX (*.tex)")
            if not path:
                return
            target_path = Path(path)

        # Cập nhật UI trạng thái
        self._export_cancelled = False
        self.big_export_btn.setEnabled(False)
        self.btn_cancel_export.setVisible(True)
        self.btn_cancel_export.setEnabled(True)
        self.export_progress_bar.setVisible(True)
        self.export_progress_bar.setRange(0, 0)
        self.export_status_lbl.setText("⏳ Đang đóng gói tài nguyên và biên dịch pdfLaTeX...")
        self.export_status_lbl.setStyleSheet("color: #0284c7; font-weight: bold;")
        self.export_path_lbl.setVisible(False)
        self.btn_open_pdf.setVisible(False)
        self.btn_open_folder.setVisible(False)
        self.btn_open_tex.setVisible(False)
        self.btn_view_log.setVisible(False)

        # Đọc cấu hình compiler
        compiler_cfg = {}
        if self.services:
            cpath = self.services.config.data_dir / "compiler.json"
            if cpath.exists():
                try:
                    compiler_cfg = json.loads(cpath.read_text(encoding='utf-8'))
                except Exception:
                    pass
        engine = compiler_cfg.get('engine', 'pdflatex')
        preamble_file = compiler_cfg.get('preamble_file') or None

        from latex_question_studio.ui.jobs import Job
        from latex_question_studio.application.exams import ExamService
        snapshot_data = self.snapshot

        def do_export(cancelled, progress):
            check_cancelled = lambda: cancelled() or getattr(self, '_export_cancelled', False)
            exam_svc = ExamService(self.services)
            if fmt == 'pdf':
                selected_count = int(export_student) + int(export_teacher) + int(export_answers)
                created_pdfs = []
                errors = []
                if selected_count == 1:
                    res = exam_svc.export_pdf(
                        snapshot_data,
                        target_path,
                        solutions=export_teacher,
                        answer_only=export_answers,
                        engine=engine,
                        preamble_file=preamble_file,
                        cancelled=check_cancelled
                    )
                    tex_side = target_path.with_suffix('.tex')
                    exam_svc.export_tex(
                        snapshot_data,
                        tex_side,
                        solutions=export_teacher,
                        answer_only=export_answers,
                        preamble=None if style == 'article' else MAPCLASS_PREAMBLE,
                        bundle_dependencies=True
                    )
                    if res.ok:
                        created_pdfs.append(target_path)
                    else:
                        errors.append(('File PDF', res.log))
                else:
                    base_dir = target_path.parent
                    base_stem = target_path.stem
                    if export_student:
                        s_pdf = base_dir / f"{base_stem}_hoc_sinh.pdf"
                        s_res = exam_svc.export_pdf(snapshot_data, s_pdf, solutions=False, answer_only=False, engine=engine, preamble_file=preamble_file, cancelled=check_cancelled)
                        exam_svc.export_tex(snapshot_data, s_pdf.with_suffix('.tex'), solutions=False, answer_only=False, preamble=None if style == 'article' else MAPCLASS_PREAMBLE, bundle_dependencies=True)
                        if s_res.ok:
                            created_pdfs.append(s_pdf)
                        else:
                            errors.append(('Đề học sinh', s_res.log))
                    if export_teacher:
                        t_pdf = base_dir / f"{base_stem}_giao_vien.pdf"
                        t_res = exam_svc.export_pdf(snapshot_data, t_pdf, solutions=True, answer_only=False, engine=engine, preamble_file=preamble_file, cancelled=check_cancelled)
                        exam_svc.export_tex(snapshot_data, t_pdf.with_suffix('.tex'), solutions=True, answer_only=False, preamble=None if style == 'article' else MAPCLASS_PREAMBLE, bundle_dependencies=True)
                        if t_res.ok:
                            created_pdfs.append(t_pdf)
                        else:
                            errors.append(('Đề giáo viên', t_res.log))
                    if export_answers:
                        a_pdf = base_dir / f"{base_stem}_dap_an.pdf"
                        a_res = exam_svc.export_pdf(snapshot_data, a_pdf, solutions=False, answer_only=True, engine=engine, preamble_file=preamble_file, cancelled=check_cancelled)
                        exam_svc.export_tex(snapshot_data, a_pdf.with_suffix('.tex'), solutions=False, answer_only=True, preamble=None if style == 'article' else MAPCLASS_PREAMBLE, bundle_dependencies=True)
                        if a_res.ok:
                            created_pdfs.append(a_pdf)
                        else:
                            errors.append(('Bảng đáp án', a_res.log))

                return {
                    'fmt': 'pdf',
                    'target': str(created_pdfs[0] if created_pdfs else target_path),
                    'ok': len(errors) == 0,
                    'errors': errors,
                    'log': errors[0][1] if errors else ''
                }
            elif fmt == 'bundle':
                res = exam_svc.export_bundle(
                    snapshot_data,
                    target_path,
                    export_student=export_student,
                    export_teacher=export_teacher,
                    export_answers=export_answers,
                    style=style,
                    compile_pdf=True,
                    engine=engine,
                    preamble_file=preamble_file,
                    cancelled=check_cancelled,
                    progress=progress
                )
                return {'fmt': 'bundle', 'target': str(target_path), 'res': res, 'ok': res['ok'], 'errors': res.get('errors', [])}
            elif fmt == 'zip':
                res = exam_svc.export_zip(
                    snapshot_data,
                    target_path,
                    export_student=export_student,
                    export_teacher=export_teacher,
                    export_answers=export_answers,
                    style=style,
                    compile_pdf=True,
                    engine=engine,
                    preamble_file=preamble_file,
                    cancelled=check_cancelled
                )
                return {'fmt': 'zip', 'target': str(target_path), 'ok': True}
            else:
                selected_count = int(export_student) + int(export_teacher) + int(export_answers)
                created_texs = []
                if selected_count == 1:
                    exam_svc.export_tex(
                        snapshot_data,
                        target_path,
                        solutions=export_teacher,
                        answer_only=export_answers,
                        preamble=None if style == 'article' else MAPCLASS_PREAMBLE,
                        bundle_dependencies=True
                    )
                    created_texs.append(target_path)
                else:
                    base_dir = target_path.parent
                    base_stem = target_path.stem
                    if export_student:
                        s_tex = base_dir / f"{base_stem}_hoc_sinh.tex"
                        exam_svc.export_tex(snapshot_data, s_tex, solutions=False, answer_only=False, preamble=None if style == 'article' else MAPCLASS_PREAMBLE, bundle_dependencies=True)
                        created_texs.append(s_tex)
                    if export_teacher:
                        t_tex = base_dir / f"{base_stem}_giao_vien.tex"
                        exam_svc.export_tex(snapshot_data, t_tex, solutions=True, answer_only=False, preamble=None if style == 'article' else MAPCLASS_PREAMBLE, bundle_dependencies=True)
                        created_texs.append(t_tex)
                    if export_answers:
                        a_tex = base_dir / f"{base_stem}_dap_an.tex"
                        exam_svc.export_tex(snapshot_data, a_tex, solutions=False, answer_only=True, preamble=None if style == 'article' else MAPCLASS_PREAMBLE, bundle_dependencies=True)
                        created_texs.append(a_tex)
                return {'fmt': 'tex', 'target': str(created_texs[0] if created_texs else target_path), 'ok': True}

        job = Job(do_export)
        self._current_export_job = job
        job.signals.completed.connect(self._on_export_completed)
        job.signals.failed.connect(self._on_export_failed)
        if self.run_job:
            self.run_job(job)
        else:
            from PySide6.QtCore import QThreadPool
            QThreadPool.globalInstance().start(job)

    def _cancel_export_process(self):
        self._export_cancelled = True
        if hasattr(self, '_current_export_job') and self._current_export_job:
            self._current_export_job.cancel()
        self.btn_cancel_export.setEnabled(False)
        self.export_status_lbl.setText("⏳ Đang hủy tác vụ xuất đề...")
        self.export_status_lbl.setStyleSheet("color: #f59e0b; font-weight: bold;")

    def _on_export_completed(self, payload):
        self.big_export_btn.setEnabled(True)
        self.btn_cancel_export.setVisible(False)
        self.export_progress_bar.setVisible(False)
        target = payload.get('target', '')
        fmt = payload.get('fmt', '')
        ok = payload.get('ok', True)
        self._last_exported_target = target
        self._last_exported_fmt = fmt
        self._last_exported_log = payload.get('log', '')

        if ok:
            self.export_status_lbl.setText("🎉 XUẤT BẢN VÀ BIÊN DỊCH THÀNH CÔNG!")
            self.export_status_lbl.setStyleSheet("color: #16a34a; font-weight: bold; font-size: 13px;")
            self.export_path_lbl.setText(f"📁 Đường dẫn: {target}")
            self.export_path_lbl.setStyleSheet("color: #0f172a; font-size: 12px;")
            self.export_path_lbl.setVisible(True)

            self.btn_open_folder.setVisible(True)
            if fmt == 'pdf':
                self.btn_open_pdf.setVisible(True)
            elif fmt == 'tex':
                self.btn_open_tex.setVisible(True)
            elif fmt == 'bundle':
                pdir = Path(target)
                if list(pdir.glob('*.pdf')):
                    self.btn_open_pdf.setVisible(True)
                if list(pdir.glob('*.tex')):
                    self.btn_open_tex.setVisible(True)
            elif fmt == 'zip':
                self.btn_open_folder.setVisible(True)
        else:
            errors = payload.get('errors', [])
            err_msg = "\n".join(f"{item}: {log[:300]}" for item, log in errors) if errors else payload.get('log', '')
            self._last_exported_log = err_msg or payload.get('log', '')
            self.export_status_lbl.setText("⚠️ ĐÃ XUẤT FILE TEX NHƯNG BIÊN DỊCH PDF GẶP LỖI")
            self.export_status_lbl.setStyleSheet("color: #d97706; font-weight: bold; font-size: 13px;")
            self.export_path_lbl.setText(f"Tài nguyên đã được lưu tại: {target}\nBạn có thể kiểm tra nhật ký lỗi để sửa câu hỏi.")
            self.export_path_lbl.setStyleSheet("color: #475569; font-size: 12px;")
            self.export_path_lbl.setVisible(True)
            self.btn_open_folder.setVisible(True)
            self.btn_view_log.setVisible(True)

    def _on_export_failed(self, message):
        self.big_export_btn.setEnabled(True)
        self.btn_cancel_export.setVisible(False)
        self.export_progress_bar.setVisible(False)
        self.export_status_lbl.setText(f"❌ Quá trình xuất đề thất bại: {message}")
        self.export_status_lbl.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px;")

    def _open_exported_pdf(self):
        if not hasattr(self, '_last_exported_target'):
            return
        target = Path(self._last_exported_target)
        to_open = None
        if target.is_file() and target.suffix.lower() == '.pdf':
            to_open = target
        elif target.is_dir():
            student = target / 'de-thi-hoc-sinh.pdf'
            teacher = target / 'de-thi-giao-vien.pdf'
            pdfs = list(target.glob('*.pdf'))
            if student.is_file():
                to_open = student
            elif teacher.is_file():
                to_open = teacher
            elif pdfs:
                to_open = pdfs[0]
        if to_open and to_open.is_file():
            try:
                os.startfile(str(to_open))
            except Exception:
                pass

    def _open_exported_folder(self):
        if not hasattr(self, '_last_exported_target'):
            return
        target = Path(self._last_exported_target)
        folder = target if target.is_dir() else target.parent
        if folder.exists():
            try:
                os.startfile(str(folder))
            except Exception:
                pass

    def _open_exported_tex(self):
        if not hasattr(self, '_last_exported_target'):
            return
        target = Path(self._last_exported_target)
        to_open = None
        if target.is_file() and target.suffix.lower() == '.tex':
            to_open = target
        elif target.is_dir():
            student = target / 'de-thi-hoc-sinh.tex'
            teacher = target / 'de-thi-giao-vien.tex'
            texs = list(target.glob('*.tex'))
            if student.is_file():
                to_open = student
            elif teacher.is_file():
                to_open = teacher
            elif texs:
                to_open = texs[0]
        if to_open and to_open.is_file():
            try:
                os.startfile(str(to_open))
            except Exception:
                pass

    def _view_export_log(self):
        from PySide6.QtWidgets import QDialog, QPlainTextEdit, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Nhật ký biên dịch LaTeX")
        dlg.resize(720, 480)
        vbox = QVBoxLayout(dlg)
        txt = QPlainTextEdit(dlg)
        txt.setReadOnly(True)
        txt.setPlainText(getattr(self, '_last_exported_log', 'Không có nhật ký chi tiết.'))
        vbox.addWidget(txt)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.close)
        vbox.addWidget(btns)
        dlg.exec()
