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

        self.delete_btn = QPushButton("🗑️ Xóa khỏi ngân hàng CSDL (0 câu đã chọn)")
        self.delete_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 6px 12px;")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.delete_btn.setEnabled(False)
        action_bar.addWidget(self.delete_btn)

        right_layout.addLayout(action_bar)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 7)

        main_layout.addWidget(splitter, 1)

        self.selected_files = []
        self._on_scope_changed(0)

    def _on_scope_changed(self, index):
        is_files = (self.scope_combo.currentData() == "files")
        self.db_filter_widget.setVisible(not is_files)
        self.file_control_widget.setVisible(is_files)
        self.merge_btn.setVisible(not is_files)
        self.export_tex_btn.setVisible(is_files)
        self._update_action_bar_counts()
        if 0 <= self.current_group_idx < len(self.groups):
            self._render_group_cards(self.groups[self.current_group_idx])

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
        else:
            self._update_action_bar_counts()

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
            self._update_action_bar_counts()
            return

        self.current_group_idx = row
        group = self.groups[row]
        self.group_info_lbl.setText(
            f"Nhóm #{row + 1} • {len(group.items)} bản ghi • Độ tin cậy: {group.confidence*100:.0f}%\n"
            f"Lý do: {group.match_reason}"
        )
        self.ignore_btn.setEnabled(True)
        self.merge_btn.setEnabled(self.scope_combo.currentData() == "database")
        self._render_group_cards(group)
        self._update_action_bar_counts()

    def _render_group_cards(self, group: DuplicateGroup):
        self._clear_cards()
        scope = self.scope_combo.currentData()

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
            cb_label = "Xóa khỏi CSDL" if scope == "database" else "Loại khỏi file .tex"
            cb = QCheckBox(cb_label)
            cb.setChecked(it.id in group.selected_to_delete)
            cb.setEnabled(not is_primary)
            if is_primary:
                cb.setToolTip("Bản gốc đang được bảo vệ giữ lại, không thể đánh dấu xóa/loại bỏ.")
            else:
                cb.setToolTip(f"Đánh dấu câu này để {'xóa khỏi CSDL' if scope == 'database' else 'loại khỏi file .tex'}")
            cb.toggled.connect(lambda checked, item_id=it.id: self._toggle_delete(item_id, checked))
            h_row.addWidget(cb)
            card_layout.addLayout(h_row)

            # Metadata info
            if scope == "files":
                meta_txt = f"<b>Nguồn:</b> {it.source_location}"
                if it.span_start >= 0 and it.span_end >= 0:
                    meta_txt += f" | <b>Vị trí ký tự:</b> {it.span_start} - {it.span_end}"
            else:
                meta_txt = f"<b>ID:</b> {it.id[:16]}...<br><b>Nguồn:</b> {it.source_location}"
                if it.created_at:
                    meta_txt += f" | <b>Ngày:</b> {it.created_at[:10]}"
                if it.references:
                    meta_txt += f"<br><span style='color: #e67e22;'>⚠️ <b>Đang dùng trong:</b> {', '.join(it.references)}</span>"

            if is_primary:
                meta_txt = "<span style='color: #27ae60; font-weight: bold;'>[BẢN GỐC - ĐƯỢC BẢO VỆ GIỮ LẠI]</span><br>" + meta_txt

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
        if not checked or self.current_group_idx < 0 or self.current_group_idx >= len(self.groups):
            return
        group = self.groups[self.current_group_idx]
        group.primary_id = item_id
        # Primary cannot be selected to delete
        group.selected_to_delete.discard(item_id)
        self._render_group_cards(group)
        self._update_action_bar_counts()

    def _toggle_delete(self, item_id: str, checked: bool):
        if self.current_group_idx < 0 or self.current_group_idx >= len(self.groups):
            return
        group = self.groups[self.current_group_idx]
        if checked:
            group.selected_to_delete.add(item_id)
        else:
            group.selected_to_delete.discard(item_id)
        self._update_action_bar_counts()

    def _update_action_bar_counts(self):
        scope = self.scope_combo.currentData()
        if scope == "database":
            current_group = self.groups[self.current_group_idx] if (0 <= self.current_group_idx < len(self.groups)) else None
            count = len(current_group.selected_to_delete) if current_group else 0
            self.delete_btn.setText(f"🗑️ Xóa khỏi ngân hàng CSDL ({count} câu đã chọn)")
            self.delete_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 6px 12px;")
            self.delete_btn.setEnabled(count > 0)
        else:
            total_selected = sum(len(g.selected_to_delete) for g in self.groups)
            self.delete_btn.setText(f"✂️ Loại câu khỏi file .tex ({total_selected} câu đã chọn)")
            self.delete_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px 12px;")
            self.delete_btn.setEnabled(total_selected > 0)
            self.export_tex_btn.setEnabled(total_selected > 0)
            self.export_tex_btn.setText(f"Xuất file .tex đã lọc ({total_selected} câu)...")

    def _ignore_current_group(self):
        if self.current_group_idx < 0 or self.current_group_idx >= len(self.groups):
            return
        del self.groups[self.current_group_idx]
        self.group_list.takeItem(self.current_group_idx)
        if self.groups:
            self.group_list.setCurrentRow(min(self.current_group_idx, len(self.groups) - 1))
        else:
            self._on_group_selected(-1)
        self._update_action_bar_counts()

    def _merge_metadata(self):
        if self.current_group_idx < 0 or self.current_group_idx >= len(self.groups):
            return
        group = self.groups[self.current_group_idx]
        secondary_ids = [it.id for it in group.items if it.id != group.primary_id]
        if not secondary_ids:
            QMessageBox.information(self, "Không có bản sao", "Nhóm chỉ có 1 bản ghi duy nhất.")
            return

        confirm = QMessageBox.question(
            self, "Xác nhận gộp metadata",
            f"Bạn có chắc muốn gộp toàn bộ nhãn taxonomy và ghi chú từ {len(secondary_ids)} câu trùng vào câu bản gốc [{group.primary_id[:8]}]?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok = self.service.merge_metadata(group.primary_id, secondary_ids)
        if ok:
            QMessageBox.information(
                self, "Gộp thành công",
                f"Đã gộp toàn bộ nhãn taxonomy và metadata từ {len(secondary_ids)} câu vào bản gốc [{group.primary_id[:8]}]."
            )
        else:
            QMessageBox.warning(self, "Lỗi gộp", "Không thể gộp metadata.")

    def _on_delete_clicked(self):
        scope = self.scope_combo.currentData()
        if scope == "database":
            self._delete_selected_database()
        else:
            self._export_cleaned_tex_files()

    def _delete_selected_database(self):
        if self.current_group_idx < 0 or self.current_group_idx >= len(self.groups):
            return
        group = self.groups[self.current_group_idx]
        to_delete = list(group.selected_to_delete)
        if not to_delete:
            QMessageBox.information(
                self, "Chưa chọn câu cần xóa",
                "Vui lòng tick chọn 'Xóa khỏi CSDL' ở các câu hỏi trùng lặp mà bạn muốn xóa khỏi ngân hàng."
            )
            return

        # Check references to inform user
        blocked_refs = [
            f"[{it.id[:8]}]: {', '.join(it.references)}"
            for it in group.items if it.id in to_delete and it.references
        ]
        if blocked_refs:
            msg = (
                "Các câu hỏi sau đang được sử dụng trong bài giảng hoặc đề thi:\n\n"
                + "\n".join(blocked_refs)
                + "\n\nĐể đảm bảo tính toàn vẹn dữ liệu, các câu này sẽ được bảo vệ và không bị xóa."
            )
            QMessageBox.warning(self, "Cảnh báo tài liệu đang tham chiếu", msg)

        confirm = QMessageBox.question(
            self, "Xác nhận xóa vĩnh viễn khỏi CSDL",
            f"Bạn có chắc chắn muốn xóa {len(to_delete)} câu hỏi đã chọn khỏi CSDL ngân hàng câu hỏi?\n\n"
            f"Lưu ý: Thao tác này sẽ xóa dữ liệu vĩnh viễn trong CSDL và không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        count, errors = self.service.delete_selected(to_delete)
        if errors:
            QMessageBox.warning(self, "Thông báo xóa câu hỏi", "\n".join(errors))

        if count > 0:
            QMessageBox.information(
                self, "Xóa hoàn tất",
                f"Đã xóa thành công {count}/{len(to_delete)} câu hỏi khỏi CSDL ngân hàng."
            )
            # Remove deleted from group items
            group.items = [it for it in group.items if it.id not in to_delete]
            group.selected_to_delete.clear()
            if len(group.items) <= 1:
                self._ignore_current_group()
            else:
                self._render_group_cards(group)
            self._update_action_bar_counts()

    def _export_cleaned_tex_files(self):
        items_to_remove = [it for g in self.groups for it in g.items if it.id in g.selected_to_delete]
        if not items_to_remove:
            QMessageBox.information(
                self, "Chưa chọn câu để loại bỏ",
                "Vui lòng tick chọn 'Loại khỏi file .tex' ở các câu hỏi trùng lặp cần loại bỏ trước khi xuất file."
            )
            return

        # Group by file path
        affected_files = sorted(set(it.file_path for it in items_to_remove if it.file_path))
        if not affected_files and self.selected_files:
            affected_files = [str(Path(f).resolve()) for f in self.selected_files]

        output_map: dict[str, Path | str] = {}
        if len(affected_files) == 1:
            src_p = Path(affected_files[0])
            out_str, _ = QFileDialog.getSaveFileName(
                self, "Lưu file .tex đã làm sạch (Save As)", f"cleaned_{src_p.name}",
                "LaTeX File (*.tex)"
            )
            if not out_str:
                return
            output_map[str(src_p)] = out_str
        else:
            dir_str = QFileDialog.getExistingDirectory(
                self, f"Chọn thư mục lưu {len(affected_files)} file .tex mới đã loại bỏ câu trùng"
            )
            if not dir_str:
                return
            for af in affected_files:
                output_map[af] = Path(dir_str) / f"cleaned_{Path(af).name}"

        # Build preview confirmation text
        preview_lines = []
        for af, out_p in output_map.items():
            rem_count = sum(1 for it in items_to_remove if it.file_path == af)
            preview_lines.append(f"• {Path(af).name}: Loại bỏ {rem_count} câu -> Tạo file: {Path(out_p).name}")

        confirm_msg = (
            f"Xác nhận loại bỏ câu trùng và xuất file .tex mới:\n\n"
            + "\n".join(preview_lines) + "\n\n"
            f"Các tệp gốc sẽ được giữ nguyên 100% không bị thay đổi. Bạn có muốn tiếp tục?"
        )
        confirm = QMessageBox.question(
            self, "Xác nhận tạo file .tex đã làm sạch", confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            results = self.service.clean_tex_files(items_to_remove, output_map=output_map)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất file .tex", f"Không thể làm sạch file: {str(e)}")
            return

        # Show success message
        success_lines = [
            f"• {Path(r['output_path']).name} (Còn lại {r['remaining_count']}/{r['original_count']} câu)"
            for r in results.values()
        ]
        QMessageBox.information(
            self, "Xuất file .tex thành công",
            f"Đã tạo thành công {len(results)} file .tex mới đã loại bỏ câu trùng:\n\n"
            + "\n".join(success_lines)
        )

        # Update groups: remove eliminated items
        removed_ids = {it.id for it in items_to_remove}
        for g in self.groups:
            g.items = [it for it in g.items if it.id not in removed_ids]
            g.selected_to_delete.clear()

        # Prune groups with <= 1 item
        self.groups = [g for g in self.groups if len(g.items) > 1]
        self._on_scan_finished(self.groups)

    # Backwards compatibility aliases
    _delete_selected = _on_delete_clicked
    _export_clean_tex = _export_cleaned_tex_files

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
