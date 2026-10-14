"""UI Page for Question Deduplication (Tab 'Câu hỏi trùng').

Provides two scanning scopes (Files and Database), side-by-side comparative inspection,
metadata merging, and safe teacher-confirmed deletion.
"""
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QListWidget, QListWidgetItem, QGroupBox,
    QPlainTextEdit, QCheckBox, QRadioButton, QButtonGroup,
    QScrollArea, QFrame, QLineEdit, QSpinBox
)

from latex_question_studio.application.dedup import (
    DeduplicationService, DuplicateGroup, DuplicateItem
)
from latex_question_studio.ui.icons import icon


class DedupScanWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, service: DeduplicationService, scope: str, files: list, filters: dict):
        super().__init__()
        self.service = service
        self.scope = scope
        self.files = files
        self.filters = filters
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self.scope == "files":
                results = self.service.scan_files(
                    self.files,
                    cancelled=lambda: self._is_cancelled,
                    progress_callback=self.progress.emit,
                )
            else:
                results = self.service.scan_database(
                    self.filters,
                    cancelled=lambda: self._is_cancelled,
                    progress_callback=self.progress.emit,
                )
            self.finished.emit(results)
        except Exception as e:
            self.failed.emit(str(e))


class DedupPage(QWidget):
    def __init__(self, services, parent=None):
        super().__init__(parent)
        self.services = services
        self.service = DeduplicationService(services)
        self.worker: DedupScanWorker | None = None
        self.groups: list[DuplicateGroup] = []
        self.current_group_idx: int = -1

        self.setObjectName("dedupPage")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. Header & Controls Bar
        header_box = QGroupBox("Phạm vi & Thiết lập quét trùng lặp")
        header_layout = QVBoxLayout(header_box)
        header_layout.setSpacing(8)

        # Top row: Scope selector and file/db controls
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Chế độ quét:"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("Trong Cơ sở dữ liệu hiện hành", "database")
        self.scope_combo.addItem("Trong các tệp mã nguồn (.tex)", "files")
        self.scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        top_row.addWidget(self.scope_combo)

        # Database filters
        self.db_filter_widget = QWidget()
        db_fl = QHBoxLayout(self.db_filter_widget)
        db_fl.setContentsMargins(0, 0, 0, 0)
        self.type_filter = QComboBox()
        self.type_filter.addItem("Mọi loại câu hỏi", "")
        self.type_filter.addItem("Trắc nghiệm (MCQ)", "mcq")
        self.type_filter.addItem("Đúng/Sai (TF)", "true_false")
        self.type_filter.addItem("Trả lời ngắn", "short_answer")
        self.type_filter.addItem("Tự luận", "essay")
        db_fl.addWidget(self.type_filter)

        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("Lọc từ khóa / nội dung...")
        db_fl.addWidget(self.search_filter)
        top_row.addWidget(self.db_filter_widget)

        # File scope controls
        self.file_control_widget = QWidget()
        self.file_control_widget.setVisible(False)
        file_fl = QHBoxLayout(self.file_control_widget)
        file_fl.setContentsMargins(0, 0, 0, 0)
        self.select_files_btn = QPushButton("Chọn tệp .tex...")
        self.select_files_btn.clicked.connect(self._select_files)
        file_fl.addWidget(self.select_files_btn)
        self.file_list_lbl = QLabel("Chưa chọn tệp nào")
        self.file_list_lbl.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        file_fl.addWidget(self.file_list_lbl)
        top_row.addWidget(self.file_control_widget)

        top_row.addStretch()

        # Action buttons
        self.scan_btn = QPushButton("Bắt đầu quét trùng")
        self.scan_btn.setProperty("primary", True)
        self.scan_btn.clicked.connect(self.start_scan)
        top_row.addWidget(self.scan_btn)

        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_scan)
        top_row.addWidget(self.cancel_btn)

        header_layout.addLayout(top_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        header_layout.addWidget(self.progress_bar)

        # Status summary banner
        self.summary_lbl = QLabel("Sẵn sàng quét tìm câu hỏi trùng lặp hoặc tương đương.")
        self.summary_lbl.setStyleSheet("font-weight: 500; color: #2c3e50;")
        header_layout.addWidget(self.summary_lbl)

        main_layout.addWidget(header_box)

        # 2. Splitter: Left = Group List, Right = Comparison details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Groups list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("DANH SÁCH NHÓM TRÙNG LẶP"))

        self.group_list = QListWidget()
        self.group_list.currentRowChanged.connect(self._on_group_selected)
        left_layout.addWidget(self.group_list)

        # Left export tools
        report_row = QHBoxLayout()
        self.export_report_btn = QPushButton("Xuất báo cáo...")
        self.export_report_btn.setEnabled(False)
        self.export_report_btn.clicked.connect(self._export_report)
        report_row.addWidget(self.export_report_btn)

        self.export_tex_btn = QPushButton("Xuất .tex đã lọc...")
        self.export_tex_btn.setEnabled(False)
        self.export_tex_btn.clicked.connect(self._export_clean_tex)
        report_row.addWidget(self.export_tex_btn)
        left_layout.addLayout(report_row)

        splitter.addWidget(left_panel)
        splitter.setStretchFactor(0, 3)

        # Right panel: Comparative inspection & actions
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Group Info Banner
        self.group_info_lbl = QLabel("Chọn một nhóm bên trái để xem chi tiết đối chiếu.")
        self.group_info_lbl.setWordWrap(True)
        self.group_info_lbl.setStyleSheet("padding: 8px; background: #eef2f7; border-radius: 4px; font-weight: bold;")
        right_layout.addWidget(self.group_info_lbl)

        # Scroll area for comparison cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        self.scroll_area.setWidget(self.cards_container)
        right_layout.addWidget(self.scroll_area, 1)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        self.ignore_btn = QPushButton("Bỏ qua nhóm này")
        self.ignore_btn.clicked.connect(self._ignore_current_group)
        self.ignore_btn.setEnabled(False)
        action_bar.addWidget(self.ignore_btn)

        self.merge_btn = QPushButton("Gộp metadata vào bản gốc")
        self.merge_btn.clicked.connect(self._merge_metadata)
        self.merge_btn.setEnabled(False)
        action_bar.addWidget(self.merge_btn)

        action_bar.addStretch()

        self.delete_btn = QPushButton("Xóa các bản được chọn")
        self.delete_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setEnabled(False)
        action_bar.addWidget(self.delete_btn)

        right_layout.addLayout(action_bar)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 7)

        main_layout.addWidget(splitter, 1)

        self.selected_files = []

    def _on_scope_changed(self, index):
        is_files = (self.scope_combo.currentData() == "files")
        self.db_filter_widget.setVisible(not is_files)
        self.file_control_widget.setVisible(is_files)
        self.export_tex_btn.setEnabled(is_files and len(self.groups) > 0)

    def _select_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Chọn các file .tex để quét trùng", "", "LaTeX Files (*.tex)"
        )
        if paths:
            self.selected_files = paths
            self.file_list_lbl.setText(f"Đã chọn {len(paths)} tệp")

    def start_scan(self):
        scope = self.scope_combo.currentData()
        if scope == "files" and not self.selected_files:
            QMessageBox.warning(self, "Chưa chọn tệp", "Vui lòng chọn ít nhất một tệp .tex để quét.")
            return

        self.scan_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.summary_lbl.setText("Đang khởi động tiến trình quét...")
        self.group_list.clear()
        self._clear_cards()

        filters = {
            "question_type": self.type_filter.currentData(),
            "query": self.search_filter.text().strip(),
        }

        self.worker = DedupScanWorker(self.service, scope, self.selected_files, filters)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.failed.connect(self._on_scan_failed)
        self.worker.start()

    def cancel_scan(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.summary_lbl.setText("Đang hủy tiến trình quét...")

    def _on_progress(self, current, total, msg):
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.summary_lbl.setText(f"[{pct}%] {msg}")

    def _on_scan_finished(self, groups: list[DuplicateGroup]):
        self.groups = groups
        self.scan_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        total_dups = sum(len(g.items) - 1 for g in groups)
        self.summary_lbl.setText(
            f"Hoàn tất quét! Phát hiện {len(groups)} nhóm trùng lặp (Tổng cộng {total_dups} câu hỏi dư thừa có thể loại bỏ)."
        )

        self.export_report_btn.setEnabled(len(groups) > 0)
        self.export_tex_btn.setEnabled(self.scope_combo.currentData() == "files" and len(groups) > 0)

        # Populate groups in list
        self.group_list.clear()
        for idx, g in enumerate(groups):
            badge = ""
            if g.match_level == "exact":
                badge = "[100% Trùng tuyệt đối]"
            elif g.match_level == "permutation":
                badge = "[95% Hoán vị phương án]"
            else:
                badge = f"[{int(g.confidence*100)}% Gợi ý tương tự]"

            item = QListWidgetItem(f"Nhóm #{idx + 1} ({len(g.items)} câu) {badge}")
            item.setToolTip(g.match_reason)
            self.group_list.addItem(item)

        if groups:
            self.group_list.setCurrentRow(0)

    def _on_scan_failed(self, error: str):
        self.scan_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.summary_lbl.setText(f"Lỗi quét: {error}")
        QMessageBox.critical(self, "Lỗi quét trùng lặp", f"Đã xảy ra lỗi: {error}")

    def _clear_cards(self):
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _on_group_selected(self, row: int):
        if row < 0 or row >= len(self.groups):
            self.current_group_idx = -1
            self.group_info_lbl.setText("Chọn một nhóm bên trái để xem chi tiết đối chiếu.")
            self._clear_cards()
            self.ignore_btn.setEnabled(False)
            self.merge_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        self.current_group_idx = row
        group = self.groups[row]
        self.group_info_lbl.setText(
            f"Nhóm #{row + 1} • {len(group.items)} bản ghi • Độ tin cậy: {group.confidence*100:.0f}%\n"
            f"Lý do: {group.match_reason}"
        )
        self.ignore_btn.setEnabled(True)
        self.merge_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

        self._render_group_cards(group)

    def _render_group_cards(self, group: DuplicateGroup):
        self._clear_cards()

        # Button group for primary radio buttons
        bg = QButtonGroup(self.cards_container)

        for it in group.items:
            card = QFrame()
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card.setStyleSheet(
                "QFrame { background: #ffffff; border: 1px solid #dcdcdc; border-radius: 6px; padding: 8px; }"
            )
            card_layout = QVBoxLayout(card)

            # Header row
            h_row = QHBoxLayout()
            is_primary = (it.id == group.primary_id)
            rb = QRadioButton("Giữ lại bản gốc")
            rb.setChecked(is_primary)
            bg.addButton(rb)
            rb.toggled.connect(lambda checked, item_id=it.id: self._set_primary(item_id, checked))
            h_row.addWidget(rb)

            # Checkbox: Delete this item (DEFAULT FALSE)
            cb = QCheckBox("Xóa bản này")
            cb.setChecked(it.id in group.selected_to_delete)
            cb.setEnabled(not is_primary)
            cb.toggled.connect(lambda checked, item_id=it.id: self._toggle_delete(item_id, checked))
            h_row.addWidget(cb)
            card_layout.addLayout(h_row)

            # Metadata info
            meta_txt = f"<b>ID:</b> {it.id[:16]}...<br><b>Nguồn:</b> {it.source_location}"
            if it.created_at:
                meta_txt += f" | <b>Ngày:</b> {it.created_at[:10]}"
            if it.references:
                meta_txt += f"<br><span style='color: #e67e22;'><b>Đang dùng trong:</b> {', '.join(it.references)}</span>"
            lbl = QLabel(meta_txt)
            lbl.setWordWrap(True)
            card_layout.addWidget(lbl)

            # Source editor
            editor = QPlainTextEdit()
            editor.setPlainText(it.source)
            editor.setReadOnly(True)
            editor.setMaximumHeight(200)
            card_layout.addWidget(editor)

            # Solution display if any
            if it.solution:
                sol_lbl = QLabel(f"<b>Lời giải:</b> {it.solution[:150]}")
                sol_lbl.setWordWrap(True)
                card_layout.addWidget(sol_lbl)

            self.cards_layout.addWidget(card)

    def _set_primary(self, item_id: str, checked: bool):
        if not checked or self.current_group_idx < 0:
            return
        group = self.groups[self.current_group_idx]
        group.primary_id = item_id
        # Primary cannot be selected to delete
        group.selected_to_delete.discard(item_id)
        self._render_group_cards(group)

    def _toggle_delete(self, item_id: str, checked: bool):
        if self.current_group_idx < 0:
            return
        group = self.groups[self.current_group_idx]
        if checked:
            group.selected_to_delete.add(item_id)
        else:
            group.selected_to_delete.discard(item_id)

    def _ignore_current_group(self):
        if self.current_group_idx < 0:
            return
        del self.groups[self.current_group_idx]
        self.group_list.takeItem(self.current_group_idx)
        if self.groups:
            self.group_list.setCurrentRow(min(self.current_group_idx, len(self.groups) - 1))
        else:
            self._on_group_selected(-1)

    def _merge_metadata(self):
        if self.current_group_idx < 0:
            return
        group = self.groups[self.current_group_idx]
        secondary_ids = [it.id for it in group.items if it.id != group.primary_id]
        if not secondary_ids:
            QMessageBox.information(self, "Không có bản sao", "Nhóm chỉ có 1 bản ghi duy nhất.")
            return

        ok = self.service.merge_metadata(group.primary_id, secondary_ids)
        if ok:
            QMessageBox.information(
                self, "Gộp thành công",
                f"Đã gộp toàn bộ nhãn taxonomy và metadata từ {len(secondary_ids)} câu vào bản gốc [{group.primary_id[:8]}]."
            )
        else:
            QMessageBox.warning(self, "Lỗi gộp", "Không thể gộp metadata.")

    def _delete_selected(self):
        if self.current_group_idx < 0:
            return
        group = self.groups[self.current_group_idx]
        to_delete = list(group.selected_to_delete)
        if not to_delete:
            QMessageBox.information(
                self, "Chưa chọn bản xóa",
                "Vui lòng tick chọn 'Xóa bản này' ở các câu hỏi trùng lặp mà bạn muốn xóa."
            )
            return

        confirm = QMessageBox.question(
            self, "Xác nhận xóa vĩnh viễn",
            f"Bạn có chắc chắn muốn xóa {len(to_delete)} câu hỏi được chọn khỏi CSDL?\n"
            f"Hành động này không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        count, errors = self.service.delete_selected(to_delete)
        if errors:
            QMessageBox.warning(self, "Cảnh báo xóa", "\n".join(errors))

        if count > 0:
            QMessageBox.information(self, "Xóa hoàn tất", f"Đã xóa thành công {count} câu hỏi khỏi CSDL.")
            # Remove deleted from group items
            group.items = [it for it in group.items if it.id not in to_delete]
            group.selected_to_delete.clear()
            if len(group.items) <= 1:
                self._ignore_current_group()
            else:
                self._render_group_cards(group)

    def _export_report(self):
        if not self.groups:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Xuất báo cáo câu hỏi trùng", "bao-cao-cau-hoi-trung.json",
            "JSON Report (*.json);;CSV Report (*.csv)"
        )
        if not path:
            return
        fmt = "csv" if path.endswith(".csv") else "json"
        out = self.service.export_report(self.groups, path, fmt)
        QMessageBox.information(self, "Xuất báo cáo", f"Đã lưu báo cáo tại:\n{out}")

    def _export_clean_tex(self):
        if not self.selected_files or not self.groups:
            return
        src_path = self.selected_files[0]
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Xuất file TeX đã lọc bỏ trùng lặp", f"cleaned_{Path(src_path).name}",
            "LaTeX File (*.tex)"
        )
        if not out_path:
            return

        # Determine all items to keep
        deleted_ids = set()
        for g in self.groups:
            deleted_ids.update(g.selected_to_delete)

        all_item_ids = {it.id for g in self.groups for it in g.items}
        items_to_keep = all_item_ids - deleted_ids

        out = self.service.export_clean_tex(src_path, items_to_keep, out_path)
        QMessageBox.information(self, "Xuất TeX thành công", f"Đã tạo file mới đã loại bỏ câu trùng tại:\n{out}")
