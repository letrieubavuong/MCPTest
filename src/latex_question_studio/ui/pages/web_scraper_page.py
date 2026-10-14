"""UI Page for Web Question Scraping and Staging Review (Tab 'Thu thập từ Web').

Provides URL crawling, HTML parsing, 2-column staging inspection,
LaTeX editing, live preview, moderation validation, database commit, and Phase K exam export.
"""
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QListWidget, QListWidgetItem, QGroupBox,
    QPlainTextEdit, QCheckBox, QRadioButton, QButtonGroup,
    QScrollArea, QFrame, QLineEdit, QStackedWidget
)

from latex_question_studio.application.assets import AssetStore
from latex_question_studio.application.web_import import (
    QuestionDraft, WebScraperService, sanitize_url
)
from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.scraping.fetcher import SafeFetcher
from latex_question_studio.ui.icons import icon


class WebScrapeWorker(QThread):
    finished = Signal(bool, str, list)

    def __init__(self, service: WebScraperService, mode: str, input_text: str,
                 adapter_name: str, asset_store: AssetStore):
        super().__init__()
        self.service = service
        self.mode = mode
        self.input_text = input_text
        self.adapter_name = adapter_name
        self.asset_store = asset_store
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self._is_cancelled:
                self.finished.emit(False, "Tác vụ đã bị hủy.", [])
                return

            if self.mode == "url":
                ok, msg, drafts = self.service.fetch_and_extract(
                    self.input_text.strip(),
                    asset_store=self.asset_store,
                    check_robots=True
                )
                self.finished.emit(ok, msg, drafts)
            else:
                drafts = self.service.extract_from_html(
                    self.input_text,
                    base_url="http://pasted.local",
                    asset_store=self.asset_store
                )
                self.finished.emit(True, f"Đã trích xuất {len(drafts)} câu hỏi từ mã HTML đã dán.", drafts)
        except Exception as e:
            self.finished.emit(False, f"Lỗi thu thập: {str(e)}", [])


class WebCompileWorker(QThread):
    compiled = Signal(bool, str, str)  # ok, pdf_path, log

    def __init__(self, compiler: Compiler, source: str, assets: dict):
        super().__init__()
        self.compiler = compiler
        self.source = source
        self.assets = assets

    def run(self):
        try:
            res = self.compiler.compile(self.source, assets=self.assets)
            self.compiled.emit(res.ok, str(res.pdf or ""), res.log)
        except Exception as e:
            self.compiled.emit(False, "", str(e))


