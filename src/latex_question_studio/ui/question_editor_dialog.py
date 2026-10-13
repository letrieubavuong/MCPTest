"""Independent question editor dialog with live LaTeX preview and metadata classification."""
import json
from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QSplitter, QScrollArea, QFrame, QMessageBox
)
from latex_question_studio.ui.editor import LatexEditor
from latex_question_studio.application.library import LibraryService
from latex_question_studio.domain.curriculum import classification, breadcrumb
from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.ui.jobs import Job
from latex_question_studio.parsing.latex import parse_questions

TYPE_LABELS = {
    'mcq': 'Trắc nghiệm (4 phương án)',
    'true_false': 'Đúng / Sai',
    'short_answer': 'Trả lời ngắn / Điền số',
    'essay': 'Tự luận'
}

class QuestionEditorDialog(QDialog):
    question_saved = Signal(str)

    def __init__(self, question_id: str, services, parent=None):
        super().__init__(parent)
        self.setObjectName("questionEditorDialog")
        self.services = services
        self.question_id = question_id
        self.question = services.questions.get(question_id)
        if not self.question:
            raise ValueError(f"Question with id {question_id} not found.")

        self.setWindowTitle(f"Chỉnh sửa câu hỏi #{self.question.id[:8]}")
        self.resize(1100, 720)
        self.setMinimumSize(850, 550)

        self.preview_job = None
        self.original_pixmap = None
        self.nodes = LibraryService(services).taxonomy()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header bar
        header = QHBoxLayout()
        header.setSpacing(10)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.title_label = QLabel(f"Chỉnh sửa câu hỏi: #{self.question.id[:8]}")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.subtitle_label = QLabel("Chỉnh sửa nội dung LaTeX, công thức toán và phân loại câu hỏi")
        self.subtitle_label.setStyleSheet("color: #64748b; font-size: 11.5px;")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        header.addLayout(title_box, 1)

        self.compile_now_btn = QPushButton("Biên dịch xem trước (F5)")
        self.compile_now_btn.clicked.connect(self.compile_preview)
        header.addWidget(self.compile_now_btn)
        layout.addLayout(header)

        # Splitter: Left editor (60%) vs Right preview (40%)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # Left panel: Editor
        editor_frame = QFrame()
        editor_frame.setObjectName("dialogEditorSection")
        editor_box = QVBoxLayout(editor_frame)
        editor_box.setContentsMargins(8, 8, 8, 8)
        editor_box.setSpacing(6)

        ed_head = QHBoxLayout()
        ed_head.addWidget(QLabel("<b>Nội dung LaTeX</b>"))
        ed_head.addStretch(1)
        editor_box.addLayout(ed_head)

        self.editor = LatexEditor()
        self.editor.set_theme(services.config.theme)
        self.editor.setPlainText(self.question.latex_source)
        editor_box.addWidget(self.editor, 1)
        self.splitter.addWidget(editor_frame)

        # Right panel: Preview
        preview_frame = QFrame()
        preview_frame.setObjectName("dialogPreviewSection")
        preview_box = QVBoxLayout(preview_frame)
        preview_box.setContentsMargins(8, 8, 8, 8)
        preview_box.setSpacing(6)

        pv_head = QHBoxLayout()
        pv_head.addWidget(QLabel("<b>Xem trước trực quan (PDF)</b>"))
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        pv_head.addWidget(self.status_lbl, 1, Qt.AlignmentFlag.AlignRight)
        preview_box.addLayout(pv_head)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_label = QLabel("Đang chuẩn bị xem trước...")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.preview_label.setWordWrap(True)
        self.preview_scroll.setWidget(self.preview_label)
        preview_box.addWidget(self.preview_scroll, 1)
        self.splitter.addWidget(preview_frame)

        self.splitter.setSizes([620, 440])
        layout.addWidget(self.splitter, 1)

        # Metadata bar
        meta_box = QHBoxLayout()
        meta_box.setSpacing(10)

        meta_box.addWidget(QLabel("Bài / dạng:"))
        self.taxonomy_combo = QComboBox()
        self.taxonomy_combo.setMinimumWidth(220)
        self.taxonomy_combo.addItem("Chưa phân loại", None)
        for n in self.nodes:
            if n['kind'] in ('lesson', 'topic'):
                self.taxonomy_combo.addItem(breadcrumb(self.nodes, n['id']), n['id'])
        meta_box.addWidget(self.taxonomy_combo, 1)

        meta_box.addWidget(QLabel("Mức độ:"))
        self.level_combo = QComboBox()
        for label, key in [('Chưa gán', ''), ('Nhận biết (NB)', 'NB'), ('Thông hiểu (TH)', 'TH'), ('Vận dụng (VD)', 'VD'), ('Vận dụng cao (VDC)', 'VDC')]:
            self.level_combo.addItem(label, key)
        meta_box.addWidget(self.level_combo)

        meta_box.addWidget(QLabel("Dạng thức:"))
        self.type_combo = QComboBox()
        for key, label in TYPE_LABELS.items():
            self.type_combo.addItem(label, key)
        meta_box.addWidget(self.type_combo)

        layout.addLayout(meta_box)

        # Footer actions
        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.source_origin = QLineEdit()
        self.source_origin.setPlaceholderText("Nguồn trích dẫn / Đề thi gốc...")
        footer.addWidget(QLabel("Nguồn:"))
        footer.addWidget(self.source_origin, 1)

        footer.addStretch(1)
        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.clicked.connect(self.reject)
        footer.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Lưu câu hỏi (Ctrl+S)")
        self.save_btn.setProperty("primary", True)
        self.save_btn.clicked.connect(self.save)
        footer.addWidget(self.save_btn)
        layout.addLayout(footer)

        # Timers and shortcuts
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(400)
        self.preview_timer.timeout.connect(self.compile_preview)
        self.editor.textChanged.connect(self.on_text_changed)

        QShortcut(QKeySequence("F5"), self, self.compile_preview)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save)

        self.load_metadata()
        QTimer.singleShot(100, self.compile_preview)

    def load_metadata(self):
        m = LibraryService(self.services).metadata(self.question.id)
        tax_id = m.get('taxonomy_id')
        if tax_id:
            idx = self.taxonomy_combo.findData(tax_id)
            if idx >= 0:
                self.taxonomy_combo.setCurrentIndex(idx)
        level = self.question.cognitive_level or ''
        idx_lvl = self.level_combo.findData(level)
        if idx_lvl >= 0:
            self.level_combo.setCurrentIndex(idx_lvl)
        q_type = self.question.question_type or 'mcq'
        idx_type = self.type_combo.findData(q_type)
        if idx_type >= 0:
            self.type_combo.setCurrentIndex(idx_type)
        self.source_origin.setText(m.get('source', ''))

    def on_text_changed(self):
        self.status_lbl.setText("Có thay đổi...")
        self.preview_timer.start()

    def compile_preview(self):
        source = self.editor.toPlainText().strip()
        if not source:
            self.preview_label.setText("Chưa có nội dung câu hỏi.")
            return

        self.status_lbl.setText("Đang biên dịch...")
        if self.preview_job:
            self.preview_job.cancelled.set()

        from PySide6.QtCore import QThreadPool
        compiler = Compiler(self.services.config.data_dir, engine='pdflatex')
        with self.services.database.connect() as c:
            assets = {r['original_reference']: self.services.config.data_dir / r['relative_path'] for r in c.execute('SELECT qa.original_reference, a.relative_path FROM question_assets qa JOIN assets a ON a.id=qa.asset_id WHERE qa.question_id=?', (self.question.id,))}

        def work(cancelled, progress):
            res = compiler.compile(source, assets, cancelled)
            img, pages = (Compiler.render(res.pdf) if res.ok else (None, 0))
            return res, img, pages

        job = Job(work)
        self.preview_job = job
        job.signals.completed.connect(self.on_preview_ready)
        job.signals.failed.connect(lambda err: self.on_preview_failed(err))
        QThreadPool.globalInstance().start(job)

    def on_preview_ready(self, payload):
        if not self.isVisible():
            return
        result, image_bytes, pages = payload
        if result.ok and image_bytes:
            pix = QPixmap()
            pix.loadFromData(image_bytes)
            self.original_pixmap = pix
            self.status_lbl.setText("Đã xem trước ✓")
            self.fit_preview()
        else:
            self.status_lbl.setText("Lỗi biên dịch ⚠")
            err_msg = result.log or "Biên dịch LaTeX không thành công."
            self.preview_label.setText(f"<div style='color: #ef4444; padding: 12px;'><b>Lỗi LaTeX:</b><br>{err_msg[:400]}</div>")

    def on_preview_failed(self, err):
        self.status_lbl.setText("Lỗi ⚠")
        self.preview_label.setText(f"<div style='color: #ef4444; padding: 12px;'><b>Lỗi tiến trình:</b><br>{err}</div>")

    def fit_preview(self):
        if self.original_pixmap:
            max_w = max(100, self.preview_scroll.viewport().width() - 16)
            scaled = self.original_pixmap.scaledToWidth(min(max_w, self.original_pixmap.width()), Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_preview()

    def save(self):
        source = self.editor.toPlainText().strip()
        if not source:
            QMessageBox.warning(self, "Lỗi nội dung", "Nội dung câu hỏi không được để trống.")
            return

        parsed = parse_questions(source)
        q_type = self.type_combo.currentData() or (parsed[0].question_type if parsed else self.question.question_type)
        solution = parsed[0].solution if parsed else None

        updated_q = replace(
            self.question,
            latex_source=source,
            question_type=q_type,
            cognitive_level=self.level_combo.currentData() or None,
            solution=solution
        )

        try:
            self.services.questions.update(updated_q)
            tax_id = self.taxonomy_combo.currentData()
            m_values = classification(self.nodes, tax_id)
            m_values.update(
                taxonomy_id=tax_id,
                cognitive_level=updated_q.cognitive_level,
                question_type=updated_q.question_type,
                source=self.source_origin.text().strip()
            )
            LibraryService(self.services).save_metadata(self.question.id, m_values)
            self.question_saved.emit(self.question.id)
            self.accept()
        except Exception as err:
            QMessageBox.critical(self, "Không thể lưu", f"Đã xảy ra lỗi khi lưu câu hỏi:\n{err}")
