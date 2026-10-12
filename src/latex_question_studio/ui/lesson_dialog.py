"""New lesson creation wizard and lesson metadata editor."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QComboBox, QSpinBox, QCheckBox, QTreeWidget,
                             QTreeWidgetItem, QSplitter, QGroupBox, QFrame, QToolButton,
                             QMessageBox, QDialogButtonBox)
from latex_question_studio.application.lessons import (LESSON_TEMPLATES, build_template_blocks,
                                                      KINDS)
from latex_question_studio.ui.icons import icon
from latex_question_studio.domain.curriculum import classification, breadcrumb
from latex_question_studio.application.library import LibraryService


class NewLessonDialog(QDialog):
    def __init__(self, services, parent=None):
        super().__init__(parent)
        self.services = services
        self.setWindowTitle("Tạo bài giảng mới - Chuẩn sư phạm GDPT 2018")
        self.resize(860, 620)
        self.taxonomy_nodes = []
        self._load_taxonomy()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header banner
        header = QFrame()
        header.setObjectName("lessonWizardHeader")
        header.setStyleSheet("QFrame#lessonWizardHeader { background: #1e293b; border-radius: 8px; padding: 10px; border: 1px solid #334155; }")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 8, 12, 8)
        header_icon = QLabel()
        header_icon.setPixmap(icon('lesson', '#38bdf8').pixmap(32, 32))
        hl.addWidget(header_icon)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        h_title = QLabel("TẠO BÀI GIẢNG MỚI THEO CHUẨN SƯ PHẠM")
        h_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        title_box.addWidget(h_title)
        h_sub = QLabel("Thiết lập môn, lớp, liên kết chương trình GDPT và khởi tạo cấu trúc bài giảng tối ưu")
        h_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_box.addWidget(h_sub)
        hl.addLayout(title_box, 1)
        main_layout.addWidget(header)

        # Body splitter: Left settings (500px), Right outline preview (340px)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        main_layout.addWidget(splitter, 1)

        # Left panel
        left_widget = QFrame()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # 1. Lesson metadata group
        meta_group = QGroupBox("1. Thông tin bài giảng")
        ml = QVBoxLayout(meta_group)
        ml.setSpacing(8)

        # Title input + chips
        ml.addWidget(QLabel("Tên bài giảng:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("VD: Bài 1: Sự đồng biến, nghịch biến của hàm số")
        self.title_input.setText("Bài 1: Khảo sát và vẽ đồ thị hàm số")
        self.title_input.textEdited.connect(self.update_preview)
        ml.addWidget(self.title_input)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        chips_row.addWidget(QLabel("Gợi ý:"))
        for prefix in ("Bài 1:", "Bài 2:", "Chuyên đề:", "Ôn tập:", "Luyện tập:"):
            btn = QToolButton()
            btn.setText(prefix)
            btn.setStyleSheet("QToolButton { background: #334155; color: #e2e8f0; border-radius: 4px; padding: 2px 8px; font-size: 11px; } QToolButton:hover { background: #475569; }")
            btn.clicked.connect(lambda checked=False, p=prefix: self._apply_chip(p))
            chips_row.addWidget(btn)
        chips_row.addStretch()
        ml.addLayout(chips_row)

        # Subject & Grade row
        subj_grade_row = QHBoxLayout()
        subj_grade_row.setSpacing(10)

        subj_box = QVBoxLayout()
        subj_box.setSpacing(4)
        subj_box.addWidget(QLabel("Môn học:"))
        self.subject_combo = QComboBox()
        self.subject_combo.addItems(["Toán", "Vật lý", "Hóa học", "Sinh học", "Khoa học tự nhiên", "Tin học", "Tiếng Anh"])
        self.subject_combo.currentTextChanged.connect(self.update_preview)
        subj_box.addWidget(self.subject_combo)
        subj_grade_row.addLayout(subj_box, 1)

        grade_box = QVBoxLayout()
        grade_box.setSpacing(4)
        grade_box.addWidget(QLabel("Khối lớp:"))
        self.grade_combo = QComboBox()
        for g in ("12", "11", "10", "9", "8", "7", "6"):
            self.grade_combo.addItem(f"Lớp {g}", g)
        self.grade_combo.currentIndexChanged.connect(self.update_preview)
        grade_box.addWidget(self.grade_combo)
        subj_grade_row.addLayout(grade_box, 1)

        ml.addLayout(subj_grade_row)
        ml.addSpacing(6)

        # Curriculum linkage
        self.curriculum_check = QCheckBox("Liên kết Bài học từ Chương trình GDPT 2018")
        self.curriculum_check.toggled.connect(self._toggle_curriculum)
        ml.addWidget(self.curriculum_check)

        self.curriculum_box = QFrame()
        cbl = QVBoxLayout(self.curriculum_box)
        cbl.setContentsMargins(8, 4, 8, 4)
        cbl.setSpacing(4)
        self.curriculum_combo = QComboBox()
        self.curriculum_combo.setMinimumContentsLength(30)
        self.curriculum_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.curriculum_combo.currentIndexChanged.connect(self._on_curriculum_selected)
        cbl.addWidget(self.curriculum_combo)
        self.curriculum_path_label = QLabel()
        self.curriculum_path_label.setStyleSheet("color: #38bdf8; font-size: 11px;")
        self.curriculum_path_label.setWordWrap(True)
        cbl.addWidget(self.curriculum_path_label)
        self.curriculum_box.hide()
        ml.addWidget(self.curriculum_box)

        self._populate_curriculum_combo()
        left_layout.addWidget(meta_group)

        # 2. Template selection group
        tmpl_group = QGroupBox("2. Mẫu cấu trúc bài giảng")
        tl = QVBoxLayout(tmpl_group)
        tl.setSpacing(6)

        self.template_combo = QComboBox()
        for key, info in LESSON_TEMPLATES.items():
            icon_name = 'lesson' if key == 'standard' else ('chapter' if key == 'methods' else ('topic' if key == 'theory' else 'exam'))
            self.template_combo.addItem(icon(icon_name, '#38bdf8'), info['name'], key)
        self.template_combo.setCurrentIndex(0)
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        tl.addWidget(self.template_combo)

        self.template_desc = QLabel()
        self.template_desc.setStyleSheet("background: #0f172a; border-radius: 6px; padding: 8px; color: #cbd5e1; font-size: 11.5px; border: 1px solid #1e293b;")
        self.template_desc.setWordWrap(True)
        tl.addWidget(self.template_desc)
        left_layout.addWidget(tmpl_group)

        # 3. Customization group
        custom_group = QGroupBox("3. Tuỳ chỉnh chi tiết thành phần")
        cl = QVBoxLayout(custom_group)
        cl.setSpacing(6)

        num_methods_row = QHBoxLayout()
        num_methods_row.addWidget(QLabel("Số lượng Dạng toán ban đầu:"))
        self.num_methods_spin = QSpinBox()
        self.num_methods_spin.setRange(1, 5)
        self.num_methods_spin.setValue(2)
        self.num_methods_spin.valueChanged.connect(self.update_preview)
        num_methods_row.addWidget(self.num_methods_spin)
        num_methods_row.addStretch()
        cl.addLayout(num_methods_row)

        self.warmup_check = QCheckBox("Kèm phần Khởi động / Đặt vấn đề")
        self.warmup_check.setChecked(True)
        self.warmup_check.toggled.connect(self.update_preview)
        cl.addWidget(self.warmup_check)

        self.homework_check = QCheckBox("Kèm Bài tập về nhà / Hướng dẫn tự học")
        self.homework_check.setChecked(True)
        self.homework_check.toggled.connect(self.update_preview)
        cl.addWidget(self.homework_check)

        self.auto_filter_bank = QCheckBox("Tự động lọc câu hỏi theo môn/khối/bài trong Thư viện câu hỏi sau khi tạo")
        self.auto_filter_bank.setChecked(True)
        cl.addWidget(self.auto_filter_bank)

        left_layout.addWidget(custom_group)
        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # Right panel: Structure preview
        right_widget = QFrame()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        preview_header_row = QHBoxLayout()
        preview_title = QLabel("CẤU TRÚC DỰ KIẾN (OUTLINE)")
        preview_title.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 11px;")
        preview_header_row.addWidget(preview_title)
        self.count_badge = QLabel("0 mục")
        self.count_badge.setStyleSheet("background: #0284c7; color: #ffffff; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold;")
        preview_header_row.addWidget(self.count_badge)
        preview_header_row.addStretch()
        right_layout.addLayout(preview_header_row)

        self.tree_preview = QTreeWidget()
        self.tree_preview.setHeaderHidden(True)
        self.tree_preview.setStyleSheet("QTreeWidget { background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 4px; } QTreeWidget::item { padding: 4px 0; }")
        right_layout.addWidget(self.tree_preview, 1)

        tip_label = QLabel("💡 Mẹo: Sau khi tạo, bạn có thể bổ sung thêm Dạng toán, ví dụ mẫu hoặc câu hỏi từ thư viện bất kỳ lúc nào.")
        tip_label.setStyleSheet("color: #64748b; font-size: 11px;")
        tip_label.setWordWrap(True)
        right_layout.addWidget(tip_label)

        splitter.addWidget(right_widget)
        splitter.setSizes([500, 340])

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.cancel_btn = QPushButton("Hủy bỏ")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("🚀 BẮT ĐẦU TẠO BÀI GIẢNG")
        self.create_btn.setProperty("primary", True)
        self.create_btn.setStyleSheet("QPushButton { font-weight: bold; font-size: 13px; padding: 8px 20px; }")
        self.create_btn.clicked.connect(self.on_accept)
        btn_row.addWidget(self.create_btn)
        main_layout.addLayout(btn_row)

        self._on_template_changed()

    def _load_taxonomy(self):
        try:
            self.taxonomy_nodes = LibraryService(self.services).taxonomy()
        except Exception:
            self.taxonomy_nodes = []

    def _populate_curriculum_combo(self):
        self.curriculum_combo.blockSignals(True)
        self.curriculum_combo.clear()
        self.curriculum_combo.addItem("--- Chọn bài từ chương trình ---", None)
        for node in self.taxonomy_nodes:
            if node.get('kind') == 'lesson':
                title = node.get('name', 'Bài học')
                bc = breadcrumb(self.taxonomy_nodes, node['id'])
                self.curriculum_combo.addItem(f"{title} ({bc})", node['id'])
        self.curriculum_combo.blockSignals(False)

    def _toggle_curriculum(self, checked):
        self.curriculum_box.setVisible(checked)
        if checked and self.curriculum_combo.currentIndex() > 0:
            self._on_curriculum_selected(self.curriculum_combo.currentIndex())

    def _on_curriculum_selected(self, index):
        node_id = self.curriculum_combo.itemData(index)
        if not node_id:
            self.curriculum_path_label.setText("")
            return
        node = next((n for n in self.taxonomy_nodes if n['id'] == node_id), None)
        if node:
            bc = breadcrumb(self.taxonomy_nodes, node_id)
            self.curriculum_path_label.setText("📍 " + bc)
            self.title_input.setText(node.get('name', ''))
            # Auto match subject and grade if available
            info = classification(self.taxonomy_nodes, node_id)
            subj = info.get('subject')
            grade = info.get('grade')
            if subj:
                idx = self.subject_combo.findText(subj)
                if idx >= 0:
                    self.subject_combo.setCurrentIndex(idx)
            if grade:
                idx = self.grade_combo.findData(grade)
                if idx >= 0:
                    self.grade_combo.setCurrentIndex(idx)
            self.update_preview()

    def _apply_chip(self, prefix):
        current = self.title_input.text().strip()
        for p in ("Bài 1:", "Bài 2:", "Chuyên đề:", "Ôn tập:", "Luyện tập:"):
            if current.startswith(p):
                current = current[len(p):].strip()
        self.title_input.setText(f"{prefix} {current}".strip())
        self.update_preview()

    def _on_template_changed(self):
        key = self.template_combo.currentData()
        info = LESSON_TEMPLATES.get(key, {})
        self.template_desc.setText(info.get('description', ''))
        # Adjust customize controls visibility based on template
        is_blank = (key == 'blank')
        is_worksheet = (key == 'worksheet')
        self.num_methods_spin.setEnabled(key in ('standard', 'methods', 'legacy'))
        self.warmup_check.setEnabled(key in ('standard', 'theory'))
        self.homework_check.setEnabled(key in ('standard', 'methods'))
        self.update_preview()

    def update_preview(self):
        key = self.template_combo.currentData() or 'standard'
        num_methods = self.num_methods_spin.value()
        include_warmup = self.warmup_check.isChecked() and self.warmup_check.isEnabled()
        include_homework = self.homework_check.isChecked() and self.homework_check.isEnabled()

        self.preview_blocks = build_template_blocks(
            template_key=key,
            num_methods=num_methods,
            include_warmup=include_warmup,
            include_homework=include_homework
        )

        self.count_badge.setText(f"{len(self.preview_blocks)} mục")
        self.tree_preview.clear()

        # Build tree representation
        items = {}
        for b in self.preview_blocks:
            k_label = KINDS.get(b['kind'], b['kind'])
            item = QTreeWidgetItem([b['title']])
            icon_name = 'chapter' if b['kind'] in ('section', 'type') else ('exam' if b['kind'] == 'method' else ('preview' if b['kind'] == 'example' else 'lesson'))
            item.setIcon(0, icon(icon_name, '#38bdf8'))
            item.setToolTip(0, f"Loại: {k_label}")
            items[b['id']] = item

        for b in self.preview_blocks:
            parent = items.get(b['parent'])
            if parent:
                parent.addChild(items[b['id']])
            else:
                self.tree_preview.addTopLevelItem(items[b['id']])

        self.tree_preview.expandAll()

    def on_accept(self):
        title = self.title_input.text().strip()
        if not title:
            subj = self.subject_combo.currentText()
            grade = self.grade_combo.currentData()
            self.title_input.setText(f"Bài giảng {subj} {grade}")
        self.accept()

    def create_lesson(self, lesson_service):
        title = self.title_input.text().strip()
        subject = self.subject_combo.currentText()
        grade = self.grade_combo.currentData()
        template_key = self.template_combo.currentData() or 'standard'
        taxonomy_id = self.curriculum_combo.currentData() if self.curriculum_check.isChecked() else None

        return lesson_service.create(
            title=title,
            subject=subject,
            grade=grade,
            taxonomy_id=taxonomy_id,
            template_key=template_key,
            blocks=self.preview_blocks
        )


class EditLessonInfoDialog(QDialog):
    """Dialog to view and edit lesson metadata (Title, Subject, Grade, Curriculum)."""
    def __init__(self, services, doc, parent=None):
        super().__init__(parent)
        self.services = services
        self.doc = doc
        self.setWindowTitle("Chỉnh sửa thông tin bài giảng")
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QVBoxLayout()
        form.setSpacing(8)

        form.addWidget(QLabel("Tên bài giảng:"))
        self.title_input = QLineEdit(doc.get('title', ''))
        form.addWidget(self.title_input)

        row = QHBoxLayout()
        sub_box = QVBoxLayout()
        sub_box.addWidget(QLabel("Môn học:"))
        self.subject_combo = QComboBox()
        self.subject_combo.addItems(["Toán", "Vật lý", "Hóa học", "Sinh học", "Khoa học tự nhiên", "Tin học", "Tiếng Anh"])
        if doc.get('subject'):
            idx = self.subject_combo.findText(doc['subject'])
            if idx >= 0:
                self.subject_combo.setCurrentIndex(idx)
        sub_box.addWidget(self.subject_combo)
        row.addLayout(sub_box, 1)

        grade_box = QVBoxLayout()
        grade_box.addWidget(QLabel("Khối lớp:"))
        self.grade_combo = QComboBox()
        for g in ("12", "11", "10", "9", "8", "7", "6"):
            self.grade_combo.addItem(f"Lớp {g}", g)
        if doc.get('grade'):
            idx = self.grade_combo.findData(str(doc['grade']))
            if idx >= 0:
                self.grade_combo.setCurrentIndex(idx)
        grade_box.addWidget(self.grade_combo)
        row.addLayout(grade_box, 1)
        form.addLayout(row)

        form.addWidget(QLabel("Liên kết chương trình GDPT:"))
        self.curriculum_combo = QComboBox()
        self.curriculum_combo.addItem("Không liên kết", None)
        try:
            nodes = LibraryService(services).taxonomy()
            for node in nodes:
                if node.get('kind') == 'lesson':
                    bc = breadcrumb(nodes, node['id'])
                    self.curriculum_combo.addItem(f"{node['name']} ({bc})", node['id'])
        except Exception:
            pass
        if doc.get('taxonomy_id'):
            idx = self.curriculum_combo.findData(doc['taxonomy_id'])
            if idx >= 0:
                self.curriculum_combo.setCurrentIndex(idx)
        form.addWidget(self.curriculum_combo)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def apply_to_doc(self, doc):
        doc['title'] = self.title_input.text().strip() or doc.get('title', 'Bài giảng')
        doc['subject'] = self.subject_combo.currentText()
        doc['grade'] = self.grade_combo.currentData()
        doc['taxonomy_id'] = self.curriculum_combo.currentData()
        return doc
