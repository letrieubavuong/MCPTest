"""File-based exam mixing alongside the existing question-bank workflow."""
import json
import re

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGridLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

from latex_question_studio.application.tex_exams import TexExamService
from latex_question_studio.ui.components.workspace import CommandToolbar, Workspace
from latex_question_studio.ui.jobs import Job
from latex_question_studio.ui.panels.question_preview import QuestionPreview


class TexExamPage(QWidget):
    def __init__(self, services, run_job=None, parent=None):
        super().__init__(parent)
        self.services, self.run_job = services, run_job
        self.service = TexExamService(services) if services else None
        self.document = self.batch = self.job = None
        self.generation = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar = CommandToolbar('Trộn file TeX', self)
        self.open_action = self.toolbar.command('import', 'Chọn file TeX', self.choose_file)
        self.generate_action = self.toolbar.command('exam', 'Tạo mã đề', self.generate_variants, True)
        self.export_action = self.toolbar.command('save', 'Xuất các mã đề và bảng đáp án', self.export_variants)
        self.cancel_action = self.toolbar.command('close', 'Hủy tác vụ', self.cancel)
        layout.addWidget(self.toolbar)
        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        self.file_path.setPlaceholderText('Chưa chọn file TeX')
        layout.addWidget(self.file_path)
        self.controls = QWidget()
        form = QGridLayout(self.controls)
        form.setContentsMargins(0, 0, 0, 0)
        self.codes = QLineEdit('101, 102, 103, 104')
        self.codes.setToolTip('Các mã đề, phân cách bằng dấu phẩy')
        self.seed = QSpinBox()
        self.seed.setRange(0, 2_000_000_000)
        self.seed.setValue(2027)
        self.seed.setToolTip('Seed để tái lập thứ tự câu và phương án')
        form.addWidget(QLabel('Mã đề'), 0, 0)
        form.addWidget(self.codes, 0, 1, 1, 3)
        form.addWidget(QLabel('Seed'), 0, 4)
        form.addWidget(self.seed, 0, 5)
        self.shuffle_questions = QCheckBox('Xáo câu trong từng phần')
        self.shuffle_questions.setChecked(True)
        self.shuffle_options = QCheckBox('Xáo phương án trắc nghiệm')
        self.shuffle_options.setChecked(True)
        self.audience = QComboBox()
        self.audience.addItem('Đề học sinh', False)
        self.audience.addItem('Đề kèm lời giải', True)
        self.pdf = QCheckBox('Xuất PDF')
        self.pdf.setChecked(True)
        form.addWidget(self.shuffle_questions, 1, 0, 1, 2)
        form.addWidget(self.shuffle_options, 1, 2, 1, 2)
        form.addWidget(self.audience, 1, 4)
        form.addWidget(self.pdf, 1, 5)
        form.setColumnStretch(1, 1)
        layout.addWidget(self.controls)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.workspace = Workspace('texExamSplit')
        left = QWidget()
        box = QVBoxLayout(left)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(QLabel('MÃ ĐỀ'))
        self.variants = QListWidget()
        self.variants.setMaximumHeight(150)
        box.addWidget(self.variants)
        self.mapping = QTableWidget(0, 4)
        self.mapping.setHorizontalHeaderLabels(['Phần', 'Câu', 'Câu gốc', 'Đáp án'])
        self.mapping.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.mapping.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        box.addWidget(self.mapping, 1)
        self.workspace.addWidget(left)
        self.preview = QuestionPreview(services, run_job)
        self.workspace.addWidget(self.preview)
        self.workspace.setSizes([340, 800])
        layout.addWidget(self.workspace, 1)
        self.status = QLabel('Chưa tải đề từ file TeX.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.variants.currentRowChanged.connect(self.preview_selected)
        self.audience.currentIndexChanged.connect(lambda: self.preview_selected(self.variants.currentRow()))
        self._busy(False)

    def _busy(self, value):
        self.open_action.setEnabled(bool(self.service) and not value)
        self.generate_action.setEnabled(self.document is not None and not value)
        self.export_action.setEnabled(self.batch is not None and not value)
        self.cancel_action.setEnabled(value)
        self.controls.setEnabled(not value)
        self.variants.setEnabled(not value)

    def _work(self, label, function, completed):
        if self.job:
            return
        self.preview.cancel()
        self.generation += 1
        generation = self.generation
        job = Job(function)
        self.job = job
        self._busy(True)
        self.status.setText(label + '…')
        def ready(result):
            if generation != self.generation:
                return
            self.job = None
            completed(result)
            self._busy(False)
        def failed(message):
            if generation != self.generation:
                return
            self.job = None
            self._busy(False)
            self.status.setText(label + ' đã dừng: ' + message)
        job.signals.completed.connect(ready)
        job.signals.failed.connect(failed)
        job.signals.progress.connect(lambda current, total: self.status.setText(f'{label} · {current}/{total}') if generation == self.generation else None)
        self.run_job(job) if self.run_job else QThreadPool.globalInstance().start(job)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Chọn đề TeX để trộn', '', 'LaTeX (*.tex)')
        if path:
            self.load_path(path)

    def load_path(self, path):
        self._work('Đọc đề TeX', lambda cancelled, progress: self.service.load(path, cancelled), self.set_document)

    def set_document(self, document):
        self.document, self.batch = document, None
        self.file_path.setText(document['source_path'])
        self.file_path.setToolTip(document['source_path'])
        self.variants.clear()
        self.mapping.setRowCount(0)
        self.preview.set_source('')
        self.preview.code.setPlainText(document['source'])
        self.preview.tabs.setCurrentIndex(1)
        self.summary.setText(f"{document['question_count']} câu · {len(document['sections'])} phần · " + ('Mẫu TeX gốc' if document['full_document'] else 'Đoạn câu hỏi, mẫu MAPClass'))
        self.status.setText('Đã tải file TeX.')
        self._busy(False)

    def generate_variants(self):
        if not self.document or self.job:
            return
        codes = [code for code in re.split(r'[,;\s]+', self.codes.text().strip()) if code]
        document, seed = self.document, self.seed.value()
        questions, options = self.shuffle_questions.isChecked(), self.shuffle_options.isChecked()
        self._work('Trộn mã đề', lambda cancelled, progress: self.service.generate(document, codes, seed, questions, options, cancelled, progress), self.set_batch)

    def set_batch(self, batch):
        self.batch = batch
        self.variants.blockSignals(True)
        self.variants.clear()
        for variant in batch['variants']:
            self.variants.addItem('Mã đề ' + variant['exam_code'])
        self.variants.blockSignals(False)
        self.variants.setCurrentRow(0)
        self.preview.tabs.setCurrentIndex(0)
        self.status.setText(f"Đã tạo {len(batch['variants'])} mã đề, mỗi mã {self.document['question_count']} câu.")
        self._busy(False)

    def preview_selected(self, index):
        if not self.batch or not 0 <= index < len(self.batch['variants']):
            return
        variant = self.batch['variants'][index]
        self.mapping.setRowCount(len(variant['questions']))
        for row, question in enumerate(variant['questions']):
            answer = question['answer']
            value = answer.get('correct_letter', answer.get('value', ' '.join('Đ' if v else 'S' for v in answer.get('truth', [])) or 'Tự luận'))
            for column, text in enumerate((question['section'], question['number'], question['original_number'], value)):
                cell = QTableWidgetItem(str(text));cell.setToolTip(str(text));self.mapping.setItem(row, column, cell)
        try:
            source, body, profile, assets = self.service.preview(self.batch, variant, self.audience.currentData())
            self.preview.set_source(body, assets, preamble_file=profile, display_source=source)
        except (ValueError, OSError) as error:
            self.preview.set_source('')
            self.preview.code.setPlainText(variant['source'])
            self.preview.errors.setPlainText(str(error))
            self.preview.status.setText('Không thể chuẩn bị bản đang chọn; xem tab Lỗi.')

    def export_variants(self):
        if not self.batch or self.job:
            return
        folder = QFileDialog.getExistingDirectory(self, 'Thư mục xuất các mã đề')
        if not folder:
            return
        path = self.services.config.data_dir / 'compiler.json'
        try:
            config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        except (ValueError, OSError):
            config = {}
        batch, pdf, solutions = self.batch, self.pdf.isChecked(), self.audience.currentData()
        self._work('Xuất mã đề', lambda cancelled, progress: self.service.export(batch, folder, pdf, solutions, config.get('engine', 'pdflatex'), cancelled, progress),
                   lambda target: self.status.setText('Đã xuất mã đề và bảng đáp án: ' + str(target)))

    def cancel(self):
        if self.job:
            self.job.cancelled.set()
            self.status.setText('Đang hủy tác vụ…')

    def cancel_all(self):
        self.generation += 1
        self.cancel()
        self.preview.cancel()

    def closeEvent(self, event):
        self.cancel_all()
        super().closeEvent(event)