class WebScraperPage(QWidget):
    def __init__(self, services, compiler_factory=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.compiler_factory = compiler_factory
        self.service = WebScraperService(SafeFetcher())
        self.asset_store = AssetStore(services.config.data_dir)
        self.drafts: list[QuestionDraft] = []
        self.current_draft_idx: int = -1
        self.worker: WebScrapeWorker | None = None
        self.compile_worker: WebCompileWorker | None = None

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. Header Toolbar
        top_bar = QHBoxLayout()
        title_lbl = QLabel("THU THẬP TỪ WEB & DUYỆT CÂU HỎI")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #4ba3eb;")
        top_bar.addWidget(title_lbl)
        top_bar.addStretch()

        self.btn_history = QPushButton("Lịch sử phiên")
        self.btn_history.setIcon(icon("exam"))
        self.btn_history.clicked.connect(self._show_history)
        top_bar.addWidget(self.btn_history)
        main_layout.addLayout(top_bar)

        # 2. Source Configuration Box
        cfg_group = QGroupBox("Nguồn thu thập dữ liệu")
        cfg_layout = QVBoxLayout(cfg_group)

        input_row = QHBoxLayout()
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["URL trang web", "Dán mã HTML thô"])
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        input_row.addWidget(QLabel("Chế độ:"))
        input_row.addWidget(self.combo_mode)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://vietjack.com/... hoặc https://tech24.vn/... hoặc URL bài tập")
        self.url_input.returnPressed.connect(self._start_scrape)
        input_row.addWidget(QLabel("Đường dẫn:"))
        input_row.addWidget(self.url_input, 1)

        self.btn_scrape = QPushButton("Thu thập dữ liệu")
        self.btn_scrape.setIcon(icon("import"))
        self.btn_scrape.setStyleSheet("background-color: #1677d2; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_scrape.clicked.connect(self._start_scrape)
        input_row.addWidget(self.btn_scrape)

        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setIcon(icon("close"))
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_scrape)
        input_row.addWidget(self.btn_cancel)

        cfg_layout.addLayout(input_row)

        # Paste HTML text area (collapsible)
        self.html_paste_edit = QPlainTextEdit()
        self.html_paste_edit.setPlaceholderText("Dán mã nguồn HTML của bài tập hoặc bài viết vào đây...")
        self.html_paste_edit.setMaximumHeight(100)
        self.html_paste_edit.hide()
        cfg_layout.addWidget(self.html_paste_edit)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        cfg_layout.addWidget(self.progress_bar)

        main_layout.addWidget(cfg_group)

        # 3. Status Summary Bar
        status_bar = QHBoxLayout()
        self.summary_lbl = QLabel("Chưa thu thập dữ liệu.")
        self.summary_lbl.setStyleSheet("font-weight: bold; color: #888;")
        status_bar.addWidget(self.summary_lbl)
        status_bar.addStretch()

        self.btn_verify_all = QPushButton("Duyệt nhanh tất cả câu hợp lệ")
        self.btn_verify_all.clicked.connect(self._verify_all_valid)
        status_bar.addWidget(self.btn_verify_all)

        main_layout.addLayout(status_bar)

        # 4. Main 2-Column Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Column: List of extracted questions + raw snippet
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_header = QLabel("Danh sách câu hỏi thu thập được:")
        left_header.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(left_header)

        self.list_questions = QListWidget()
        self.list_questions.currentRowChanged.connect(self._on_question_selected)
        left_layout.addWidget(self.list_questions, 1)

        raw_header = QLabel("Mã nguồn / Đoạn trích gốc:")
        left_layout.addWidget(raw_header)
        self.raw_preview = QPlainTextEdit()
        self.raw_preview.setReadOnly(True)
        self.raw_preview.setMaximumHeight(120)
        left_layout.addWidget(self.raw_preview)

        splitter.addWidget(left_widget)

        # Right Column: Editor & Preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Moderation bar
        mod_bar = QHBoxLayout()
        self.draft_title_edit = QLineEdit()
        self.draft_title_edit.setPlaceholderText("Tiêu đề câu hỏi")
        self.draft_title_edit.textChanged.connect(self._on_draft_field_changed)
        mod_bar.addWidget(QLabel("Tiêu đề:"))
        mod_bar.addWidget(self.draft_title_edit, 1)

        self.combo_qtype = QComboBox()
        self.combo_qtype.addItems(["Trắc nghiệm (MCQ)", "Đúng/Sai (TF)", "Trả lời ngắn", "Tự luận"])
        self.combo_qtype.currentIndexChanged.connect(self._on_type_changed)
        mod_bar.addWidget(QLabel("Loại câu:"))
        mod_bar.addWidget(self.combo_qtype)

        self.btn_verify = QPushButton("✓ Đã kiểm duyệt")
        self.btn_verify.setStyleSheet("background-color: #2da44e; color: white; font-weight: bold;")
        self.btn_verify.clicked.connect(lambda: self._set_current_status("verified"))
        mod_bar.addWidget(self.btn_verify)

        self.btn_reject = QPushButton("✕ Loại bỏ")
        self.btn_reject.setStyleSheet("background-color: #cf222e; color: white;")
        self.btn_reject.clicked.connect(lambda: self._set_current_status("rejected"))
        mod_bar.addWidget(self.btn_reject)

        self.btn_reset_status = QPushButton("↺ Chờ duyệt")
        self.btn_reset_status.clicked.connect(lambda: self._set_current_status("needs_review"))
        mod_bar.addWidget(self.btn_reset_status)

        right_layout.addLayout(mod_bar)

        # Warnings alert
        self.warn_lbl = QLabel("")
        self.warn_lbl.setStyleSheet("color: #d97706; font-weight: bold; padding: 4px; background: #fef3c7; border-radius: 4px;")
        self.warn_lbl.hide()
        right_layout.addWidget(self.warn_lbl)

        # Prompt LaTeX Editor
        prompt_box = QGroupBox("Nội dung đề bài (LaTeX)")
        prompt_box_layout = QVBoxLayout(prompt_box)
        self.edit_prompt = QPlainTextEdit()
        self.edit_prompt.textChanged.connect(self._on_draft_field_changed)
        prompt_box_layout.addWidget(self.edit_prompt)
        right_layout.addWidget(prompt_box, 2)

        # Options Container (Stacked: MCQ, TF, ShortAns, Essay)
        self.options_group = QGroupBox("Các phương án lựa chọn")
        opts_layout = QVBoxLayout(self.options_group)

        self.opts_stack = QStackedWidget()

        # Page 0: MCQ (4 options A, B, C, D + radio button for correct answer)
        mcq_page = QWidget()
        mcq_layout = QVBoxLayout(mcq_page)
        self.mcq_radios = []
        self.mcq_edits = []
        self.mcq_btn_group = QButtonGroup(self)

        for i, letter in enumerate(["A", "B", "C", "D"]):
            row = QHBoxLayout()
            rdo = QRadioButton(letter)
            self.mcq_radios.append(rdo)
            self.mcq_btn_group.addButton(rdo, i)
            rdo.toggled.connect(self._on_draft_field_changed)
            row.addWidget(rdo)

            edt = QLineEdit()
            edt.setPlaceholderText(f"Nội dung phương án {letter}")
            edt.textChanged.connect(self._on_draft_field_changed)
            self.mcq_edits.append(edt)
            row.addWidget(edt, 1)
            mcq_layout.addLayout(row)
        self.opts_stack.addWidget(mcq_page)

        # Page 1: True/False (4 statements a, b, c, d + True/False checkbox)
        tf_page = QWidget()
        tf_layout = QVBoxLayout(tf_page)
        self.tf_checks = []
        self.tf_edits = []

        for i, letter in enumerate(["a", "b", "c", "d"]):
            row = QHBoxLayout()
            chk = QCheckBox(f"{letter}) Đúng")
            self.tf_checks.append(chk)
            chk.toggled.connect(self._on_draft_field_changed)
            row.addWidget(chk)

            edt = QLineEdit()
            edt.setPlaceholderText(f"Mệnh đề {letter})")
            edt.textChanged.connect(self._on_draft_field_changed)
            self.tf_edits.append(edt)
            row.addWidget(edt, 1)
            tf_layout.addLayout(row)
        self.opts_stack.addWidget(tf_page)

        # Page 2: Short Answer
        sa_page = QWidget()
        sa_layout = QHBoxLayout(sa_page)
        sa_layout.addWidget(QLabel("Đáp số / Kết quả:"))
        self.sa_edit = QLineEdit()
        self.sa_edit.setPlaceholderText("Ví dụ: 12 hoặc -3/4 hoặc \\sqrt{2}")
        self.sa_edit.textChanged.connect(self._on_draft_field_changed)
        sa_layout.addWidget(self.sa_edit, 1)
        self.opts_stack.addWidget(sa_page)

        # Page 3: Essay (empty placeholder)
        essay_page = QWidget()
        essay_layout = QVBoxLayout(essay_page)
        essay_layout.addWidget(QLabel("Câu hỏi tự luận không có các phương án lựa chọn."))
        self.opts_stack.addWidget(essay_page)

        opts_layout.addWidget(self.opts_stack)
        right_layout.addWidget(self.options_group, 2)

        # Solution LaTeX Editor
        sol_box = QGroupBox("Lời giải chi tiết (LaTeX)")
        sol_box_layout = QVBoxLayout(sol_box)
        self.edit_sol = QPlainTextEdit()
        self.edit_sol.textChanged.connect(self._on_draft_field_changed)
        sol_box_layout.addWidget(self.edit_sol)
        right_layout.addWidget(sol_box, 1)

        # Preview button & result
        prev_bar = QHBoxLayout()
        self.btn_preview_pdf = QPushButton("Biên dịch xem trước")
        self.btn_preview_pdf.setIcon(icon("preview"))
        self.btn_preview_pdf.clicked.connect(self._compile_preview)
        prev_bar.addWidget(self.btn_preview_pdf)

        self.preview_status_lbl = QLabel("")
        prev_bar.addWidget(self.preview_status_lbl, 1)
        right_layout.addLayout(prev_bar)

        splitter.addWidget(right_widget)
        splitter.setSizes([340, 680])
        main_layout.addWidget(splitter, 1)

        # 5. Bottom Action Bar
        bottom_bar = QHBoxLayout()
        self.btn_commit_db = QPushButton("Nhập câu đã duyệt vào Ngân hàng CSDL")
        self.btn_commit_db.setIcon(icon("bank"))
        self.btn_commit_db.setStyleSheet("background-color: #2da44e; color: white; font-weight: bold; padding: 8px 16px;")
        self.btn_commit_db.clicked.connect(self._commit_to_db)
        bottom_bar.addWidget(self.btn_commit_db)

        self.btn_export_exam = QPushButton("Xuất đề thi Phase K (PDF & ZIP)")
        self.btn_export_exam.setIcon(icon("save"))
        self.btn_export_exam.setStyleSheet("background-color: #1f6feb; color: white; font-weight: bold; padding: 8px 16px;")
        self.btn_export_exam.clicked.connect(self._export_exam_bundle)
        bottom_bar.addWidget(self.btn_export_exam)

        bottom_bar.addStretch()
        main_layout.addLayout(bottom_bar)

    def _on_mode_changed(self, idx: int):
        if idx == 0:
            self.url_input.show()
            self.html_paste_edit.hide()
        else:
            self.url_input.hide()
            self.html_paste_edit.show()

    def _start_scrape(self):
        mode = "url" if self.combo_mode.currentIndex() == 0 else "html"
        raw_text = self.url_input.text() if mode == "url" else self.html_paste_edit.toPlainText()
        if not raw_text.strip():
            QMessageBox.warning(self, "Chưa nhập thông tin", "Vui lòng nhập URL hoặc dán mã HTML để thu thập.")
            return

        text = sanitize_url(raw_text) if mode == "url" else raw_text
        if mode == "url" and text != raw_text:
            self.url_input.setText(text)

        self.btn_scrape.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.show()

        self.worker = WebScrapeWorker(
            self.service, mode, text,
            "Auto", self.asset_store
        )
        self.worker.finished.connect(self._on_scrape_finished)
        self.worker.start()

    def _cancel_scrape(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)

    def _on_scrape_finished(self, ok: bool, message: str, drafts: list[QuestionDraft]):
        self.btn_scrape.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.hide()

        if not ok:
            QMessageBox.critical(self, "Lỗi thu thập", message)
            return

        self.drafts = drafts
        self._refresh_question_list()
        self.summary_lbl.setText(message)
        if self.drafts:
            self.list_questions.setCurrentRow(0)

    def _refresh_question_list(self):
        self.list_questions.clear()
        v_count = sum(1 for d in self.drafts if d.status == "verified")
        r_count = sum(1 for d in self.drafts if d.status == "rejected")
        n_count = len(self.drafts) - v_count - r_count

        for i, d in enumerate(self.drafts):
            status_symbol = "✓" if d.status == "verified" else ("✕" if d.status == "rejected" else "?")
            warn_flag = " ⚠️" if d.warnings else ""
            item = QListWidgetItem(f"[{status_symbol}] Câu {i+1}: {d.title} ({d.question_type}){warn_flag}")
            if d.status == "verified":
                item.setForeground(Qt.GlobalColor.darkGreen)
            elif d.status == "rejected":
                item.setForeground(Qt.GlobalColor.darkRed)
            else:
                item.setForeground(Qt.GlobalColor.darkYellow)
            self.list_questions.addItem(item)

        self.summary_lbl.setText(
            f"Tổng số: {len(self.drafts)} câu | Đã duyệt: {v_count} | Chờ duyệt: {n_count} | Loại bỏ: {r_count}"
        )

    def _on_question_selected(self, row: int):
        if row < 0 or row >= len(self.drafts):
            return
        self.current_draft_idx = row
        draft = self.drafts[row]

        # Block signals while setting values
        self.draft_title_edit.blockSignals(True)
        self.combo_qtype.blockSignals(True)
        self.edit_prompt.blockSignals(True)
        self.edit_sol.blockSignals(True)
        self.mcq_btn_group.blockSignals(True)

        self.draft_title_edit.setText(draft.title)

        type_map = {"mcq": 0, "true_false": 1, "short_answer": 2, "essay": 3}
        self.combo_qtype.setCurrentIndex(type_map.get(draft.question_type, 0))
        self.opts_stack.setCurrentIndex(type_map.get(draft.question_type, 0))

        self.edit_prompt.setPlainText(draft.prompt_latex)
        self.edit_sol.setPlainText(draft.solution_latex)

        # Populate MCQ
        if draft.question_type == "mcq":
            for i, edt in enumerate(self.mcq_edits):
                edt.blockSignals(True)
                edt.setText(draft.options_latex[i] if i < len(draft.options_latex) else "")
                edt.blockSignals(False)
            if draft.correct_choice is not None and 0 <= draft.correct_choice < 4:
                self.mcq_radios[draft.correct_choice].setChecked(True)
            else:
                for r in self.mcq_radios:
                    r.setAutoExclusive(False)
                    r.setChecked(False)
                    r.setAutoExclusive(True)

        # Populate True/False
        elif draft.question_type == "true_false":
            for i, edt in enumerate(self.tf_edits):
                edt.blockSignals(True)
                edt.setText(draft.options_latex[i] if i < len(draft.options_latex) else "")
                edt.blockSignals(False)
            tf_ans = draft.choice_tf_answers or [False] * 4
            for i, chk in enumerate(self.tf_checks):
                chk.blockSignals(True)
                chk.setChecked(tf_ans[i] if i < len(tf_ans) else False)
                chk.blockSignals(False)

        # Populate Short Answer
        elif draft.question_type == "short_answer":
            self.sa_edit.blockSignals(True)
            self.sa_edit.setText(draft.short_answer_key)
            self.sa_edit.blockSignals(False)

        # Display raw source snippet
        self.raw_preview.setPlainText(
            f"URL: {draft.source_url}\n"
            f"Hình ảnh tìm thấy: {len(draft.image_urls)}\n"
            f"Trạng thái: {draft.status}\n\n"
            f"--- Đoạn trích ---\n{draft.review_notes or 'Không có ghi chú'}"
        )

        # Warnings
        if draft.warnings:
            self.warn_lbl.setText("⚠️ CẢNH BÁO: " + " | ".join(draft.warnings))
            self.warn_lbl.show()
        else:
            self.warn_lbl.hide()

        self.draft_title_edit.blockSignals(False)
        self.combo_qtype.blockSignals(False)
        self.edit_prompt.blockSignals(False)
        self.edit_sol.blockSignals(False)
        self.mcq_btn_group.blockSignals(False)

    def _on_type_changed(self, idx: int):
        type_names = ["mcq", "true_false", "short_answer", "essay"]
        if 0 <= self.current_draft_idx < len(self.drafts):
            self.drafts[self.current_draft_idx].question_type = type_names[idx]
            self.opts_stack.setCurrentIndex(idx)
            self._on_draft_field_changed()

    def _on_draft_field_changed(self):
        if self.current_draft_idx < 0 or self.current_draft_idx >= len(self.drafts):
            return
        draft = self.drafts[self.current_draft_idx]

        draft.title = self.draft_title_edit.text()
        draft.prompt_latex = self.edit_prompt.toPlainText()
        draft.solution_latex = self.edit_sol.toPlainText()

        if draft.question_type == "mcq":
            draft.options_latex = [edt.text() for edt in self.mcq_edits]
            checked_id = self.mcq_btn_group.checkedId()
            draft.correct_choice = checked_id if checked_id >= 0 else None
        elif draft.question_type == "true_false":
            draft.options_latex = [edt.text() for edt in self.tf_edits]
            draft.choice_tf_answers = [chk.isChecked() for chk in self.tf_checks]
        elif draft.question_type == "short_answer":
            draft.short_answer_key = self.sa_edit.text().strip()

        draft.validate_and_update_warnings()
        if draft.warnings:
            self.warn_lbl.setText("⚠️ CẢNH BÁO: " + " | ".join(draft.warnings))
            self.warn_lbl.show()
        else:
            self.warn_lbl.hide()

        # Update item in list
        curr_row = self.list_questions.currentRow()
        if 0 <= curr_row < self.list_questions.count():
            status_symbol = "✓" if draft.status == "verified" else ("✕" if draft.status == "rejected" else "?")
            warn_flag = " ⚠️" if draft.warnings else ""
            self.list_questions.item(curr_row).setText(
                f"[{status_symbol}] Câu {curr_row+1}: {draft.title} ({draft.question_type}){warn_flag}"
            )

    def _set_current_status(self, new_status: str):
        if self.current_draft_idx < 0 or self.current_draft_idx >= len(self.drafts):
            return
        self._on_draft_field_changed()
        draft = self.drafts[self.current_draft_idx]
        if new_status == "verified":
            draft.validate_and_update_warnings()
            if draft.has_missing_images:
                QMessageBox.warning(
                    self, "Không thể duyệt câu hỏi",
                    "Câu hỏi này bị thiếu hình ảnh từ nguồn web. Không thể đánh dấu 'Đã kiểm duyệt' khi chưa bổ sung ảnh đầy đủ."
                )
                return
            if draft.warnings:
                reply = QMessageBox.question(
                    self, "Cảnh báo dữ liệu",
                    f"Câu hỏi có cảnh báo:\n" + "\n".join(f"- {w}" for w in draft.warnings) + "\n\nBạn có chắc chắn muốn duyệt không?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        draft.status = new_status
        self._refresh_question_list()
        self.list_questions.setCurrentRow(self.current_draft_idx)

    def _verify_all_valid(self):
        count = 0
        skipped = 0
        for d in self.drafts:
            d.validate_and_update_warnings()
            if not d.warnings and not d.has_missing_images:
                d.status = "verified"
                count += 1
            else:
                skipped += 1
        self._refresh_question_list()
        msg = f"Đã chuyển {count} câu hỏi hợp lệ sang trạng thái 'Đã kiểm duyệt' (Verified)."
        if skipped > 0:
            msg += f"\nBỏ qua {skipped} câu hỏi có cảnh báo hoặc thiếu thông tin/ảnh."
        QMessageBox.information(self, "Kết quả duyệt hàng loạt", msg)

    def _compile_preview(self):
        if self.current_draft_idx < 0 or self.current_draft_idx >= len(self.drafts):
            return
        self._on_draft_field_changed()
        draft = self.drafts[self.current_draft_idx]

        if not self.compiler_factory:
            # Fallback compiler
            compiler = Compiler(self.services.config.data_dir)
        else:
            compiler = self.compiler_factory()

        latex_snippet = draft.to_ex_test_latex()
        self.preview_status_lbl.setText("Đang biên dịch kiểm tra...")

        assets_map = {}
        for ast in draft.local_assets:
            rel = ast.get("relative_path", "")
            stg = ast.get("staging_path", "")
            if rel and stg and Path(stg).is_file():
                assets_map[rel] = stg

        self.compile_worker = WebCompileWorker(compiler, latex_snippet, assets_map)
        self.compile_worker.compiled.connect(self._on_preview_compiled)
        self.compile_worker.start()

    def _on_preview_compiled(self, ok: bool, pdf_path: str, log: str):
        if ok:
            self.preview_status_lbl.setText("✓ pdfLaTeX biên dịch thành công!")
            self.preview_status_lbl.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.preview_status_lbl.setText("✕ Biên dịch thất bại!")
            self.preview_status_lbl.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.warning(self, "Lỗi biên dịch LaTeX", f"Chi tiết nhật ký biên dịch:\n\n{log[:600]}")

    def _commit_to_db(self):
        verified_count = sum(1 for d in self.drafts if d.status == "verified")
        if verified_count == 0:
            QMessageBox.warning(
                self, "Chưa duyệt câu hỏi",
                "Chưa có câu hỏi nào được xác nhận (Verified). Vui lòng nhấn nút '[✓ Đã kiểm duyệt]' trước khi lưu."
            )
            return

        reply = QMessageBox.question(
            self, "Xác nhận nhập CSDL",
            f"Bạn có chắc chắn muốn nhập {verified_count} câu hỏi đã kiểm duyệt vào CSDL ngân hàng không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        res = self.service.commit_drafts_to_db(self.drafts, self.services, self.asset_store)
        if res["ok"]:
            QMessageBox.information(self, "Thành công", res["message"])
            # Remove committed drafts from staging
            self.drafts = [d for d in self.drafts if d.status != "verified"]
            self._refresh_question_list()
        else:
            QMessageBox.critical(self, "Lỗi nhập CSDL", res.get("message", "Thao tác thất bại."))

    def _export_exam_bundle(self):
        verified_count = sum(1 for d in self.drafts if d.status == "verified")
        if verified_count == 0:
            QMessageBox.warning(
                self, "Chưa duyệt câu hỏi",
                "Chưa có câu hỏi nào được xác nhận (Verified) để xuất đề thi."
            )
            return

        target_dir = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất đề thi Phase K")
        if not target_dir:
            return

        if not self.compiler_factory:
            compiler = Compiler(self.services.config.data_dir)
        else:
            compiler = self.compiler_factory()

        res = self.service.export_drafts_to_exam_bundle(
            self.drafts,
            "Đề thi thu thập từ Web",
            Path(target_dir),
            compiler
        )

        if res["ok"]:
            QMessageBox.information(
                self, "Xuất đề thành công",
                f"{res['message']}\n\nĐường dẫn PDF: {res['pdf_path']}\nĐường dẫn ZIP: {res['zip_path']}"
            )
        else:
            QMessageBox.critical(
                self, "Xuất đề thất bại",
                f"LỖI: {res.get('error', 'Không xác định')}\n\nNhật ký biên dịch:\n{res.get('compile_log', '')[:500]}"
            )

    def _show_history(self):
        QMessageBox.information(
            self, "Lịch sử thu thập",
            f"Phiên hiện tại: {len(self.drafts)} câu hỏi trong khu vực staging review."
        )
