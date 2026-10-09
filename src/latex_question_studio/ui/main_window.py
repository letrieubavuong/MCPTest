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
        return 0 if parent.isValid() else 4

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():return None
        q=self.rows[index.row()]
        from latex_question_studio.ui.pages.library import readable,TYPE_LABELS
        label=getattr(self,'classification_labels',{}).get(q.id,'Chưa phân loại')
        values=(readable(q.latex_source)[:220],TYPE_LABELS.get(q.question_type,q.question_type),q.cognitive_level or 'Chưa gán',label)
        if role==Qt.ItemDataRole.DisplayRole:return values[index.column()]
        if role==Qt.ItemDataRole.ToolTipRole:return q.latex_source if index.column()==0 else values[index.column()]

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role==Qt.ItemDataRole.DisplayRole and orientation==Qt.Orientation.Horizontal:
            return ('Nội dung câu hỏi','Loại','Mức độ','Bài / dạng')[section]

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
        from latex_question_studio.ui.shell.application import ApplicationShell
        self.shell = ApplicationShell(self)
        self.drawer=self.shell.activity;self.drawer_toggle=self.shell.toggle
        self.navigation=self.shell.navigation;self.pages=self.shell.pages
        self.sidebar_collapsed=False
        self.drawer_toggle.clicked.connect(self.toggle_drawer)
        self.setCentralWidget(self.shell)
        self.library_control = QMainWindow()
        self.library_control.setWindowFlags(Qt.WindowType.Widget)
        self.pages.addWidget(self.library_control)
        self.explorer = QTreeWidget()
        self.explorer.setExpandsOnDoubleClick(True)
        self.explorer.setHeaderLabel("Môn → Chương → Bài → Dạng")
        self.root_node = QTreeWidgetItem(self.explorer, ["Tất cả câu hỏi"])
        self.explorer.itemClicked.connect(self.taxonomy_selected)
        self.explorer.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.explorer.customContextMenuRequested.connect(self.taxonomy_context)
        self.explorer_dock = self.make_dock("CÂY CSDL", "explorer", self.explorer, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.explorer_dock.setMinimumWidth(240)
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
        # Workspace layout is assembled below after inspector creation.
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
        from latex_question_studio.ui.components.workspace import Workspace
        self.library_split=Workspace('librarySplit')
        self.library_split.addWidget(self.explorer_dock);self.library_split.addWidget(self.tabs);self.library_split.addWidget(self.preview_dock)
        self.library_split.setSizes([270,640,400])
        self.library_vertical=QSplitter(Qt.Orientation.Vertical)
        self.library_vertical.setChildrenCollapsible(False)
        self.library_vertical.addWidget(self.library_split);self.library_vertical.addWidget(self.log_dock)
        self.library_vertical.setSizes([640,120])
        self.library_control.setCentralWidget(self.library_vertical)
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
        from latex_question_studio.ui.pages.library import LibraryWorkspace
        self.library_ui=LibraryWorkspace(self,library,scroll)
        self.restore_workspace()
        self.ensure_library_tree()
        self.apply_theme()
        self.refresh_status()

    def build_pages(self):
        self.import_page = QWidget()
        self.import_page.setObjectName("importPage")
        layout = QVBoxLayout(self.import_page)
        layout.addWidget(QLabel("NHẬP CÂU HỎI"))
        self.import_toolbar=QToolBar('Nhập câu hỏi',self.import_page)
        self.import_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        from latex_question_studio.ui.icons import icon
        for name,text,callback in (('import','Chọn file TeX',self.import_files),('chapter','Chọn thư mục',self.import_folder),('bank','Hàng chờ / Sửa lỗi',self.show_pending)):
            action=self.import_toolbar.addAction(icon(name,'#4ba3eb'),text);action.setToolTip(text);action.triggered.connect(callback)
            if name=='import':self.import_toolbar.widgetForAction(action).setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        layout.addWidget(self.import_toolbar)
        self.import_steps=QLabel('1 Chọn tệp   →   2 Phân tích   →   3 Duyệt / phân loại   →   4 Xác nhận nhập')
        layout.addWidget(self.import_steps)
        self.import_status = QLabel("Chọn file hoặc thư mục LaTeX để xem trước, rồi xác nhận nhập.")
        self.import_status.setWordWrap(True)
        layout.addWidget(self.import_status)
        self.import_progress = QProgressBar(); self.import_progress.setValue(0)
        layout.addWidget(self.import_progress)
        self.import_cancel=self.import_toolbar.addAction(icon('close','#4ba3eb'),'Hủy phân tích')
        self.import_cancel.setToolTip('Hủy phân tích file TeX đang chạy');self.import_cancel.setEnabled(False)
        self.import_cancel.triggered.connect(self.cancel_import)
        self.import_content_host = QWidget(self.import_page)
        self.import_content = QVBoxLayout(self.import_content_host)
        self.import_content.setContentsMargins(0,0,0,0)
        layout.addWidget(self.import_content_host,1)
        self.pages.addWidget(self.import_page)
        from latex_question_studio.ui.exam_dialog import ExamDialog
        self.exam_page = ExamDialog([], self.pages,services=self.services,run_job=self.start_job)
        self.exam_page.setObjectName("examPage")
        self.exam_page.submitted.connect(self.generate_exam)
        self.exam_page.use_selection.connect(self.use_exam_selection)
        self.exam_status = QLabel("Chọn câu trong Xem CSDL rồi lấy vào đề, hoặc thêm hàng ma trận.")
        self.exam_status.setWordWrap(True)
        self.exam_page.layout().addWidget(self.exam_status)
        self.exam_page.toolbar.addSeparator()
        self.exam_cancel=self.exam_page.toolbar.addAction(icon('close','#4ba3eb'),'Hủy tạo đề')
        self.exam_cancel.setToolTip('Hủy tác vụ tạo đề đang chạy');self.exam_cancel.setEnabled(False);self.exam_cancel.triggered.connect(self.cancel_exam)
        self.exam_export = self.exam_page.toolbar.addAction(icon('save','#4ba3eb'),"Xuất đề / Đáp án / Lời giải")
        self.exam_export.setToolTip('Xuất đề, đáp án hoặc lời giải từ đề đã tạo')
        self.exam_export.setEnabled(False)
        self.exam_export.triggered.connect(lambda: self.export_exam(self.exam_snapshot))
        self.pages.addWidget(self.exam_page)
        self.settings_page = QWidget()
        layout = QVBoxLayout(self.settings_page); layout.addWidget(QLabel("CÀI ĐẶT"))
        form = QFormLayout(); config = self.compiler_config()
        self.engine_input = QLineEdit(config.get('engine', 'pdflatex'))
        self.preamble_input = QLineEdit(config.get('preamble_file', ''))
        form.addRow("Đường dẫn pdfLaTeX", self.engine_input)
        self.preamble_input.setPlaceholderText("Để trống: MAPClass + ex_test trong docs")
        form.addRow("File preamble riêng", self.preamble_input)
        layout.addWidget(QLabel("Preview mặc định: MAPClass + ex_test • hiển thị đáp án và lời giải để phân loại câu hỏi."))
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
        if index==0 and hasattr(self,"library_ui"):self.ensure_library_tree()
        self.statusBar().showMessage(["CSDL", "Nhập câu hỏi", "Ra đề thi", "Cài đặt", "Bài giảng"][index]+f" · {len(self.all_jobs)} tác vụ đang chạy")
        if self.navigation.currentRow() != index: self.navigation.setCurrentRow(index)

    def ensure_library_tree(self):
        self.explorer_dock.show()
        self.explorer_dock.setMinimumWidth(240)
        sizes=self.library_split.sizes()
        if sizes and sizes[0]<240:self.library_split.setSizes([300,max(320,sum(sizes)-660),360])

    def toggle_drawer(self):
        self.sidebar_collapsed=not self.sidebar_collapsed
        if self.pages.currentIndex()==0:
            self.ensure_library_tree()
            sizes=self.library_split.sizes();total=sum(sizes)
            left=240 if self.sidebar_collapsed else 340
            self.library_split.setSizes([left,max(320,total-left-sizes[2]),sizes[2]])
            return
        page={2:getattr(self.exam_page,'workspace',None),4:getattr(self.lesson_page,'workspace',None),1:getattr(getattr(self,'import_review',None),'workspace',None)}.get(self.pages.currentIndex())
        if page and page.count():page.widget(0).setVisible(not self.sidebar_collapsed)

    def make_dock(self, title, name, widget, area):
        from latex_question_studio.ui.components.workspace import Panel
        return Panel(title,name,widget,self.library_control)

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

    def refresh_status(self,refresh_tree=True):
        try:
            count = self.filtered_count()
            self.table_model.replace_rows(self.library_page())
            if hasattr(self,"library_ui"):
                self.library_ui.update_table_details();self.library_ui.sync_cards();self.library_ui.update_scope(count)
            if refresh_tree:self.refresh_taxonomy()
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
            self.refresh_status(refresh_tree=False)

    def previous_page(self):
        self.offset = max(0, self.offset - 100)
        self.refresh_status(refresh_tree=False)

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
        editor.set_theme(self.theme)
        editor.setPlainText(question.latex_source)
        editor.document().setModified(False)
        self.editors[editor] = question
        self.tabs.addTab(editor, question.id[:8])
        editor.document().modificationChanged.connect(lambda modified, e=editor: self.dirty_changed(e, modified))
        editor.textChanged.connect(lambda e=editor:self.library_ui.editor_text_changed(e))
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
        from latex_question_studio.ui.themes.design import apply,TOKENS
        from latex_question_studio.ui.icons import icon
        apply(self.theme)
        for i,name in enumerate(('bank','import','exam','settings','lesson')):self.navigation.item(i).setIcon(icon(name,TOKENS[self.theme]['fg']))
        for editor in self.editors:editor.set_theme(self.theme)
        self.lesson_page.editor.set_theme(self.theme)

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        replace(self.services.config, theme=self.theme).save()
        self.apply_theme()

    def restore_workspace(self):
        if not self.layout_path.exists():
            return
        try:
            state = json.loads(self.layout_path.read_text(encoding="utf-8"))
            if state.get("version") not in (1, 2, 3):
                return
            self.restored_panels=state.get("panels",{})
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
            for split in self.findChildren(QSplitter):
                name=split.objectName()
                if name and hasattr(split,'restore'):split.restore(state.get('panels',{}).get(name,{}))
            self.library_vertical.setSizes(state.get('library_vertical',[640,120]))
            self.preview_dock.setVisible(state.get('preview_visible',True));self.log_dock.setVisible(state.get('logs_visible',True))
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
        state = {"version": 3, "panels":{**getattr(self,"restored_panels",{}),**{split.objectName():split.state() for split in self.findChildren(QSplitter) if split.objectName() and hasattr(split,"state")}}, "library_vertical":self.library_vertical.sizes(), "preview_visible":not self.preview_dock.isHidden(),"logs_visible":not self.log_dock.isHidden(), "taxonomy_id":getattr(self,'selected_taxonomy',None),"taxonomy_expanded":expanded, "page": self.pages.currentIndex(), "drawer_collapsed": self.sidebar_collapsed, "lesson_id": self.lesson_page.doc["id"] if self.lesson_page.doc else None, "geometry": base64.b64encode(bytes(self.saveGeometry())).decode(),
                 "layout": base64.b64encode(bytes(self.library_control.saveState())).decode(), "tabs": [q.id for q in self.editors.values()]}
        temp = self.layout_path.with_suffix(".tmp")
        temp.write_text(json.dumps(state), encoding="utf-8")
        temp.replace(self.layout_path)

    def closeEvent(self, event):
        if not self.lesson_page.save():
            event.ignore();return
        self.library_ui.preview_timer.stop();self.library_ui.timer.stop()
        self.exam_page.cancel_statistics()
        self.exam_page.preview.cancel()
        self.lesson_page.cancel_preview()
        if hasattr(getattr(self,'import_review',None),'cancel_preview'):self.import_review.cancel_preview()
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
        self.import_steps.setText("Chọn tệp ✓  →  PHÂN TÍCH  →  Duyệt / phân loại  →  Xác nhận")
        self.import_status.setText("Đang phân tích LaTeX…")
        self.import_cancel.setEnabled(True)
        self.import_job.signals.progress.connect(lambda done,total:self.import_progress.setValue(done))
        self.import_job.signals.completed.connect(self.import_ready)
        self.import_job.signals.failed.connect(self.import_failed)
        self.start_job(self.import_job)

    def cancel_import(self):
        for name in ('import_job','commit_job'):
            job=getattr(self,name,None)
            if job:job.cancelled.set()

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
        self.import_steps.setText("Chọn tệp ✓  →  Phân tích ✓  →  DUYỆT / PHÂN LOẠI  →  Xác nhận")
        self.import_status.setText(f"Đã phân tích {len(results)} mục. Xem và xác nhận bên dưới.")
        review = ImportReview(results, self.import_page,services=self.services)
        review.accepted.connect(lambda: self.commit_import(batch, review))
        review.rejected.connect(lambda: self.import_status.setText("Đã giữ batch trong hàng chờ."))
        self.replace_import_content(review)

    def commit_import(self, batch, review):
        from latex_question_studio.application.importing import ImportService
        from latex_question_studio.ui.jobs import Job
        if getattr(self, 'commit_job', None): return
        review.cancel_preview();review.setEnabled(False)
        for action in self.import_review_actions:action.setEnabled(False)
        self.import_cancel.setEnabled(True)
        selected_ids=review.selected_ids() if hasattr(review,"selected_ids") else None
        job = Job(lambda cancelled,progress:ImportService(self.services).commit(batch,selected_ids=selected_ids,cancelled=cancelled))
        self.commit_job = job
        job.signals.completed.connect(self.commit_ready)
        def failed(error):
            self.commit_job = None
            review.setEnabled(True)
            for action in self.import_review_actions:action.setEnabled(True)
            self.import_cancel.setEnabled(False)
            self.import_status.setText('Ghi batch lỗi: ' + error)
        job.signals.failed.connect(failed)
        self.start_job(job)

    def replace_import_content(self, widget):
        for action in getattr(self,'import_review_actions',[]):
            self.import_toolbar.removeAction(action)
        self.import_review_actions=[]
        while self.import_content.count():
            item = self.import_content.takeAt(0)
            if item.widget():
                if hasattr(item.widget(),'workspace'):
                    self.restored_panels=getattr(self,'restored_panels',{});self.restored_panels[item.widget().workspace.objectName()]=item.widget().workspace.state()
                if hasattr(item.widget(),'cancel_preview'):item.widget().cancel_preview()
                item.widget().deleteLater()
        self.import_content.addWidget(widget)
        self.import_review = widget
        if hasattr(widget,'workspace'):
            widget.workspace.restore(getattr(self,'restored_panels',{}).get(widget.workspace.objectName(),{}))
        if self.sidebar_collapsed and hasattr(widget,"workspace"):widget.workspace.widget(0).hide()
        if hasattr(widget,'toolbar'):
            self.import_review_actions.append(self.import_toolbar.addSeparator())
            for action in list(widget.toolbar.actions()):
                widget.toolbar.removeAction(action)
                self.import_toolbar.addAction(action)
                self.import_review_actions.append(action)
                button=self.import_toolbar.widgetForAction(action)
                if hasattr(button,'setToolButtonStyle'):
                    button.setProperty('primary',bool(action.property('primary')))
                    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon if button.property("primary") else Qt.ToolButtonStyle.ToolButtonIconOnly)
            widget.toolbar.hide()

    def show_pending(self):
        from latex_question_studio.ui.pending_dialog import PendingDialog
        if getattr(self, 'commit_job', None): return
        self.show_page(1)
        pending = PendingDialog(self.services, self.import_page)
        pending.committed.connect(self.refresh_status)
        self.replace_import_content(pending)

    def library_page(self):
        from latex_question_studio.application.search import SearchService
        return self.library_ui.search() if hasattr(self,"library_ui") else SearchService(self.services).find(getattr(self,"search_text",""),getattr(self,"search_filters",{}),offset=self.offset,taxonomy_id=getattr(self,"selected_taxonomy",None))

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
        from latex_question_studio.ui.icons import icon
        self.root_node.setIcon(0,icon('bank','#4ba3eb'))
        tree_icons={kind:icon(name,color) for kind,name,color in (('subject','subject','#4ba3eb'),('grade','subject','#4ba3eb'),('chapter','chapter','#e7ad4b'),('lesson','topic','#55bca3'),('topic','topic','#55bca3'))}
        items={n['id']:QTreeWidgetItem([f"{n['name']} ({n['count']})"]) for n in nodes}
        for n in nodes:
            item=items[n['id']];item.setData(0,Qt.ItemDataRole.UserRole,n['id']);item.setToolTip(0,n['name']);item.setIcon(0,tree_icons.get(n['kind'],tree_icons['topic']))
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
        for root in (n for n in nodes if n['parent_id'] is None):
            root_id=root['id'];attribute=root_id.split(':')[-1]+'_menu'
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
        self.show_page(0);self.tabs.setCurrentIndex(0)
        self.selected_taxonomy=item.data(0,Qt.ItemDataRole.UserRole)
        self.offset=0;self.refresh_status(refresh_tree=False)

    def edit_metadata(self):
        self.show_page(0)
        editor=self.tabs.currentWidget()
        if editor in self.editors:
            self.library_ui.selected_id=self.editors[editor].id;self.library_ui.load_metadata(self.editors[editor])
        self.preview_dock.show();self.library_ui.inspector.setCurrentIndex(1)

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
        q=self.editors.get(editor) or (self.library_ui.current_question() if hasattr(self,'library_ui') else None)
        if q is None:return
        self.cancel_preview();self.preview_generation+=1;generation=self.preview_generation
        source=editor.toPlainText() if editor in self.editors else q.latex_source
        config=self.compiler_config()
        cached=self.library_ui.cached(q,source,config)
        if cached:
            result,image,pages=cached
            self.preview_ready((generation,q.id,source,result,image,pages,0));return
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
        q=self.editors.get(editor) or self.library_ui.current_question()
        current_source=editor.toPlainText() if editor in self.editors else q.latex_source if q else None
        if generation!=self.preview_generation or not q or q.id!=question_id or current_source!=source:return
        self.preview_job=None
        self.preview_info=(question_id,source,result,pages,page)
        self.logs.setPlainText(result.log)
        self.library_ui.errors.setPlainText(result.log)
        if result.ok:
            self.library_ui.remember(q,source,self.compiler_config(),result,image,pages)
            self.library_ui.display_image(image)
            self.statusBar().showMessage(f"Preview • Trang {page+1}/{pages} • "+("Cache" if result.cache_hit else "Biên dịch mới"))
        else:
            self.preview.setPixmap(QPixmap());self.preview.setText("Không thể tạo preview. Xem Nhật ký / Tác vụ.")
            self.statusBar().showMessage("Preview đã hủy" if result.cancelled else "Preview lỗi")

    def search_library(self):
        self.show_page(0);self.tabs.setCurrentIndex(0);self.library_ui.query.setFocus()

    def clear_search(self):
        self.library_ui.reset_filters()

    def filter_library(self):
        self.show_page(0);self.tabs.setCurrentIndex(0);self.library_ui.kind.setFocus()

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
        if hasattr(self,'library_ui') and self.tabs.currentIndex()==0 and self.library_ui.mode.currentIndex()==1:
            return [item.data(Qt.ItemDataRole.UserRole) for item in self.library_ui.cards.selectedItems()]
        editor = self.tabs.currentWidget()
        return ([self.editors[editor].id] if editor in self.editors else
                [self.table_model.rows[i.row()].id for i in self.table.selectionModel().selectedRows()])

    def create_exam(self):
        self.show_page(2)

    def use_exam_selection(self):
        self.exam_page.set_manual_ids(self.selected_exam_ids())

    def generate_exam(self):
        from latex_question_studio.application.exams import ExamService
        from latex_question_studio.ui.jobs import Job
        if getattr(self,'exam_job',None):return
        try:values=self.exam_page.values()
        except Exception as error:self.exam_status.setText('Không thể tạo đề: '+str(error));return
        self.exam_page.generate_action.setEnabled(False);self.exam_export.setEnabled(False);self.exam_cancel.setEnabled(True)
        self.exam_status.setText('Đang tạo đề…')
        job=Job(lambda cancelled,progress:ExamService(self.services).generate(**values,cancelled=cancelled));self.exam_job=job
        def finished():
            self.exam_job=None;self.exam_page.generate_action.setEnabled(True);self.exam_cancel.setEnabled(False)
        def ready(payload):
            finished();version,snapshot=payload;self.exam_snapshot=snapshot
            warnings=snapshot.get('duplicate_warnings',[])
            self.exam_status.setText(f"Đã tạo đề {version[:8]} gồm {len(snapshot['questions'])} câu • {len(warnings)} cặp trùng/gần trùng cần kiểm tra.")
            self.exam_status.setToolTip('\n'.join(f"{w['kind']}: {' / '.join(w['question_ids'])}" for w in warnings))
            self.exam_page.show_snapshot(snapshot)
            self.exam_export.setEnabled(True);self.logs.appendPlainText(self.exam_status.text())
        def failed(message):finished();self.exam_status.setText('Tạo đề đã dừng: '+message)
        job.signals.completed.connect(ready);job.signals.failed.connect(failed);self.start_job(job)

    def cancel_exam(self):
        if getattr(self,'exam_job',None):self.exam_job.cancelled.set();self.exam_status.setText('Đang hủy tạo đề…')

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
        return self.library_ui.search(count_only=True) if hasattr(self,"library_ui") else SearchService(self.services).find(getattr(self,"search_text",""),getattr(self,"search_filters",{}),taxonomy_id=getattr(self,"selected_taxonomy",None),count_only=True)

    def start_job(self,job):
        from PySide6.QtCore import QThreadPool
        self.all_jobs.append(job)
        if hasattr(self,"library_ui"):self.library_ui.update_tasks()
        job.signals.completed.connect(lambda *_:self.finish_job(job))
        job.signals.failed.connect(lambda *_:self.finish_job(job))
        QThreadPool.globalInstance().setMaxThreadCount(2)
        QThreadPool.globalInstance().start(job)

    def finish_job(self,job):
        if job in self.all_jobs:self.all_jobs.remove(job)
        if hasattr(self,"library_ui"):self.library_ui.update_tasks()

    def commit_ready(self,count):
        self.commit_job=None
        self.import_steps.setText("Chọn tệp ✓  →  Phân tích ✓  →  Duyệt ✓  →  NHẬP HOÀN TẤT")
        self.import_cancel.setEnabled(False)
        for action in self.import_review_actions:action.setEnabled(False)
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
        q=self.editors.get(editor) or self.library_ui.current_question()
        if not result.ok or not 0<=target<pages or not q or q.id!=question_id:return
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

    def eventFilter(self,obj,event):
        from PySide6.QtCore import QEvent,QTimer
        if hasattr(self,'library_ui') and obj==self.library_ui.scroll.viewport() and event.type()==QEvent.Type.Resize:QTimer.singleShot(0,self.library_ui.fit)
        return super().eventFilter(obj,event)
