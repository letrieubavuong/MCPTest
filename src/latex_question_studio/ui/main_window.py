import base64
import json
from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QAction, QKeySequence, QPixmap, QPalette, QColor
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QDockWidget, QTreeWidget, QTreeWidgetItem, QTabWidget, QPlainTextEdit, QTableView,
    QToolBar, QMessageBox, QSplitter, QFileDialog, QProgressBar, QDialog, QInputDialog, QScrollArea, QMenu, QHBoxLayout, QStackedWidget, QListWidget, QLineEdit, QFormLayout, QStyle)
from latex_question_studio.application.services import Services

class QuestionTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 3

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        q = self.rows[index.row()]
        return (q.latex_source.replace("\n", " ")[:100], q.question_type, q.revision)[index.column()]

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return ("Nội dung", "Loại", "Phiên bản")[section]

    def replace_rows(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

class MainWindow(QMainWindow):
    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self.setWindowTitle("LaTeX Question Studio")
        self.resize(1380, 860)
        self.setMinimumSize(800, 500)
        self.editors = {}
        self.theme = services.config.theme
        self.offset = 0
        self.all_jobs = []
        self._menus = {}
        self.preview_generation = 0
        self.preview_job = None
        self.layout_path = services.config.data_dir / "workspace.json"
        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.drawer = QWidget()
        self.drawer.setObjectName("navigationDrawer")
        self.drawer.setFixedWidth(205)
        drawer_layout = QVBoxLayout(self.drawer)
        self.drawer_toggle = QPushButton("☰  Menu")
        self.drawer_toggle.clicked.connect(self.toggle_drawer)
        drawer_layout.addWidget(self.drawer_toggle)
        self.navigation = QListWidget()
        self.navigation.setObjectName("pageNavigation")
        self.navigation.addItems(["CSDL", "Nhập câu hỏi", "Ra đề thi", "Cài đặt", "Bài giảng"])
        for index,icon in enumerate((QStyle.StandardPixmap.SP_DirIcon,QStyle.StandardPixmap.SP_ArrowDown,QStyle.StandardPixmap.SP_FileDialogDetailedView,QStyle.StandardPixmap.SP_FileDialogInfoView,QStyle.StandardPixmap.SP_FileIcon)):
            self.navigation.item(index).setIcon(self.style().standardIcon(icon))
        self.navigation.setSpacing(6)
        drawer_layout.addWidget(self.navigation)
        self.pages = QStackedWidget()
        self.pages.setObjectName("pageContent")
        shell_layout.addWidget(self.drawer)
        shell_layout.addWidget(self.pages, 1)
        self.setCentralWidget(shell)
        self.library_control = QMainWindow()
        self.library_control.setWindowFlags(Qt.WindowType.Widget)
        self.pages.addWidget(self.library_control)
        self.explorer = QTreeWidget()
        self.explorer.setHeaderLabel("THƯ VIỆN")
        self.root_node = QTreeWidgetItem(self.explorer, ["Tất cả câu hỏi"])
        self.explorer.itemClicked.connect(self.taxonomy_selected)
        self.explorer.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.explorer.customContextMenuRequested.connect(self.taxonomy_context)
        self.explorer_dock = self.make_dock("Khám phá", "explorer", self.explorer, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.explorer_dock.setMinimumWidth(200)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.table_model = QuestionTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.table_model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 470)
        self.table.doubleClicked.connect(self.open_row)
        library = QWidget()
        layout = QVBoxLayout(library)
        self.database_status = QLabel()
        layout.addWidget(self.database_status)
        layout.addWidget(self.table)
        self.refresh_button = QPushButton("Kiểm tra cơ sở dữ liệu")
        self.refresh_button.clicked.connect(self.refresh_status)
        layout.addWidget(self.refresh_button)
        self.tabs.addTab(library, "Thư viện")
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)
        self.library_control.setCentralWidget(self.tabs)
        self.preview = QLabel("Chọn một câu hỏi để xem trước.\nF5 — Biên dịch LaTeX")
        self.preview.setWordWrap(True)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.preview.setMinimumWidth(260)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.preview)
        self.preview_dock = self.make_dock("Xem trước", "preview", scroll, Qt.DockWidgetArea.RightDockWidgetArea)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(3000)
        self.log_dock = self.make_dock("Nhật ký / Tác vụ", "logs", self.logs, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.log_dock.setMaximumHeight(240)
        self.build_pages()
        self.csdl_menu = self.menuBar().addMenu("CSDL")
        self.navigation.currentRowChanged.connect(self.show_page)
        self.navigation.setCurrentRow(0)
        self.add_action("Xem CSDL", lambda: self.show_page(0), "Ctrl+1", activity=True)
        self.add_action("Nhập câu hỏi", lambda: self.show_page(1), "Ctrl+I", activity=True)
        self.add_action("Nhập thư mục", self.import_folder)
        self.add_action("Phân loại / Nhãn", self.edit_metadata)
        self.add_action("Thêm mục phân loại", self.add_taxonomy)
        self.add_action("Lịch sử / Khôi phục", self.show_revisions)
        self.add_action("Sao lưu", self.backup_library)
        self.add_action("Phục hồi backup", self.restore_library)
        self.add_action("Hàng chờ nhập", self.show_pending)
        self.add_action("Cài đặt pdfLaTeX", self.compiler_settings, activity=True)
        self.add_action("Biên dịch / Preview", self.compile_current, "F5")
        self.add_action("Hủy biên dịch", self.cancel_preview)
        self.add_action("Trang preview trước",lambda:self.preview_page(-1))
        self.add_action("Trang preview tiếp",lambda:self.preview_page(1))
        self.add_action("Tìm trong câu", self.editor_find, "Ctrl+F")
        self.add_action("Thay thế", self.editor_replace, "Ctrl+H")
        self.add_action("Tìm kiếm thư viện", self.search_library, "Ctrl+Shift+F", activity=True)
        self.add_action("Bộ lọc", self.filter_library)
        self.add_action("Xóa tìm kiếm / bộ lọc", self.clear_search)
        self.add_action("Tìm câu trùng", self.find_duplicates)
        self.add_action("Tạo đề", self.create_exam, activity=True)
        self.add_action("Lịch sử đề", self.exam_history)
        self.add_action("Lưu trữ câu hỏi", self.archive_question)
        self.add_action("Khôi phục câu lưu trữ",self.restore_archived)
        self.add_action("Câu hỏi mới", self.new_question, "Ctrl+N")
        self.add_action("Lưu câu hỏi", self.save_current, "Ctrl+S")
        self.add_action("Đóng tab", lambda: self.close_tab(self.tabs.currentIndex()), "Ctrl+W")
        self.add_action("Trang trước", self.previous_page, "Alt+Left")
        self.add_action("Trang tiếp", self.next_page, "Alt+Right")
        self.add_action("Đổi giao diện", self.toggle_theme, "Ctrl+Shift+T", activity=True)
        view = self.menuBar().addMenu("Hiển thị")
        for dock in (self.explorer_dock, self.preview_dock, self.log_dock):
            view.addAction(dock.toggleViewAction())
        self.restore_workspace()
        self.apply_theme()
        self.refresh_status()

    def build_pages(self):
        self.import_page = QWidget()
        self.import_page.setObjectName("importPage")
        layout = QVBoxLayout(self.import_page)
        layout.addWidget(QLabel("NHẬP CÂU HỎI"))
        buttons = QHBoxLayout()
        for text, callback in (("Chọn file TeX", self.import_files), ("Chọn thư mục", self.import_folder), ("Hàng chờ / Sửa lỗi", self.show_pending)):
            button = QPushButton(text); button.clicked.connect(callback); buttons.addWidget(button)
        layout.addLayout(buttons)
        self.import_status = QLabel("Chọn file hoặc thư mục LaTeX để xem trước, rồi xác nhận nhập.")
        self.import_status.setWordWrap(True)
        layout.addWidget(self.import_status)
        self.import_progress = QProgressBar(); self.import_progress.setValue(0)
        layout.addWidget(self.import_progress)
        self.import_cancel = QPushButton("Hủy phân tích")
        self.import_cancel.setEnabled(False)
        self.import_cancel.clicked.connect(lambda: self.import_job.cancelled.set() if getattr(self, 'import_job', None) else None)
        layout.addWidget(self.import_cancel)
        self.import_content = QVBoxLayout()
        layout.addLayout(self.import_content, 1)
        self.pages.addWidget(self.import_page)
        from latex_question_studio.ui.exam_dialog import ExamDialog
        self.exam_page = ExamDialog([], self.pages)
        self.exam_page.setObjectName("examPage")
        self.exam_page.submitted.connect(self.generate_exam)
        self.exam_page.use_selection.connect(self.use_exam_selection)
        self.exam_status = QLabel("Chọn câu trong Xem CSDL rồi lấy vào đề, hoặc thêm hàng ma trận.")
        self.exam_status.setWordWrap(True)
        self.exam_page.layout().addWidget(self.exam_status)
        self.exam_export = QPushButton("Xuất đề / Đáp án / Lời giải")
        self.exam_export.setEnabled(False)
        self.exam_export.clicked.connect(lambda: self.export_exam(self.exam_snapshot))
        self.exam_page.layout().addWidget(self.exam_export)
        self.pages.addWidget(self.exam_page)
        self.settings_page = QWidget()
        layout = QVBoxLayout(self.settings_page); layout.addWidget(QLabel("CÀI ĐẶT"))
        form = QFormLayout(); config = self.compiler_config()
        self.engine_input = QLineEdit(config.get('engine', 'pdflatex'))
        self.preamble_input = QLineEdit(config.get('preamble_file', ''))
        form.addRow("Đường dẫn pdfLaTeX", self.engine_input)
        form.addRow("File preamble riêng", self.preamble_input)
        layout.addLayout(form)
        button = QPushButton("Lưu cấu hình"); button.clicked.connect(self.save_compiler_settings); layout.addWidget(button)
        button = QPushButton("Đổi giao diện sáng / tối"); button.clicked.connect(self.toggle_theme); layout.addWidget(button)
        self.settings_status = QLabel(); layout.addWidget(self.settings_status); layout.addStretch()
        self.pages.addWidget(self.settings_page)
        from latex_question_studio.ui.lesson_page import LessonPage
        self.lesson_page = LessonPage(self.services, self.start_job, self.compiler_config, self.pages)
        self.pages.addWidget(self.lesson_page)

    def show_page(self, index):
        if not 0 <= index < self.pages.count(): return
        self.pages.setCurrentIndex(index)
        if self.navigation.currentRow() != index: self.navigation.setCurrentRow(index)

    def toggle_drawer(self):
        collapsed = self.drawer.width() > 100
        self.drawer.setFixedWidth(64 if collapsed else 205)
        labels = ["CSDL", "Nhập", "Đề thi", "Cài đặt", "Bài"] if collapsed else ["CSDL", "Nhập câu hỏi", "Ra đề thi", "Cài đặt", "Bài giảng"]
        for i, text in enumerate(labels): self.navigation.item(i).setText(text)
        self.drawer_toggle.setText("☰" if collapsed else "☰  Menu")

    def make_dock(self, title, name, widget, area):
        dock = QDockWidget(title, self.library_control)
        dock.setObjectName(name)
        dock.setWidget(widget)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.library_control.addDockWidget(area, dock)
        return dock

    def add_action(self, title, callback, shortcut=None, activity=False):
        action = QAction(title, self)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        self.addAction(action)
        if activity:
            pass  # Drawer owns page navigation.
        else:
            group = "Thư viện"
            if title in ("Câu hỏi mới","Lưu câu hỏi","Đóng tab","Sao lưu","Phục hồi backup","Nhập thư mục","Hàng chờ nhập"):group="Tệp"
            elif title in ("Tìm trong câu","Thay thế"):group="Biên tập"
            elif title in ("Biên dịch / Preview","Hủy biên dịch"):group="LaTeX"
            elif title in ("Lịch sử đề",):group="Đề thi"
            if group not in self._menus:self._menus[group]=self.menuBar().addMenu(group)
            self._menus[group].addAction(action)
        return action

    def refresh_status(self):
        try:
            count = self.filtered_count()
            self.table_model.replace_rows(self.library_page())
            self.refresh_taxonomy()
            self.database_status.setText(f"Cơ sở dữ liệu đã sẵn sàng • {count} câu hỏi • Trang {self.offset // 100 + 1}")
            from latex_question_studio.application.search import SearchService
            total=SearchService(self.services).find(count_only=True)
            self.root_node.setText(0, f"Tất cả câu hỏi ({total})")
            selected=self.taxonomy_items.get(getattr(self,'selected_taxonomy',None))
            if selected:
                self.database_status.setText(f"{selected.text(0)} • {count} câu phù hợp • Trang {self.offset // 100 + 1}")
            self.statusBar().showMessage(f"Sẵn sàng • SQLite • {count} câu hỏi")
        except Exception:
            self.database_status.setText("Không thể đọc cơ sở dữ liệu. Xem nhật ký ứng dụng.")
            self.logs.appendPlainText("Không thể đọc cơ sở dữ liệu.")

    def next_page(self):
        if self.offset + 100 < self.filtered_count():
            self.offset += 100
            self.refresh_status()

    def previous_page(self):
        self.offset = max(0, self.offset - 100)
        self.refresh_status()

    def open_row(self, index):
        self.open_question(self.table_model.rows[index.row()].id)

    def open_question(self, question_id):
        for editor, question in self.editors.items():
            if question.id == question_id:
                self.show_page(0)
                self.tabs.setCurrentWidget(editor)
                return editor
        self.show_page(0)
        question = self.services.questions.get(question_id)
        if question is None:
            return None
        from latex_question_studio.ui.editor import LatexEditor
        editor = LatexEditor()
        editor.setPlainText(question.latex_source)
        editor.document().setModified(False)
        self.editors[editor] = question
        self.tabs.addTab(editor, question.id[:8])
        editor.document().modificationChanged.connect(lambda modified, e=editor: self.dirty_changed(e, modified))
        self.tabs.setCurrentWidget(editor)
        return editor

    def new_question(self):
        if self.pages.currentIndex()==4:
            self.lesson_page.new_lesson();return
        q = self.services.questions.create("\\begin{ex}\nNội dung câu hỏi\n\\loigiai{}\n\\end{ex}\n")
        if getattr(self,'selected_taxonomy',None):
            from latex_question_studio.application.library import LibraryService
            LibraryService(self.services).save_metadata(q.id,{'taxonomy_id':self.selected_taxonomy})
        self.refresh_status()
        self.open_question(q.id)

    def dirty_changed(self, editor, modified):
        index = self.tabs.indexOf(editor)
        if index >= 0:
            self.tabs.setTabText(index, self.editors[editor].id[:8] + (" *" if modified else ""))

    def save_current(self):
        if self.pages.currentIndex()==4:return self.lesson_page.save()
        return self.save_question_editor()

    def save_question_editor(self):
        editor = self.tabs.currentWidget()
        if editor not in self.editors:
            return True
        if not editor.document().isModified():return True
        try:
            from latex_question_studio.parsing.latex import parse_questions
            parsed = parse_questions(editor.toPlainText())
            if len(parsed)!=1 or parsed[0].diagnostics:
                if QMessageBox.question(self,"Cấu trúc chưa hợp lệ","Giữ nguyên source và lưu dưới dạng chưa phân tích? Chi tiết lỗi sẽ xuất hiện trong log.")!=QMessageBox.StandardButton.Yes:return False
                self.logs.appendPlainText("; ".join(d.message for item in parsed for d in item.diagnostics))
                q = self.services.questions.update(replace(self.editors[editor],latex_source=editor.toPlainText(),question_type="unknown"))
            else:
                q = self.services.questions.update(replace(self.editors[editor],latex_source=editor.toPlainText(),question_type=parsed[0].question_type,solution=parsed[0].solution))
            self.editors[editor] = q
            editor.document().setModified(False)
            self.refresh_status()
            return True
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))
            return False

    def close_tab(self, index):
        editor = self.tabs.widget(index)
        if editor not in self.editors:
            return False
        if editor.document().isModified():
            answer = QMessageBox.question(self, "Chưa lưu", "Lưu thay đổi trước khi đóng?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if answer == QMessageBox.StandardButton.Cancel:
                return False
            if answer == QMessageBox.StandardButton.Save:
                self.tabs.setCurrentWidget(editor)
                if not self.save_question_editor():
                    return False
        del self.editors[editor]
        self.tabs.removeTab(index)
        editor.deleteLater()
        return True

    def tab_changed(self, index):
        if not hasattr(self,'preview'):return
        editor = self.tabs.widget(index)
        if editor not in self.editors:
            self.cancel_preview();self.preview_generation+=1
            self.preview.setPixmap(QPixmap());self.preview.setMinimumSize(260,0);self.preview.setText('Chọn một câu để xem trước.')
            return
        if editor in self.editors:
            q = self.editors[editor]
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Đang chuẩn bị preview…")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100,self.compile_current)

    def apply_theme(self):
        dark = self.theme == "dark"
        bg, fg, panel = ("#1e1e1e", "#dedede", "#252526") if dark else ("#ffffff", "#202020", "#eeeeee")
        from PySide6.QtWidgets import QApplication
        palette=QPalette()
        for role,color in ((QPalette.ColorRole.Window,bg),(QPalette.ColorRole.Base,bg),(QPalette.ColorRole.AlternateBase,panel),(QPalette.ColorRole.Text,fg),(QPalette.ColorRole.WindowText,fg),(QPalette.ColorRole.Button,panel),(QPalette.ColorRole.ButtonText,fg),(QPalette.ColorRole.Highlight,'#007acc'),(QPalette.ColorRole.HighlightedText,'#ffffff')):palette.setColor(role,QColor(color))
        QApplication.instance().setPalette(palette)
        from latex_question_studio.ui.icons import icon
        for i,name in enumerate(('bank','import','exam','settings','lesson')):
            self.navigation.item(i).setIcon(icon(name,fg))
        for button in self.findChildren(QPushButton):
            if button.text() in ('Ghi các câu hợp lệ vào ngân hàng','Tạo đề','Xuất bộ TeX + PDF'):button.setProperty('primary',True)
            if button.property('iconName'):button.setIcon(icon(button.property('iconName'),'#ffffff' if button.property('primary') else fg))
        self.setStyleSheet(f"QWidget {{background:{bg};color:{fg};font-family:'Segoe UI';font-size:13px;}} QPlainTextEdit {{background:{bg};color:{fg};font-family:'Consolas';font-size:15px;selection-background-color:#264f78;}} QTabBar::tab {{background:{panel};color:{fg};padding:7px;}} QTabBar::tab:selected {{background:{bg};border-top:2px solid #007acc;}} QToolBar,QDockWidget,QHeaderView::section {{background:{panel};}} QPushButton {{padding:7px;background:{panel};color:{fg};border:1px solid #666;border-radius:4px;}} QPushButton[primary='true'] {{background:#007acc;color:white;border:1px solid #007acc;}} QStatusBar {{background:#007acc;color:white;}} QTableView {{alternate-background-color:{panel};}} QListWidget::item {{padding:10px 5px;}} QListWidget::item:selected {{background:#007acc;color:white;}} QPushButton:disabled {{background:{panel};color:#888888;}}")

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        replace(self.services.config, theme=self.theme).save()
        self.apply_theme()

    def restore_workspace(self):
        if not self.layout_path.exists():
            return
        try:
            state = json.loads(self.layout_path.read_text(encoding="utf-8"))
            if state.get("version") not in (1, 2):
                return
            self.selected_taxonomy=state.get("taxonomy_id")
            self.restored_taxonomy_expanded=state.get("taxonomy_expanded",[])
            self.restoreGeometry(base64.b64decode(state["geometry"]))
            if state.get("version") == 2:
                self.library_control.restoreState(base64.b64decode(state["layout"]))
            for question_id in state.get("tabs", [])[:30]:
                self.open_question(question_id)
            if state.get("lesson_id"):
                lesson=self.lesson_page.service.get(state['lesson_id'])
                if lesson:
                    self.lesson_page.reload_list(lesson['id']);self.lesson_page.load(lesson)
            self.show_page(state.get("page", 0))
            if state.get("drawer_collapsed", False): self.toggle_drawer()
        except (ValueError, KeyError, TypeError):
            self.logs.appendPlainText("Không thể khôi phục layout; dùng mặc định.")

    def save_workspace(self):
        from PySide6.QtWidgets import QTreeWidgetItemIterator
        expanded=[];iterator=QTreeWidgetItemIterator(self.explorer)
        while iterator.value():
            item=iterator.value()
            if item.isExpanded() and item.data(0,Qt.ItemDataRole.UserRole):expanded.append(item.data(0,Qt.ItemDataRole.UserRole))
            iterator+=1
        state = {"version": 2, "taxonomy_id":getattr(self,'selected_taxonomy',None),"taxonomy_expanded":expanded, "page": self.pages.currentIndex(), "drawer_collapsed": self.drawer.width() < 100, "lesson_id": self.lesson_page.doc["id"] if self.lesson_page.doc else None, "geometry": base64.b64encode(bytes(self.saveGeometry())).decode(),
                 "layout": base64.b64encode(bytes(self.library_control.saveState())).decode(), "tabs": [q.id for q in self.editors.values()]}
        temp = self.layout_path.with_suffix(".tmp")
        temp.write_text(json.dumps(state), encoding="utf-8")
        temp.replace(self.layout_path)

    def closeEvent(self, event):
        if not self.lesson_page.save():
            event.ignore();return
        self.lesson_page.cancel_preview()
        open_ids = [q.id for q in self.editors.values()]
        # Resolve every dirty document before changing any tab or persisted workspace.
        for editor in list(self.editors):
            if editor.document().isModified():
                self.tabs.setCurrentWidget(editor)
                answer = QMessageBox.question(self, "Chưa lưu", "Lưu thay đổi trước khi thoát?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
                if answer == QMessageBox.StandardButton.Cancel or (answer == QMessageBox.StandardButton.Save and not self.save_question_editor()):
                    event.ignore()
                    return
        try:
            self.save_workspace()
        except OSError:
            self.logs.appendPlainText("Không thể lưu layout.")
        for job in self.all_jobs:job.cancelled.set()
        from PySide6.QtCore import QThreadPool
        if not QThreadPool.globalInstance().waitForDone(5000):
            self.logs.appendPlainText("Tác vụ đang dừng; hãy thử đóng lại sau giây lát.")
            event.ignore();return
        event.accept()

    def import_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Nhập LaTeX", "", "LaTeX (*.tex)")
        if paths: self.start_import(paths)

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Nhập thư mục LaTeX")
        if folder: self.start_import(list(Path(folder).rglob("*.tex")))

    def start_import(self, paths):
        from PySide6.QtCore import QThreadPool
        from latex_question_studio.ui.jobs import Job
        from latex_question_studio.application.importing import ImportService
        if getattr(self, "import_job", None) or getattr(self, "commit_job", None): return
        importer = ImportService(self.services)
        self.import_job = Job(lambda cancelled, progress: importer.stage(paths,cancelled,progress))
        self.show_page(1)
        self.import_progress.setRange(0, len(paths))
        self.import_progress.setValue(0)
        self.import_status.setText("Đang phân tích LaTeX…")
        self.import_cancel.setEnabled(True)
        self.import_job.signals.progress.connect(lambda done,total:self.import_progress.setValue(done))
        self.import_job.signals.completed.connect(self.import_ready)
        self.import_job.signals.failed.connect(self.import_failed)
        self.start_job(self.import_job)

    def import_failed(self, error):
        self.import_job = None
        self.import_cancel.setEnabled(False)
        self.import_status.setText("Nhập dữ liệu đã dừng: " + error)
        self.logs.appendPlainText("Nhập dữ liệu đã dừng: " + error)

    def import_ready(self, result):
        from latex_question_studio.ui.import_dialog import ImportReview
        self.import_job = None
        self.import_cancel.setEnabled(False)
        batch, results = result
        self.import_status.setText(f"Đã phân tích {len(results)} mục. Xem và xác nhận bên dưới.")
        review = ImportReview(results, self.import_page)
        review.accepted.connect(lambda: self.commit_import(batch, review))
        review.rejected.connect(lambda: self.import_status.setText("Đã giữ batch trong hàng chờ."))
        self.replace_import_content(review)

    def commit_import(self, batch, review):
        from latex_question_studio.application.importing import ImportService
        from latex_question_studio.ui.jobs import Job
        if getattr(self, 'commit_job', None): return
        review.setEnabled(False)
        job = Job(lambda cancelled,progress:ImportService(self.services).commit(batch))
        self.commit_job = job
        job.signals.completed.connect(self.commit_ready)
        def failed(error):
            self.commit_job = None
            review.setEnabled(True)
            self.import_status.setText('Ghi batch lỗi: ' + error)
        job.signals.failed.connect(failed)
        self.start_job(job)

    def replace_import_content(self, widget):
        while self.import_content.count():
            item = self.import_content.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.import_content.addWidget(widget)
        self.import_review = widget

    def show_pending(self):
        from latex_question_studio.ui.pending_dialog import PendingDialog
        if getattr(self, 'commit_job', None): return
        self.show_page(1)
        pending = PendingDialog(self.services, self.import_page)
        pending.committed.connect(self.refresh_status)
        self.replace_import_content(pending)

    def library_page(self):
        from latex_question_studio.application.search import SearchService
        return SearchService(self.services).find(getattr(self,"search_text",""),getattr(self,"search_filters",{}),offset=self.offset,taxonomy_id=getattr(self,"selected_taxonomy",None))

    def refresh_taxonomy(self):
        from latex_question_studio.application.library import LibraryService
        from latex_question_studio.domain.curriculum import ROOT_ID
        from PySide6.QtWidgets import QTreeWidgetItemIterator
        expanded=set();iterator=QTreeWidgetItemIterator(self.explorer)
        while iterator.value():
            item=iterator.value()
            if item.isExpanded():expanded.add(item.data(0,Qt.ItemDataRole.UserRole))
            iterator+=1
        if not getattr(self,'taxonomy_built',False):
            expanded=set(getattr(self,'restored_taxonomy_expanded',[ROOT_ID]))
        self.root_node.takeChildren()
        nodes=LibraryService(self.services).taxonomy()
        items={n['id']:QTreeWidgetItem([f"{n['name']} ({n['count']})"]) for n in nodes}
        for n in nodes:
            item=items[n['id']];item.setData(0,Qt.ItemDataRole.UserRole,n['id']);item.setToolTip(0,n['name'])
            items.get(n['parent_id'],self.root_node).addChild(item)
            item.setExpanded(n['id'] in expanded)
        self.taxonomy_items=items;self.taxonomy_built=True
        self.root_node.setExpanded(True)
        selected=items.get(getattr(self,'selected_taxonomy',None))
        if selected:
            self.explorer.setCurrentItem(selected)
            ancestor=selected.parent()
            while ancestor:ancestor.setExpanded(True);ancestor=ancestor.parent()
        self.refresh_curriculum_menu(nodes)

    def refresh_curriculum_menu(self,nodes):
        from latex_question_studio.domain.curriculum import ROOT_ID,MATH_ROOT_ID,KHTN7_ROOT_ID,MATH7_ROOT_ID,KHTN8_ROOT_ID,MATH8_ROOT_ID,KHTN9_ROOT_ID,MATH9_ROOT_ID
        key=tuple((n['id'],n['parent_id'],n['name']) for n in nodes)
        if getattr(self,'curriculum_menu_key',None)==key:return
        self.curriculum_menu_key=key;self.csdl_menu.clear();self.curriculum_submenus=[]
        self.csdl_menu.addAction('Tất cả câu hỏi',lambda:self.open_taxonomy(None))
        for root_id,attribute in ((ROOT_ID,'khtn6_menu'),(MATH_ROOT_ID,'math6_menu'),(KHTN7_ROOT_ID,'khtn7_menu'),(MATH7_ROOT_ID,'math7_menu'),(KHTN8_ROOT_ID,'khtn8_menu'),(MATH8_ROOT_ID,'math8_menu'),(KHTN9_ROOT_ID,'khtn9_menu'),(MATH9_ROOT_ID,'math9_menu'),('curriculum:math10','math10_menu'),('curriculum:physics10','physics10_menu'),('curriculum:math11','math11_menu')):
            root=next((n for n in nodes if n['id']==root_id),None)
            if not root:continue
            menu=QMenu(root['name'],self.csdl_menu);self.csdl_menu.addMenu(menu);setattr(self,attribute,menu)
            self.curriculum_submenus.append(menu)
            action=menu.addAction('Tất cả '+root['name'],lambda checked=False,key=root_id:self.open_taxonomy(key));action.setData(root_id)
            menu.addSeparator()
            for chapter in (n for n in nodes if n['parent_id']==root_id):
                if chapter['kind']=='lesson':
                    action=menu.addAction(chapter['name'],lambda checked=False,key=chapter['id']:self.open_taxonomy(key));action.setData(chapter['id'])
                    continue
                submenu=QMenu(chapter['name'],menu);menu.addMenu(submenu);self.curriculum_submenus.append(submenu)
                action=submenu.addAction('Tất cả câu trong chương',lambda checked=False,key=chapter['id']:self.open_taxonomy(key));action.setData(chapter['id'])
                submenu.addSeparator()
                for lesson in (n for n in nodes if n['parent_id']==chapter['id']):
                    action=submenu.addAction(lesson['name'],lambda checked=False,key=lesson['id']:self.open_taxonomy(key));action.setData(lesson['id'])

    def open_taxonomy(self,taxonomy_id):
        self.show_page(0);self.tabs.setCurrentIndex(0)
        self.selected_taxonomy=taxonomy_id;self.search_text='';self.search_filters={};self.offset=0
        self.refresh_status()
        item=self.taxonomy_items.get(taxonomy_id,self.root_node)
        self.explorer.setCurrentItem(item);item.setExpanded(True);self.explorer.scrollToItem(item)

    def taxonomy_selected(self,item,*args):
        self.selected_taxonomy=item.data(0,Qt.ItemDataRole.UserRole)
        self.offset=0;self.refresh_status()

    def edit_metadata(self):
        from latex_question_studio.application.library import LibraryService
        from latex_question_studio.ui.metadata_dialog import MetadataDialog
        editor=self.tabs.currentWidget()
        if editor not in self.editors:return
        if not self.save_question_editor():return
        q=self.editors[editor];library=LibraryService(self.services)
        dialog=MetadataDialog({**library.metadata(q.id),"question_type":q.question_type,"difficulty_legacy":q.difficulty_legacy,"cognitive_level":q.cognitive_level},library.taxonomy(),self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            library.save_metadata(q.id,dialog.values())
            self.editors[editor]=self.services.questions.get(q.id)
            self.refresh_status()

    def add_taxonomy(self):
        from latex_question_studio.application.library import LibraryService
        name,ok=QInputDialog.getText(self,"Thêm phân loại","Tên mục con của mục đang chọn:")
        if not ok:return
        kind,ok=QInputDialog.getItem(self,"Loại phân loại","Cấp:",["subject","grade","chapter","lesson","topic","category"],0,False)
        if ok:
            try:LibraryService(self.services).add_taxonomy(name,kind,getattr(self,"selected_taxonomy",None));self.refresh_status()
            except Exception as error:QMessageBox.warning(self,"Không thể thêm",str(error))

    def show_revisions(self):
        from latex_question_studio.application.library import LibraryService
        editor=self.tabs.currentWidget()
        if editor not in self.editors:return
        if editor.document().isModified() and not self.save_question_editor():return
        q=self.editors[editor];library=LibraryService(self.services);revisions=library.revisions(q.id)
        labels=[f"Phiên bản {r['revision']} • {r['created_at']}" for r in revisions]
        label,ok=QInputDialog.getItem(self,"Khôi phục phiên bản","Chọn phiên bản để phục hồi (tạo bản mới):",labels,0,False)
        if ok and QMessageBox.question(self,"Khôi phục","Phục hồi nội dung phiên bản đã chọn?")==QMessageBox.StandardButton.Yes:
            restored=library.restore_revision(q.id,revisions[labels.index(label)]['revision'])
            self.editors[editor]=restored;editor.setPlainText(restored.latex_source);editor.document().setModified(False);self.refresh_status()

    def backup_library(self):
        from latex_question_studio.application.library import LibraryService
        if self.all_jobs:
            QMessageBox.information(self,'Đang có tác vụ','Đợi tác vụ hoàn tất trước khi sao lưu.');return
        path,_=QFileDialog.getSaveFileName(self,"Sao lưu thư viện","studio-backup.zip","Backup (*.zip)")
        if path:
            if not self.lesson_page.save():return
            try:LibraryService(self.services).backup(path);self.logs.appendPlainText("Đã sao lưu DB, nguồn và tài nguyên.")
            except Exception as error:QMessageBox.warning(self,"Backup lỗi",str(error))

    def restore_library(self):
        from latex_question_studio.application.library import LibraryService
        if self.all_jobs:
            QMessageBox.information(self,"Đang có tác vụ","Đợi tác vụ hoàn tất trước khi phục hồi.");return
        path,_=QFileDialog.getOpenFileName(self,"Phục hồi thư viện","","Backup (*.zip)")
        if not path:return
        if QMessageBox.question(self,"Phục hồi","Thay thư viện hiện tại bằng backup? Một bản DB trước phục hồi sẽ được giữ lại.")!=QMessageBox.StandardButton.Yes:return
        if not self.lesson_page.save():return
        for editor in list(self.editors):
            if not self.close_tab(self.tabs.indexOf(editor)):return
        try:
            LibraryService(self.services).restore_backup(path);self.refresh_status();self.lesson_page.reset_after_restore();self.logs.appendPlainText("Đã phục hồi thư viện; DB trước đó được lưu ở backups.")
        except Exception as error:QMessageBox.warning(self,"Phục hồi lỗi",str(error))

    def editor_find(self):
        if self.pages.currentIndex()==4:
            self.lesson_page.editor.find_text();return
        editor=self.tabs.currentWidget()
        if editor in self.editors:editor.find_text()

    def editor_replace(self):
        if self.pages.currentIndex()==4:
            self.lesson_page.editor.replace_text();return
        editor=self.tabs.currentWidget()
        if editor in self.editors:editor.replace_text()

    def compiler_config(self):
        path=self.services.config.data_dir/"compiler.json"
        try:return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except ValueError:return {}

    def compiler_settings(self):
        self.show_page(3)

    def save_compiler_settings(self):
        path=self.services.config.data_dir/"compiler.json";temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps({'engine':self.engine_input.text().strip() or 'pdflatex','preamble_file':self.preamble_input.text().strip()},ensure_ascii=False),encoding='utf-8');temp.replace(path)
        self.settings_status.setText("Đã lưu cấu hình pdfLaTeX.")

    def cancel_preview(self):
        if self.preview_job:self.preview_job.cancelled.set()

    def compile_current(self):
        if self.pages.currentIndex()==4:
            self.lesson_page.start_preview();return
        from PySide6.QtCore import QThreadPool
        from latex_question_studio.ui.jobs import Job
        from latex_question_studio.preview.compiler import Compiler
        editor=self.tabs.currentWidget()
        if editor not in self.editors:return
        self.cancel_preview();self.preview_generation+=1;generation=self.preview_generation
        q=self.editors[editor];source=editor.toPlainText()
        config=self.compiler_config()
        compiler=Compiler(self.services.config.data_dir,engine=config.get('engine','pdflatex'),preamble_file=config.get('preamble_file') or None)
        with self.services.database.connect() as c:
            assets={r['original_reference']:self.services.config.data_dir/r['relative_path'] for r in c.execute('SELECT qa.original_reference,a.relative_path FROM question_assets qa JOIN assets a ON a.id=qa.asset_id WHERE qa.question_id=?',(q.id,))}
        def work(cancelled,progress):
            result=compiler.compile(source,assets,cancelled)
            image,pages=(Compiler.render(result.pdf) if result.ok else (None,0))
            return generation,q.id,source,result,image,pages,0
        job=Job(work);self.preview_job=job
        job.signals.completed.connect(self.preview_ready)
        job.signals.failed.connect(lambda error:self.logs.appendPlainText('Preview lỗi: '+error))
        self.start_job(job)
        self.statusBar().showMessage("Đang biên dịch câu được chọn…")

    def preview_ready(self,payload):
        generation,question_id,source,result,image,pages,page=payload
        editor=self.tabs.currentWidget()
        if generation!=self.preview_generation or editor not in self.editors or self.editors[editor].id!=question_id or editor.toPlainText()!=source:return
        self.preview_job=None
        self.preview_info=(question_id,source,result,pages,page)
        self.logs.setPlainText(result.log)
        if result.ok:
            pixmap=QPixmap();pixmap.loadFromData(image)
            width=max(240,self.preview_dock.width()-35)
            scaled=pixmap.scaledToWidth(min(max(width,560),pixmap.width()),Qt.TransformationMode.SmoothTransformation)
            self.preview.setText('');self.preview.setMinimumSize(scaled.size());self.preview.setPixmap(scaled)
            self.statusBar().showMessage(f"Preview • Trang {page+1}/{pages} • "+("Cache" if result.cache_hit else "Biên dịch mới"))
        else:
            self.preview.setPixmap(QPixmap());self.preview.setText("Không thể tạo preview. Xem Nhật ký / Tác vụ.")
            self.statusBar().showMessage("Preview đã hủy" if result.cancelled else "Preview lỗi")

    def search_library(self):
        text,ok=QInputDialog.getText(self,"Tìm kiếm thư viện","Nội dung hoặc metadata (hỗ trợ tiếng Việt không dấu):",text=getattr(self,"search_text",""))
        if ok:self.search_text=text;self.offset=0;self.show_page(0);self.tabs.setCurrentIndex(0);self.refresh_status()

    def clear_search(self):
        self.search_text='';self.search_filters={};self.selected_taxonomy=None;self.offset=0;self.refresh_status()

    def filter_library(self):
        from latex_question_studio.ui.metadata_dialog import MetadataDialog
        dialog=MetadataDialog(getattr(self,"search_filters",{}),[],self)
        dialog.setWindowTitle("Bộ lọc — trường rỗng không giới hạn")
        if dialog.exec()==QDialog.DialogCode.Accepted:
            values=dialog.values();values['tag']=next(iter(values.pop('tags',[])),'')
            self.search_filters=values;self.offset=0;self.show_page(0);self.tabs.setCurrentIndex(0);self.refresh_status()

    def find_duplicates(self):
        from PySide6.QtCore import QThreadPool
        from latex_question_studio.ui.jobs import Job
        from latex_question_studio.application.search import SearchService
        editor=self.tabs.currentWidget()
        if editor not in self.editors:return
        question_id=self.editors[editor].id
        job=Job(lambda cancelled,progress:(question_id,SearchService(self.services).duplicates(question_id,cancelled=cancelled)))
        self.duplicate_job=job
        job.signals.completed.connect(self.duplicates_ready)
        job.signals.failed.connect(lambda error:self.logs.appendPlainText(error))
        self.start_job(job)
        self.logs.appendPlainText("Đang tìm trùng/gần trùng…")

    def duplicates_ready(self,result):
        from latex_question_studio.application.search import SearchService
        question_id,duplicates=result
        self.duplicate_job=None
        if not duplicates:self.logs.appendPlainText("Không có gợi ý trùng.");return
        labels=[f"{'Trùng' if r['exact'] else 'Gần trùng'} {r['score']:.0%} • {r['id'][:8]} • {r['source'][:80]}" for r in duplicates]
        label,ok=QInputDialog.getItem(self,"Gợi ý trùng","Chọn câu để xem (không tự xóa):",labels,0,False)
        if not ok:return
        candidate=duplicates[labels.index(label)];self.open_question(candidate['id'])
        answer=QMessageBox.question(self,"Hợp nhất có xác nhận","Giữ câu đang tìm làm chính và lưu trữ câu vừa xem? Source/đáp án/revision câu phụ vẫn được giữ. Chọn No để giữ cả hai.")
        if answer==QMessageBox.StandardButton.Yes:
            SearchService(self.services).merge(question_id,candidate['id']);self.refresh_status()

    def selected_exam_ids(self):
        editor = self.tabs.currentWidget()
        return ([self.editors[editor].id] if editor in self.editors else
                [self.table_model.rows[i.row()].id for i in self.table.selectionModel().selectedRows()])

    def create_exam(self):
        self.show_page(2)

    def use_exam_selection(self):
        self.exam_page.set_manual_ids(self.selected_exam_ids())

    def generate_exam(self):
        from latex_question_studio.application.exams import ExamService
        try:
            version,snapshot=ExamService(self.services).generate(**self.exam_page.values())
            self.exam_snapshot = snapshot
            self.exam_status.setText(f"Đã tạo đề {version[:8]} gồm {len(snapshot['questions'])} câu. Có thể xuất đề bên dưới.")
            self.exam_export.setEnabled(True)
            self.logs.appendPlainText(self.exam_status.text())
        except Exception as error:
            self.exam_status.setText("Không thể tạo đề: " + str(error))

    def exam_history(self):
        from latex_question_studio.application.exams import ExamService
        history=ExamService(self.services).history()
        if not history:self.logs.appendPlainText('Chưa có lịch sử đề.');return
        labels=[r['title']+' • '+r['created_at'] for r in history]
        label,ok=QInputDialog.getItem(self,"Lịch sử đề","Chọn đề để xuất lại:",labels,0,False)
        if ok:self.export_exam(json.loads(history[labels.index(label)]['snapshot_json']))

    def export_exam(self,snapshot):
        from PySide6.QtCore import QThreadPool
        from latex_question_studio.application.exams import ExamService
        from latex_question_studio.ui.jobs import Job
        mode,ok=QInputDialog.getItem(self,"Xuất đề","Nội dung:",["Đề học sinh","Đề kèm lời giải","Đáp án"],0,False)
        if not ok:return
        path,selected=QFileDialog.getSaveFileName(self,"Xuất đề","de-kiem-tra.tex","LaTeX (*.tex);;PDF (*.pdf)")
        if not path:return
        service=ExamService(self.services);solutions=mode=='Đề kèm lời giải';answer_only=mode=='Đáp án';config=self.compiler_config()
        if path.lower().endswith('.pdf'):
            job=Job(lambda cancelled,progress:service.export_pdf(snapshot,path,solutions,answer_only,engine=config.get('engine','pdflatex'),preamble_file=config.get('preamble_file') or None,cancelled=cancelled))
            self.export_job=job
            job.signals.completed.connect(self.exam_export_ready)
            job.signals.failed.connect(lambda error:self.logs.appendPlainText('Xuất PDF lỗi: '+error))
            self.start_job(job);self.logs.appendPlainText('Đang xuất PDF nền…')
        else:
            preamble=Path(config['preamble_file']).read_text(encoding='utf-8-sig') if config.get('preamble_file') else None
            service.export_tex(snapshot,path,solutions,answer_only,preamble=preamble);self.logs.appendPlainText('Đã xuất TeX cùng tài nguyên.')

    def exam_export_ready(self,result):
        self.export_job=None;self.logs.setPlainText(('Đã xuất PDF.\n' if result.ok else 'Xuất PDF lỗi.\n')+result.log)

    def filtered_count(self):
        from latex_question_studio.application.search import SearchService
        return SearchService(self.services).find(getattr(self,"search_text",""),getattr(self,"search_filters",{}),taxonomy_id=getattr(self,"selected_taxonomy",None),count_only=True)

    def start_job(self,job):
        from PySide6.QtCore import QThreadPool
        self.all_jobs.append(job)
        job.signals.completed.connect(lambda *_:self.finish_job(job))
        job.signals.failed.connect(lambda *_:self.finish_job(job))
        QThreadPool.globalInstance().setMaxThreadCount(2)
        QThreadPool.globalInstance().start(job)

    def finish_job(self,job):
        if job in self.all_jobs:self.all_jobs.remove(job)

    def commit_ready(self,count):
        self.commit_job=None
        self.import_status.setText(f"Đã nhập {count} câu; mục lỗi vẫn giữ trong hàng chờ.")
        self.logs.appendPlainText(self.import_status.text())
        self.refresh_status()

    def archive_question(self):
        from latex_question_studio.application.library import LibraryService
        editor=self.tabs.currentWidget()
        if editor not in self.editors:return
        if QMessageBox.question(self,"Lưu trữ","Ẩn câu khỏi thư viện/tạo đề, giữ source và lịch sử? Có thể phục hồi từ lịch sử revision.")!=QMessageBox.StandardButton.Yes:return
        if not self.save_question_editor():return
        q=self.editors[editor];LibraryService(self.services).save_metadata(q.id,{'archived':True})
        self.editors[editor]=self.services.questions.get(q.id)
        self.close_tab(self.tabs.indexOf(editor));self.refresh_status()

    def taxonomy_context(self,position):
        item=self.explorer.itemAt(position)
        if not item:return
        self.explorer.setCurrentItem(item);self.selected_taxonomy=item.data(0,Qt.ItemDataRole.UserRole)
        menu=QMenu(self);menu.addAction('Thêm mục con',self.add_taxonomy)
        if self.selected_taxonomy:
            menu.addAction('Đổi tên',self.rename_taxonomy);menu.addAction('Xóa mục rỗng',self.remove_taxonomy)
        menu.exec(self.explorer.viewport().mapToGlobal(position))

    def rename_taxonomy(self):
        name,ok=QInputDialog.getText(self,'Đổi tên phân loại','Tên mới:')
        if ok and name.strip():
            with self.services.database.transaction() as c:c.execute('UPDATE taxonomy_nodes SET name=? WHERE id=?',(name.strip(),self.selected_taxonomy))
            self.refresh_status()

    def remove_taxonomy(self):
        if QMessageBox.question(self,'Xóa mục','Chỉ xóa mục không có câu hoặc mục con. Tiếp tục?')!=QMessageBox.StandardButton.Yes:return
        try:
            with self.services.database.transaction() as c:c.execute('DELETE FROM taxonomy_nodes WHERE id=?',(self.selected_taxonomy,))
            self.selected_taxonomy=None;self.refresh_status()
        except Exception:QMessageBox.warning(self,'Không thể xóa','Mục vẫn có câu hỏi hoặc mục con.')

    def preview_page(self,direction):
        from latex_question_studio.preview.compiler import Compiler
        from latex_question_studio.ui.jobs import Job
        info=getattr(self,'preview_info',None)
        if not info:return
        question_id,source,result,pages,page=info;target=page+direction
        editor=self.tabs.currentWidget()
        if not result.ok or not 0<=target<pages or editor not in self.editors or self.editors[editor].id!=question_id:return
        generation=self.preview_generation
        def work(cancelled,progress):
            image,total=Compiler.render(result.pdf,page=target)
            return generation,question_id,source,result,image,total,target
        job=Job(work);job.signals.completed.connect(self.preview_ready);self.start_job(job)

    def restore_archived(self):
        from latex_question_studio.application.library import LibraryService
        with self.services.database.connect() as c:
            rows=c.execute("SELECT q.id,q.latex_source FROM questions q JOIN question_metadata m ON q.id=m.question_id WHERE json_extract(m.data_json,'$.archived')=1 ORDER BY q.updated_at DESC LIMIT 500").fetchall()
        if not rows:self.logs.appendPlainText('Không có câu lưu trữ.');return
        labels=[r['id'][:8]+' • '+r['latex_source'].replace('\n',' ')[:100] for r in rows]
        label,ok=QInputDialog.getItem(self,'Khôi phục câu','Câu sẽ hiện lại trong thư viện:',labels,0,False)
        if ok:
            question_id=rows[labels.index(label)]['id'];LibraryService(self.services).save_metadata(question_id,{'archived':False})
            self.refresh_status();self.open_question(question_id)
