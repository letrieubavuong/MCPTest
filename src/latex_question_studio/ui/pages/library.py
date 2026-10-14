from dataclasses import replace
from collections import OrderedDict
import json,re,hashlib
from PySide6.QtCore import Qt,QTimer,QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLineEdit,QComboBox,QTabWidget,QPlainTextEdit,QFormLayout,QPushButton,QListWidget,QListWidgetItem,QLabel,QStackedWidget,QHeaderView,QScrollArea,QListView,QFrame,QToolButton,QMenu,QDialog,QTreeWidget,QTreeWidgetItem,QMessageBox,QInputDialog)
from latex_question_studio.ui.components.workspace import CommandToolbar
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.search import SearchService
from latex_question_studio.persistence.questions import QuestionRepository
from latex_question_studio.domain.curriculum import classification,breadcrumb
from latex_question_studio.parsing.latex import group,skip_space
from latex_question_studio.preview.queue import RenderPriority
TYPE_LABELS={'mcq':'Trắc nghiệm','true_false':'Đúng / sai','essay':'Tự luận','short_answer':'Trả lời ngắn','unknown':'Chưa xác định'}

SUPERSCRIPTS=str.maketrans('0123456789+-=()nxyz','⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿˣʸᶻ')
SUBSCRIPTS=str.maketrans('0123456789+-=()nij','₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₙᵢⱼ')

def format_tex_math(s):
    if not s:return ''
    s=re.sub(r'(?m)%[^\n]*','',s)
    s=re.sub(r'\\(?:text|mathrm|mathbf|textit|textbf|mathit)\{([^{}]*)\}',r'\1',s)
    for _ in range(3):
        s=re.sub(r'\\d?frac\{([^{}]+)\}\{([^{}]+)\}',r'\1/\2',s)
    s=re.sub(r'\\sqrt\{([^{}]+)\}',r'√\1',s)
    s=re.sub(r'\\vec\{([^{}]+)\}',r'\1⃗',s)
    s=re.sub(r'\\widehat\{([^{}]+)\}',r'∠\1',s)
    s=re.sub(r'\^\\circ\b','°',s)
    s=re.sub(r'\^\{([0-9+-nxyz]+)\}',lambda m:m.group(1).translate(SUPERSCRIPTS),s)
    s=re.sub(r'\^([0-9n])',lambda m:m.group(1).translate(SUPERSCRIPTS),s)
    s=re.sub(r'_\{([0-9+-nij]+)\}',lambda m:m.group(1).translate(SUBSCRIPTS),s)
    s=re.sub(r'_([0-9n])',lambda m:m.group(1).translate(SUBSCRIPTS),s)
    syms=[
        (r'\\(?:le|leq)\b','≤'),(r'\\(?:ge|geq)\b','≥'),(r'\\(?:neq|ne)\b','≠'),
        (r'\\approx\b','≈'),(r'\\pm\b','±'),(r'\\times\b','×'),(r'\\div\b','÷'),
        (r'\\cdot\b','·'),(r'\\circ\b','°'),(r'\\infty\b','∞'),(r'\\in\b','∈'),
        (r'\\notin\b','∉'),(r'\\subset\b','⊂'),(r'\\cap\b','∩'),(r'\\cup\b','∪'),
        (r'\\forall\b','∀'),(r'\\exists\b','∃'),(r'\\(?:emptyset|varnothing)\b','∅'),
        (r'\\Rightarrow\b','⇒'),(r'\\Leftrightarrow\b','⇔'),(r'\\(?:rightarrow|to)\b','→'),
        (r'\\perp\b','⊥'),(r'\\parallel\b','∥'),(r'\\angle\b','∠'),(r'\\triangle\b','△'),
        (r'\\int\b','∫'),(r'\\sum\b','∑'),(r'\\alpha\b','α'),(r'\\beta\b','β'),
        (r'\\gamma\b','γ'),(r'\\delta\b','δ'),(r'\\pi\b','π'),(r'\\Delta\b','Δ'),
        (r'\\Omega\b','Ω'),(r'\\omega\b','ω'),
    ]
    for pat,rep in syms:s=re.sub(pat,rep,s)
    s=re.sub(r'\\(?:begin|end)\{[^}]*\}','',s)
    s=re.sub(r'\\(?:displaystyle|limits|quad|qquad|left|right)','',s)
    s=re.sub(r'\\,',' ',s)
    s=s.replace('$','')
    s=re.sub(r'([0-9a-zA-Z])([=+\-])([0-9a-zA-Z])',r'\1 \2 \3',s)
    return re.sub(r'\s+',' ',s).strip()

def parse_tex_card(source):
    res={'stem':'','options':[],'short_ans':'','solution':'','type':'essay'}
    if not source:return res
    sol=''
    m=re.search(r'\\(?:loigiai|hdan)\s*\{',source)
    cleaned=source
    if m:
        try:
            sol,end,start=group(source,m.end()-1)
            cleaned=source[:m.start()]+source[end:]
        except Exception:pass
    res['solution']=format_tex_math(sol)
    cm=re.search(r'\\(choiceTFt?|choice)\b',cleaned)
    if cm:
        macro=cm.group(1)
        res['type']='true_false' if 'TF' in macro else 'mcq'
        res['stem']=format_tex_math(cleaned[:cm.start()])
        idx=cm.end()
        idx=skip_space(cleaned,idx)
        if idx<len(cleaned) and cleaned[idx]=='[':
            try:_,idx,_=group(cleaned,idx,'[',']')
            except Exception:pass
        options=[]
        labels=['A','B','C','D'] if res['type']=='mcq' else ['a','b','c','d']
        for l in labels:
            try:
                val,idx,_=group(cleaned,idx)
                correct=bool(re.search(r'\\True\b',val))
                clean_val=re.sub(r'\\True\b','',val).strip()
                options.append({'label':l,'text':format_tex_math(clean_val),'correct':correct})
            except Exception:break
        res['options']=options
        return res
    sm=re.search(r'\\shortans\s*\{',cleaned)
    if sm:
        res['type']='short_answer'
        res['stem']=format_tex_math(cleaned[:sm.start()])
        try:
            ans,_,_=group(cleaned,sm.end()-1)
            res['short_ans']=format_tex_math(ans)
        except Exception:pass
        return res
    res['stem']=format_tex_math(cleaned)
    return res

def readable(source):
    # Display summary only. Never feed this transformed text to parser/export.
    p=parse_tex_card(source)
    return p['stem'] or format_tex_math(source)

class MoveTaxonomyDialog(QDialog):
    def __init__(self, nodes, question_count=1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Di chuyển câu hỏi sang Bài / Dạng khác")
        self.resize(560, 580)
        self.selected_node_id = None
        self.nodes = nodes
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        hint = QLabel(f"Chọn bài hoặc dạng đích để di chuyển <b>{question_count}</b> câu hỏi đã chọn:")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm kiếm môn, chương, bài, dạng... (Ctrl+F)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_tree)
        layout.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Cây CSDL • Môn → Chương → Bài → Dạng")
        self.tree.setExpandsOnDoubleClick(True)
        layout.addWidget(self.tree, 1)
        self.dest_label = QLabel("Chưa chọn bài / dạng đích")
        self.dest_label.setWordWrap(True)
        self.dest_label.setStyleSheet("color: #4ba3eb; font-weight: bold;")
        layout.addWidget(self.dest_label)
        btn_box = QHBoxLayout()
        self.unassign_btn = QPushButton("Chuyển thành Chưa phân loại")
        self.unassign_btn.clicked.connect(self.choose_unassign)
        btn_box.addWidget(self.unassign_btn)
        btn_box.addStretch()
        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.cancel_btn)
        self.move_btn = QPushButton("Di chuyển")
        self.move_btn.setProperty("primary", True)
        self.move_btn.setEnabled(False)
        self.move_btn.clicked.connect(self.accept)
        btn_box.addWidget(self.move_btn)
        layout.addLayout(btn_box)
        self.tree.currentItemChanged.connect(self.node_selected)
        self.populate_tree()

    def populate_tree(self):
        self.tree.clear();self.items = {}
        from latex_question_studio.ui.icons import icon
        icons = {kind: icon(name, color) for kind, name, color in [
            ('subject', 'subject', '#4ba3eb'), ('grade', 'subject', '#4ba3eb'),
            ('chapter', 'chapter', '#e7ad4b'), ('lesson', 'topic', '#55bca3'),
            ('topic', 'topic', '#55bca3')]}
        for node in self.nodes:
            item = QTreeWidgetItem([node['name']])
            item.setData(0, Qt.ItemDataRole.UserRole, node['id'])
            item.setIcon(0, icons.get(node['kind'], icons['topic']))
            self.items[node['id']] = item
        for node in self.nodes:
            item = self.items[node['id']]
            parent = self.items.get(node['parent_id'])
            if parent: parent.addChild(item)
            else: self.tree.addTopLevelItem(item)

    def filter_tree(self, text):
        text = text.casefold().strip()
        for node in self.nodes:
            item = self.items[node['id']]
            match = not text or text in breadcrumb(self.nodes, node['id']).casefold()
            item.setHidden(not match)
            if match and text:
                p = item.parent()
                while p: p.setHidden(False); p.setExpanded(True); p = p.parent()

    def node_selected(self, current, _):
        if not current:
            self.move_btn.setEnabled(False);self.dest_label.setText("Chưa chọn bài / dạng đích");return
        node_id = current.data(0, Qt.ItemDataRole.UserRole)
        node = next((n for n in self.nodes if n['id'] == node_id), None)
        if node and node['kind'] in ('lesson', 'topic'):
            self.selected_node_id = node_id
            self.dest_label.setText(f"Đích đến: {breadcrumb(self.nodes, node_id)}")
            self.move_btn.setEnabled(True)
        else:
            self.selected_node_id = None
            self.dest_label.setText("Vui lòng chọn cấp Bài hoặc Dạng (không chọn Môn/Chương)")
            self.move_btn.setEnabled(False)

    def choose_unassign(self):
        self.selected_node_id = None
        self.dest_label.setText("Đích đến: Chưa phân loại")
        self.accept()

class LibraryWorkspace:
    def __init__(self,w,library,scroll):
        self.w=w;self.cache=OrderedDict();self.images={};self.compile_errors={};self.original=None;self.scroll=scroll;self.selected_id=None;self.loading=False;self.expanded_ids=set()
        layout=library.layout();layout.setContentsMargins(8,8,8,8);layout.setSpacing(6)
        self.toolbar=CommandToolbar('Thư viện',w.library_control)
        frame=QWidget();outer=QVBoxLayout(frame);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0);outer.addWidget(self.toolbar);outer.addWidget(w.library_vertical,1);w.library_control.setCentralWidget(frame)
        self.toolbar.command('lesson','Sửa câu',self.edit)
        self.toolbar.command('subject','Phân loại',self.open_classification)
        self.toolbar.command('chapter','Di chuyển dạng',self.move_questions)
        self.toolbar.command('preview','Xem trước',self.preview_action,False)
        self.toolbar.command('save','Lưu câu · Ctrl+S',w.save_current)
        self.toolbar.addSeparator()
        self.toolbar.command('bank','Lấy vào đề',lambda:(w.use_exam_selection(),w.show_page(2)))
        from PySide6.QtWidgets import QToolButton,QMenu
        from latex_question_studio.ui.icons import icon
        more=QToolButton();more.setText('Thao tác khác');more.setIcon(icon('settings','#6d8aa6'));more.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        menu=QMenu(more)
        menu.addAction('Thêm câu hỏi mới · Ctrl+N', w.new_question)
        menu.addAction('Tìm câu hỏi trùng lặp...', w.find_duplicates)
        menu.addSeparator()
        menu.addAction('Di chuyển sang dạng / bài khác...', self.move_questions)
        menu.addAction('Đổi dạng thức câu hỏi (MCQ / Đúng-Sai / Điền khuyết / Tự luận)...', self.change_type_dialog)
        menu.addAction('Phân loại câu đã chọn...', self.open_classification)
        menu.addAction('Thêm mục phân loại mới...', w.add_taxonomy)
        menu.addSeparator()
        menu.addAction('Sao chép câu đã chọn',self.copy)
        menu.addAction('Lưu trữ câu đã chọn',self.archive)
        menu.addAction('Khôi phục câu đã lưu trữ...', w.restore_archived)
        menu.addAction('Lịch sử phiên bản / Khôi phục...', w.show_revisions)
        menu.addSeparator()
        menu.addAction('Trang trước · Alt+Left',w.previous_page);menu.addAction('Trang tiếp · Alt+Right',w.next_page)
        menu.addAction('Đi tới dòng lỗi LaTeX',self.goto_error);menu.addAction('Mở / ẩn nhật ký & tác vụ',w.log_dock.toggleViewAction().trigger)
        more.setMenu(menu);more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup);self.toolbar.addWidget(more)
        for action in self.toolbar.actions():
            button=self.toolbar.widgetForAction(action)
            if hasattr(button,'setToolButtonStyle'):button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.scope_label=QLabel('Phạm vi: Toàn bộ CSDL');self.scope_label.setWordWrap(True);self.scope_label.setObjectName('scopeBreadcrumb')
        self.guide=QLabel('1. Chọn bài / dạng bên trái   →   2. Chọn câu ở giữa   →   3. Xem trước hoặc sửa / phân loại')
        self.guide.setWordWrap(True);self.guide.hide()
        header_bar=QHBoxLayout();header_bar.setContentsMargins(2,2,2,4);header_bar.setSpacing(8)
        header_bar.addWidget(self.scope_label,1)
        self.mode=QComboBox();self.mode.addItems(['Danh sách gọn','Thẻ preview']);self.mode.setCurrentIndex(1);self.mode.setFixedWidth(130)
        header_bar.addWidget(self.mode)
        self.expand_toggle=QToolButton();self.expand_toggle.setObjectName('expandAllToggle');self.expand_toggle.setText('Mở rộng tất cả');self.expand_toggle.setToolTip('Chuyển đổi mở rộng / thu gọn tất cả thẻ câu hỏi');self.expand_toggle.clicked.connect(self.toggle_all_expand)
        header_bar.addWidget(self.expand_toggle)
        layout.insertLayout(0,header_bar)
        filter_bar=QHBoxLayout();filter_bar.setContentsMargins(0,0,0,4);filter_bar.setSpacing(6)
        self.query=QLineEdit();self.query.setPlaceholderText('Tìm nhanh nội dung câu hỏi, nguồn, nhãn… (Ctrl+F)');self.query.setClearButtonEnabled(True)
        filter_bar.addWidget(self.query,1)
        self.kind=QComboBox();self.kind.addItem('Mọi loại','')
        for key,label in TYPE_LABELS.items():self.kind.addItem(label,key)
        self.kind.setMinimumWidth(95)
        self.level=QComboBox();self.level.addItem('Mọi mức độ','')
        for key,label in [('NB','Nhận biết'),('TH','Thông hiểu'),('VD','Vận dụng'),('VDC','Vận dụng cao')]:self.level.addItem(label,key)
        self.level.setMinimumWidth(90)
        self.state=QComboBox()
        for label,key in [('Đang sử dụng','active'),('Chưa phân loại','unclassified'),('Source lỗi','invalid'),('Đã lưu trữ','archived'),('Có tài nguyên','has_asset'),('Thiếu / hỏng tài nguyên','asset_problem'),('Cần xem xét tài nguyên','asset_review')]:self.state.addItem(label,key)
        self.state.setMinimumWidth(110)
        for combo in (self.kind,self.level,self.state):filter_bar.addWidget(combo)
        layout.insertLayout(1,filter_bar)
        layout.removeWidget(w.table);self.stack=QStackedWidget();self.stack.addWidget(w.table)
        self.cards=QListWidget();self.cards.setObjectName('questionCards');self.cards.setViewMode(QListView.ViewMode.ListMode);self.cards.setFlow(QListView.Flow.TopToBottom);self.cards.setResizeMode(QListView.ResizeMode.Adjust);self.cards.setMovement(QListView.Movement.Static);self.cards.setWrapping(False);self.cards.setSpacing(6);self.cards.setUniformItemSizes(False);self.cards.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection);self.stack.addWidget(self.cards);layout.insertWidget(4,self.stack,1)
        w.table.setSelectionMode(w.table.SelectionMode.ExtendedSelection);w.table.setWordWrap(False)
        w.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);w.table.setColumnWidth(1,95);w.table.setColumnWidth(2,75);w.table.setColumnWidth(3,140)
        w.table.verticalHeader().setDefaultSectionSize(35)
        self.cards.currentRowChanged.connect(self.card_selected);self.cards.itemDoubleClicked.connect(lambda *a:self.edit())
        w.table.selectionModel().currentRowChanged.connect(lambda current,old:self.select(current.row()))
        self.cards.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.cards.customContextMenuRequested.connect(self.question_context_menu)
        w.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);w.table.customContextMenuRequested.connect(self.question_context_menu)
        self.cards.itemSelectionChanged.connect(self.update_batch_bar)
        w.table.selectionModel().selectionChanged.connect(lambda *a:self.update_batch_bar())
        self.timer=QTimer(w);self.timer.setSingleShot(True);self.timer.setInterval(250);self.timer.timeout.connect(self.filters_changed)
        self.preview_timer=QTimer(w);self.preview_timer.setSingleShot(True);self.preview_timer.setInterval(250);self.preview_timer.timeout.connect(w.compile_current)
        self.query.textChanged.connect(lambda *a:self.timer.start())
        for combo in (self.kind,self.level,self.state):combo.currentIndexChanged.connect(self.filters_changed)
        self.mode.currentIndexChanged.connect(self.switch_mode)
        self.stack.setCurrentIndex(1)
        w.refresh_button.hide()
        if hasattr(w, 'render_queue'):
            w.render_queue.signals.ready.connect(self.on_queue_thumbnail_ready)
            w.render_queue.signals.failed.connect(self.on_queue_thumbnail_failed)
        self.scroll_timer = QTimer(w)
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.setInterval(120)
        self.scroll_timer.timeout.connect(self.on_cards_scroll_settled)
        self.cards.verticalScrollBar().valueChanged.connect(lambda *a: self.scroll_timer.start())

        # Floating Batch Action Bar for bulk question management
        self.batch_bar = QFrame()
        self.batch_bar.setObjectName("batchActionBar")
        bb_layout = QHBoxLayout(self.batch_bar)
        bb_layout.setContentsMargins(10, 6, 10, 6)
        bb_layout.setSpacing(8)
        self.batch_count_lbl = QLabel("Đã chọn 0 câu hỏi:")
        self.batch_count_lbl.setObjectName("batchCountLabel")
        bb_layout.addWidget(self.batch_count_lbl)
        btn_exam = QPushButton("➕ Lấy vào đề thi")
        btn_exam.setObjectName("batchBtn")
        btn_exam.setProperty("primary", True)
        btn_exam.clicked.connect(lambda: (w.use_exam_selection(), w.show_page(2)))
        bb_layout.addWidget(btn_exam)
        btn_move = QPushButton("📁 Chuyển dạng toán")
        btn_move.setObjectName("batchBtn")
        btn_move.clicked.connect(self.move_questions)
        bb_layout.addWidget(btn_move)
        btn_level = QPushButton("🏷 Đổi mức độ...")
        btn_level.setObjectName("batchBtn")
        btn_level.clicked.connect(self.batch_change_level)
        bb_layout.addWidget(btn_level)
        btn_type = QPushButton("Đổi dạng thức...")
        btn_type.setObjectName("batchBtn")
        btn_type.clicked.connect(self.change_type_dialog)
        bb_layout.addWidget(btn_type)
        btn_copy = QPushButton("Sao chép")
        btn_copy.setObjectName("batchBtn")
        btn_copy.clicked.connect(self.copy)
        bb_layout.addWidget(btn_copy)
        btn_archive = QPushButton("Lưu trữ")
        btn_archive.setObjectName("batchBtn")
        btn_archive.clicked.connect(self.archive)
        bb_layout.addWidget(btn_archive)
        bb_layout.addStretch(1)
        btn_uncheck = QPushButton("✕ Bỏ chọn")
        btn_uncheck.setObjectName("batchBtn")
        btn_uncheck.clicked.connect(self.clear_selection)
        bb_layout.addWidget(btn_uncheck)
        self.batch_bar.hide()
        layout.addWidget(self.batch_bar)
        self.inspector=QTabWidget();w.preview_dock.layout().replaceWidget(scroll,self.inspector);self.inspector.addTab(scroll,'Xem trước')
        metadata=QWidget();form=QFormLayout(metadata);self.meta_title=QLabel('Chọn câu hỏi');self.meta_title.setWordWrap(True);form.addRow(self.meta_title)
        self.asset_status=QLabel('Tài nguyên: chưa kiểm tra');self.asset_status.setWordWrap(True);form.addRow(self.asset_status)
        self.taxonomy=QComboBox();self.taxonomy.setMinimumContentsLength(15);self.taxonomy.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);self.taxonomy.addItem('Chưa phân loại',None)
        nodes=LibraryService(w.services).taxonomy();self.nodes=nodes
        for n in nodes:
            if n['kind'] in ('lesson','topic'):self.taxonomy.addItem(breadcrumb(nodes,n['id']),n['id'])
        form.addRow('Bài / dạng',self.taxonomy)
        self.meta_level=QComboBox()
        for label,key in [('Chưa gán',''),('Nhận biết','NB'),('Thông hiểu','TH'),('Vận dụng','VD'),('Vận dụng cao','VDC')]:self.meta_level.addItem(label,key)
        form.addRow('Mức độ',self.meta_level)
        self.meta_type=QComboBox()
        for key,label in TYPE_LABELS.items():self.meta_type.addItem(label,key)
        form.addRow('Dạng thức câu',self.meta_type)
        self.tags=QLineEdit();form.addRow('Nhãn',self.tags);self.origin=QLineEdit();form.addRow('Nguồn',self.origin)
        save=QPushButton('Lưu phân loại');save.setProperty('primary',True);save.clicked.connect(self.save_metadata);form.addRow(save)
        self.inspector.addTab(metadata,'Phân loại')
        source_panel=QWidget();sp_box=QVBoxLayout(source_panel);sp_box.setContentsMargins(4,4,4,4);sp_box.setSpacing(4)
        sp_top=QHBoxLayout();sp_top.addWidget(QLabel('Mã LaTeX của câu:'),1)
        self.save_source_btn=QPushButton('Lưu nội dung câu');self.save_source_btn.setProperty('primary',True);self.save_source_btn.setToolTip('Lưu nội dung câu hỏi và cập nhật xem trước');self.save_source_btn.clicked.connect(self.save_inline_source);sp_top.addWidget(self.save_source_btn)
        sp_box.addLayout(sp_top)
        from latex_question_studio.ui.editor import LatexEditor
        self.source=LatexEditor();self.source.set_theme(w.theme)
        self.source.setPlaceholderText('Chọn một câu hỏi để xem và sửa nội dung LaTeX...');sp_box.addWidget(self.source,1)
        self.inspector.addTab(source_panel,'Mã LaTeX');self.errors=QPlainTextEdit();self.errors.setReadOnly(True);self.inspector.addTab(self.errors,'Lỗi / nhật ký')
        self.inspector.setMinimumWidth(0);w.preview.setMinimumWidth(0)
        w.preview_dock.setMinimumWidth(0);w.explorer_dock.setMinimumWidth(240)
        w.tabs.currentChanged.connect(self.editor_selected)
        self.scroll.viewport().installEventFilter(w)
        self.tasks=QPlainTextEdit();self.tasks.setReadOnly(True)
        bottom=QTabWidget();w.log_dock.layout().replaceWidget(w.logs,bottom);bottom.addTab(w.logs,'Nhật ký');bottom.addTab(self.tasks,'Tác vụ')
        self.bottom_errors=QPlainTextEdit();self.bottom_errors.setReadOnly(True);bottom.addTab(self.bottom_errors,'Lỗi LaTeX');self.errors.textChanged.connect(lambda:self.bottom_errors.setPlainText(self.errors.toPlainText()))
        # CSDL navigation is essential, so it cannot disappear through a close icon.
        header=w.explorer_dock.layout().itemAt(0).widget()
        for button in header.findChildren(QToolButton):button.hide()
        self.empty_hint=QLabel();self.empty_hint.setWordWrap(True);layout.insertWidget(4,self.empty_hint)
        all_button=QPushButton('Xem tất cả câu');all_button.clicked.connect(self.show_all);layout.insertWidget(5,all_button)
        self.all_button=all_button
        if not w.layout_path.exists():w.log_dock.hide()

    def current_question(self):
        return self.w.services.questions.get(self.selected_id) if self.selected_id else None
    def editor_selected(self,index):
        if index==0:
            self.select(self.w.table.currentIndex().row());return
        editor=self.w.tabs.widget(index)
        if editor in self.w.editors:
            self.selected_id=self.w.editors[editor].id;self.load_metadata(self.w.editors[editor]);self.source.setPlainText(editor.toPlainText())
    def select(self,row):
        if self.loading:return
        self.preview_timer.stop();self.w.cancel_preview();self.w.preview_generation+=1;self.original=None;self.w.preview.clear();self.w.preview.setMinimumSize(0,0)
        q=self.w.table_model.rows[row] if 0<=row<len(self.w.table_model.rows) else None
        self.selected_id=q.id if q else None
        if q:
            self.source.setPlainText(q.latex_source);self.load_metadata(q);self.w.preview.setText('Đang chuẩn bị xem trước…')
            if self.w.tabs.currentIndex()==0:self.preview_timer.start()
        else:self.source.clear();self.w.preview.setText('Chọn câu để xem trước.');self.meta_title.setText('Chọn câu hỏi')
    def load_metadata(self,q):
        m=LibraryService(self.w.services).metadata(q.id)
        self.asset_status.setText('Tài nguyên: '+self.asset_summary(q.id))
        self.taxonomy.setCurrentIndex(max(0,self.taxonomy.findData(m.get('taxonomy_id'))));self.meta_level.setCurrentIndex(max(0,self.meta_level.findData(q.cognitive_level or '')))
        self.meta_type.setCurrentIndex(max(0,self.meta_type.findData(q.question_type or '')))
        self.tags.setText(', '.join(m.get('tags',[])));self.origin.setText(m.get('source',''));self.meta_title.setText(f'{TYPE_LABELS.get(q.question_type,q.question_type)} • Phiên bản {q.revision} • {q.id[:8]}')
    def save_metadata(self):
        q=self.current_question()
        if not q:return
        values=classification(self.nodes,self.taxonomy.currentData());values.update(taxonomy_id=self.taxonomy.currentData(),cognitive_level=self.meta_level.currentData() or None,question_type=self.meta_type.currentData() or q.question_type,tags=[x.strip() for x in self.tags.text().split(',') if x.strip()],source=self.origin.text().strip())
        try:
            LibraryService(self.w.services).save_metadata(q.id,values)
            for editor,old in self.w.editors.items():
                if old.id==q.id:self.w.editors[editor]=self.w.services.questions.get(q.id)
            self.w.refresh_status();self.w.statusBar().showMessage('Đã lưu phân loại')
        except Exception as error:self.errors.setPlainText(str(error));self.inspector.setCurrentWidget(self.errors)

    def save_inline_source(self):
        q=self.current_question()
        if not q:return
        new_source=self.source.toPlainText()
        if not new_source.strip():
            QMessageBox.warning(self.w,"Nội dung rỗng","Nội dung câu hỏi không được để trống.");return
        try:
            from latex_question_studio.parsing.latex import parse_questions
            parsed=parse_questions(new_source)
            if len(parsed)!=1 or parsed[0].diagnostics:
                if QMessageBox.question(self.w,"Cảnh báo cú pháp","Mã LaTeX có cảnh báo hoặc chưa đúng một môi trường câu hỏi. Vẫn tiếp tục lưu?")!=QMessageBox.StandardButton.Yes:
                    return
                updated_q=replace(q,latex_source=new_source,question_type="unknown")
            else:
                updated_q=replace(q,latex_source=new_source,question_type=parsed[0].question_type,solution=parsed[0].solution)
            self.w.services.questions.update(updated_q)
            for editor,old in self.w.editors.items():
                if old.id==q.id:
                    self.w.editors[editor]=updated_q;editor.blockSignals(True);editor.setPlainText(new_source);editor.document().setModified(False);editor.blockSignals(False)
            self.w.refresh_status();self.w.compile_current();self.w.statusBar().showMessage("Đã lưu nội dung câu hỏi.")
        except Exception as error:QMessageBox.warning(self.w,"Không thể lưu",str(error))

    def move_questions(self):
        ids=self.ids()
        if not ids:
            QMessageBox.information(self.w,"Chưa chọn câu","Vui lòng chọn ít nhất một câu hỏi để di chuyển.");return
        dlg=MoveTaxonomyDialog(self.nodes,question_count=len(ids),parent=self.w)
        if dlg.exec()!=QDialog.DialogCode.Accepted:return
        target_id=dlg.selected_node_id
        try:
            for qid in ids:
                LibraryService(self.w.services).save_metadata(qid,{'taxonomy_id':target_id})
            self.w.refresh_status()
            dest_name=breadcrumb(self.nodes,target_id) if target_id else "Chưa phân loại"
            self.w.statusBar().showMessage(f"Đã di chuyển {len(ids)} câu hỏi sang: {dest_name}")
        except Exception as error:QMessageBox.warning(self.w,"Lỗi di chuyển",str(error))

    def change_type_dialog(self):
        ids=self.ids()
        if not ids:
            QMessageBox.information(self.w,"Chưa chọn câu","Vui lòng chọn ít nhất một câu hỏi để đổi dạng thức.");return
        labels=[TYPE_LABELS.get(k,k) for k in ('mcq','true_false','short_answer','essay')]
        keys=['mcq','true_false','short_answer','essay']
        chosen,ok=QInputDialog.getItem(self.w,"Đổi dạng thức câu hỏi",f"Chọn dạng thức mới cho {len(ids)} câu hỏi đã chọn:",labels,0,False)
        if not ok:return
        new_type=keys[labels.index(chosen)]
        try:
            for qid in ids:
                LibraryService(self.w.services).save_metadata(qid,{'question_type':new_type})
            self.w.refresh_status();self.w.statusBar().showMessage(f"Đã đổi dạng thức {len(ids)} câu thành: {chosen}")
        except Exception as error:QMessageBox.warning(self.w,"Lỗi đổi dạng thức",str(error))

    def open_classification(self):
        ids=self.ids()
        if len(ids)>1:
            from latex_question_studio.ui.metadata_dialog import MetadataDialog
            m=LibraryService(self.w.services).metadata(ids[0]) if ids else {}
            dlg=MetadataDialog(m,self.nodes,parent=self.w)
            dlg.setWindowTitle(f"Phân loại cho {len(ids)} câu hỏi đã chọn")
            if dlg.exec()==QDialog.DialogCode.Accepted:
                vals=dlg.values()
                for qid in ids:
                    LibraryService(self.w.services).save_metadata(qid,vals)
                self.w.refresh_status();self.w.statusBar().showMessage(f"Đã cập nhật phân loại cho {len(ids)} câu.")
        else:
            self.w.edit_metadata()

    def question_context_menu(self,pos):
        sender=self.cards if self.mode.currentIndex()==1 else self.w.table
        menu=QMenu(self.w)
        menu.addAction('Sửa câu hỏi này',self.edit)
        menu.addAction('Di chuyển sang dạng / bài khác...',self.move_questions)
        menu.addAction('Đổi dạng thức câu hỏi...',self.change_type_dialog)
        menu.addAction('Phân loại câu hỏi...',self.open_classification)
        menu.addSeparator()
        menu.addAction('Lấy vào đề thi',lambda:(self.w.use_exam_selection(),self.w.show_page(2)))
        menu.addAction('Sao chép câu',self.copy);menu.addAction('Lưu trữ câu',self.archive)
        menu.exec(sender.viewport().mapToGlobal(pos))
    def filters_changed(self,*args):
        if hasattr(self.w, 'render_queue'):
            self.w.render_queue.cancel_all_pending()
        self.w.search_text=self.query.text();self.w.search_filters={'question_type':self.kind.currentData(),'cognitive_level':self.level.currentData()};self.w.offset=0;self.w.refresh_status(refresh_tree=False)
    def reset_filters(self):
        if hasattr(self.w, 'render_queue'):
            self.w.render_queue.cancel_all_pending()
        for widget in (self.query,self.kind,self.level,self.state):widget.blockSignals(True)
        self.query.clear();self.kind.setCurrentIndex(0);self.level.setCurrentIndex(0);self.state.setCurrentIndex(0);self.w.selected_taxonomy=None
        for widget in (self.query,self.kind,self.level,self.state):widget.blockSignals(False)
        self.filters_changed()
    def search(self,count_only=False):
        w=self.w;join,where,args=SearchService(w.services).query_parts(getattr(w,'search_text',''),getattr(w,'search_filters',{}),getattr(w,'selected_taxonomy',None))
        if join is None:return 0 if count_only else []
        state=self.state.currentData()
        if state=='archived':where[0]="coalesce(json_extract(m.data_json,'$.archived'),0)=1"
        elif state=='unclassified':where.append("(q.cognitive_level IS NULL OR q.cognitive_level='' OR NOT EXISTS (SELECT 1 FROM question_taxonomy t WHERE t.question_id=q.id))")
        elif state=='invalid':where.append("EXISTS (SELECT 1 FROM question_analysis a WHERE a.question_id=q.id AND a.valid=0)")
        elif state=='has_asset':where.append("EXISTS (SELECT 1 FROM question_assets qa WHERE qa.question_id=q.id)")
        elif state=='asset_problem':where.append("EXISTS (SELECT 1 FROM question_assets qa WHERE qa.question_id=q.id AND qa.resolution_status<>'RESOLVED')")
        elif state=='asset_review':where.append("EXISTS (SELECT 1 FROM question_assets qa WHERE qa.question_id=q.id AND qa.resolution_status IN ('NEEDS_REVIEW','AMBIGUOUS_ASSET'))")
        sql=('SELECT count(*)' if count_only else 'SELECT q.*')+' FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id'+join+' WHERE '+' AND '.join(where)
        if not count_only:sql+=' ORDER BY '+('bm25(questions_fts),q.id' if join else 'q.created_at,q.id')+' LIMIT ? OFFSET ?';args+=[100,w.offset]
        with w.services.database.connect() as c:
            return c.execute(sql,args).fetchone()[0] if count_only else [QuestionRepository._question(r) for r in c.execute(sql,args)]

    def asset_summary(self, question_id):
        from latex_question_studio.application.assets import AssetStore
        with self.w.services.database.connect() as connection:
            rows=connection.execute('SELECT a.relative_path,a.content_hash,qa.resolution_status FROM question_assets qa JOIN assets a ON a.id=qa.asset_id WHERE qa.question_id=?',(question_id,)).fetchall()
        if not rows:return 'không có'
        store=AssetStore(self.w.services.config.data_dir);bad=[];shared=[]
        for row in rows:
            check=store.verify(row['relative_path'],row['content_hash'])
            if row['resolution_status']!='RESOLVED' or not check['ok']:bad.append(row['resolution_status'] if row['resolution_status']!='RESOLVED' else 'CORRUPT_ASSET')
            with self.w.services.database.connect() as connection:
                links=connection.execute('SELECT count(*) FROM question_assets WHERE asset_id=(SELECT id FROM assets WHERE relative_path=?)',(row['relative_path'],)).fetchone()[0]
            if links>1:shared.append(links)
        result=f'{len(rows)} file(s)'
        if bad:result+=' · '+', '.join(bad)
        if shared:result+=f' · dùng chung {max(shared)} câu'
        return result
    def switch_mode(self,index):
        self.stack.setCurrentIndex(index);self.expand_toggle.setVisible(index==1);self.sync_cards()
    def toggle_expand(self,qid):
        if qid in self.expanded_ids:self.expanded_ids.remove(qid)
        else:self.expanded_ids.add(qid)
        self.sync_cards()
    def toggle_all_expand(self):
        all_ids={q.id for q in self.w.table_model.rows}
        if self.expanded_ids:self.expanded_ids.clear()
        else:self.expanded_ids.update(all_ids)
        self.sync_cards()
    def select_single_id(self,qid):
        for i in range(self.cards.count()):
            it=self.cards.item(i)
            if it.data(Qt.ItemDataRole.UserRole)==qid:
                self.cards.setCurrentItem(it);it.setSelected(True);break
    def sync_cards(self):
        if self.mode.currentIndex()!=1:return
        selected={item.data(Qt.ItemDataRole.UserRole) for item in self.cards.selectedItems()};current=self.cards.currentItem().data(Qt.ItemDataRole.UserRole) if self.cards.currentItem() else None
        scroll_val=self.cards.verticalScrollBar().value()

        existing_ids = [self.cards.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.cards.count())]
        current_rows_ids = [q.id for q in self.w.table_model.rows]
        if existing_ids == current_rows_ids and getattr(self, '_last_synced_expanded_ids', None) == set(self.expanded_ids):
            self.cards.blockSignals(True)
            for i in range(self.cards.count()):
                it = self.cards.item(i)
                qid = it.data(Qt.ItemDataRole.UserRole)
                should_sel = qid in selected
                if it.isSelected() != should_sel:
                    it.setSelected(should_sel)
                if qid == current and self.cards.currentItem() != it:
                    self.cards.setCurrentItem(it)
            self.cards.blockSignals(False)
            return

        self._last_synced_expanded_ids = set(self.expanded_ids)
        self.cards.blockSignals(True);self.cards.clear()
        all_ids={q.id for q in self.w.table_model.rows}
        self.expand_toggle.setText('Thu gọn tất cả' if self.expanded_ids and all_ids and self.expanded_ids>=all_ids else 'Mở rộng tất cả')
        viewport_w=self.cards.viewport().width()
        card_w=max(320,(viewport_w-24) if viewport_w>50 else 450)
        for q in self.w.table_model.rows:
            is_expanded=q.id in self.expanded_ids
            parsed=parse_tex_card(q.latex_source)
            level_str=q.cognitive_level or ''
            item=QListWidgetItem(self.cards);item.setData(Qt.ItemDataRole.UserRole,q.id)
            box=QFrame();box.setObjectName('questionCard');box.setProperty('expanded','true' if is_expanded else 'false')
            if not is_expanded:
                item.setSizeHint(QSize(card_w,46))
                row=QHBoxLayout(box);row.setContentsMargins(8,4,10,4);row.setSpacing(8)
                toggle_btn=QToolButton();toggle_btn.setObjectName('expanderToggle');toggle_btn.setText('▸');toggle_btn.setToolTip('Bấm để mở rộng xem chi tiết')
                toggle_btn.clicked.connect(lambda _,qid=q.id:self.toggle_expand(qid))
                row.addWidget(toggle_btn)
                level_badge=QLabel(level_str if level_str else 'Chưa gán');level_badge.setObjectName('cardLevelBadge');level_badge.setProperty('level',level_str if level_str else 'NONE')
                row.addWidget(level_badge)
                type_badge=QLabel(TYPE_LABELS.get(q.question_type,q.question_type));type_badge.setObjectName('cardTypeBadge')
                row.addWidget(type_badge)
                stem_summary=parsed['stem'][:140]+('…' if len(parsed['stem'])>140 else '')
                stem_lbl=QLabel(stem_summary or 'Chưa có nội dung câu hỏi');stem_lbl.setObjectName('cardStemSummary');stem_lbl.setToolTip(parsed['stem'])
                row.addWidget(stem_lbl,1)
                qid_lbl=QLabel(f'#{q.id[:6]}');qid_lbl.setObjectName('cardIdLabel')
                row.addWidget(qid_lbl)
            else:
                card_layout=QVBoxLayout(box);card_layout.setContentsMargins(12,10,12,10);card_layout.setSpacing(8)
                header=QHBoxLayout();header.setContentsMargins(0,0,0,0);header.setSpacing(8)
                toggle_btn=QToolButton();toggle_btn.setObjectName('expanderToggle');toggle_btn.setText('▾');toggle_btn.setToolTip('Bấm để thu gọn')
                toggle_btn.clicked.connect(lambda _,qid=q.id:self.toggle_expand(qid))
                header.addWidget(toggle_btn)
                level_badge=QLabel(level_str if level_str else 'Chưa gán');level_badge.setObjectName('cardLevelBadge');level_badge.setProperty('level',level_str if level_str else 'NONE')
                header.addWidget(level_badge)
                type_badge=QLabel(TYPE_LABELS.get(q.question_type,q.question_type));type_badge.setObjectName('cardTypeBadge')
                header.addWidget(type_badge)
                tax_label=getattr(self.w.table_model,'classification_labels',{}).get(q.id,'')
                if tax_label and tax_label!='Chưa phân loại':
                    tax_lbl=QLabel(tax_label);tax_lbl.setObjectName('cardTaxonomyLabel');header.addWidget(tax_lbl,1)
                else:header.addStretch(1)
                qid_lbl=QLabel(f'#{q.id[:6]}');qid_lbl.setObjectName('cardIdLabel')
                header.addWidget(qid_lbl);card_layout.addLayout(header)
                stem_lbl=QLabel(parsed['stem']);stem_lbl.setObjectName('cardStemFull');stem_lbl.setWordWrap(True)
                card_layout.addWidget(stem_lbl)
                if parsed['options']:
                    opt_frame=QFrame();opt_frame.setObjectName('cardOptionGrid')
                    grid=QGridLayout(opt_frame);grid.setContentsMargins(8,6,8,6);grid.setSpacing(6)
                    for i,opt in enumerate(parsed['options']):
                        opt_text=f"{opt['label']}. {opt['text']}"+('  ✓' if opt['correct'] else '')
                        opt_lbl=QLabel(opt_text);opt_lbl.setObjectName('cardOptionText');opt_lbl.setWordWrap(True)
                        if opt['correct']:opt_lbl.setProperty('correct','true')
                        grid.addWidget(opt_lbl,i//2,i%2)
                    card_layout.addWidget(opt_frame)
                elif parsed['short_ans']:
                    ans_frame=QFrame();ans_frame.setObjectName('cardOptionGrid')
                    ans_box=QHBoxLayout(ans_frame);ans_box.setContentsMargins(8,4,8,4)
                    ans_lbl=QLabel(f"Đáp án: {parsed['short_ans']}");ans_lbl.setObjectName('cardOptionText');ans_lbl.setProperty('correct','true')
                    ans_box.addWidget(ans_lbl);card_layout.addWidget(ans_frame)
                if parsed['solution']:
                    sol_lbl=QLabel(f"💡 Lời giải: {parsed['solution']}");sol_lbl.setObjectName('cardSolutionText');sol_lbl.setWordWrap(True)
                    card_layout.addWidget(sol_lbl)
                pix = None
                if q.id in self.images and self.images[q.id][:2]==(q.revision,q.latex_source):
                    pix = self.images[q.id][2]
                elif hasattr(self.w, 'thumbnail_manager'):
                    try:
                        config = self.w.compiler_config()
                        k = self.key(q, q.latex_source, config)
                        thumb_key = hashlib.sha256(str(k).encode('utf-8')).hexdigest()
                        pix = self.w.thumbnail_manager.get_pixmap(thumb_key)
                        if pix:
                            self.images[q.id] = (q.revision, q.latex_source, pix)
                    except Exception:
                        pass
                if pix:
                    img_lbl=QLabel();img_lbl.setObjectName('cardRenderImg')
                    scaled_pix=pix.scaledToWidth(min(card_w-30,pix.width()),Qt.TransformationMode.SmoothTransformation)
                    img_lbl.setPixmap(scaled_pix);card_layout.addWidget(img_lbl)
                elif q.id in self.compile_errors:
                    err_box = QFrame(); err_box.setObjectName('cardErrorBadge')
                    err_l = QHBoxLayout(err_box); err_l.setContentsMargins(6,2,6,2); err_l.setSpacing(6)
                    err_msg = self.compile_errors[q.id]
                    err_lbl = QLabel(f"⚠️ Render lỗi: {err_msg[:60]}…")
                    err_lbl.setStyleSheet("color: #dc2626; font-size: 11px;")
                    err_lbl.setToolTip(err_msg)
                    retry_btn = QPushButton("Thử lại")
                    retry_btn.setStyleSheet("background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; border-radius: 4px; padding: 1px 6px; font-size: 11px;")
                    retry_btn.clicked.connect(lambda _,qid=q.id:(self.select_single_id(qid),self.w.ensure_preview_visible(),self.w.compile_current()))
                    err_l.addWidget(err_lbl, 1); err_l.addWidget(retry_btn)
                    card_layout.addWidget(err_box)
                else:
                    placeholder = QFrame()
                    placeholder.setObjectName('cardRenderPlaceholder')
                    ph_layout = QHBoxLayout(placeholder)
                    ph_layout.setContentsMargins(8, 14, 8, 14)
                    ph_lbl = QLabel("⏳ Đang chuẩn bị xem trước…")
                    ph_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
                    ph_layout.addWidget(ph_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                    card_layout.addWidget(placeholder)
                    if hasattr(self.w, 'render_queue'):
                        try:
                            config = self.w.compiler_config()
                            k = self.key(q, q.latex_source, config)
                            thumb_key = hashlib.sha256(str(k).encode('utf-8')).hexdigest()
                            assets = self.w.asset_map(q.id) if hasattr(self.w, 'asset_map') else {}
                            prio = RenderPriority.SELECTED if q.id == self.selected_id else RenderPriority.PREFETCH
                            self.w.render_queue.enqueue(
                                question_id=q.id,
                                revision=q.revision,
                                source=q.latex_source,
                                key=thumb_key,
                                config=config,
                                assets=assets,
                                priority=prio,
                            )
                        except Exception:
                            pass
                actions=QHBoxLayout();actions.setContentsMargins(0,4,0,0);actions.setSpacing(8)
                pv_btn=QPushButton('Xem trước');pv_btn.setObjectName('cardActionBtn')
                pv_btn.clicked.connect(lambda _,qid=q.id:(self.select_single_id(qid),self.w.ensure_preview_visible(),self.w.compile_current()))
                actions.addWidget(pv_btn)
                edit_btn=QPushButton('Sửa câu');edit_btn.setObjectName('cardActionBtn');edit_btn.clicked.connect(lambda _,qid=q.id:self.open_editor_dialog(qid))
                actions.addWidget(edit_btn)
                exam_btn=QPushButton('Lấy vào đề');exam_btn.setObjectName('cardActionBtn');exam_btn.clicked.connect(lambda _,qid=q.id:(self.select_single_id(qid),self.w.use_exam_selection(),self.w.show_page(2)))
                actions.addWidget(exam_btn)
                actions.addStretch(1)
                collapse_btn=QPushButton('Thu gọn');collapse_btn.setObjectName('cardActionBtn');collapse_btn.clicked.connect(lambda _,qid=q.id:self.toggle_expand(qid))
                actions.addWidget(collapse_btn);card_layout.addLayout(actions)
                box.adjustSize()
                item.setSizeHint(QSize(card_w,max(140,box.sizeHint().height())))
            self.cards.setItemWidget(item,box)
            if q.id in selected:item.setSelected(True)
            if q.id==current:self.cards.setCurrentItem(item)
        self.cards.verticalScrollBar().setValue(scroll_val);self.cards.blockSignals(False)

    def on_queue_thumbnail_ready(self, question_id, revision, source, pix, key):
        self.images[question_id] = (revision, source, pix)
        while len(self.images) > 40:
            self.images.pop(next(iter(self.images)))
        self.compile_errors.pop(question_id, None)
        if self.mode.currentIndex() != 1:
            return
        card_w = max(320, (self.cards.viewport().width() - 24) if self.cards.viewport().width() > 50 else 450)
        scaled_pix = pix.scaledToWidth(min(card_w - 30, pix.width()), Qt.TransformationMode.SmoothTransformation)
        for i in range(self.cards.count()):
            item = self.cards.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == question_id:
                box = self.cards.itemWidget(item)
                if not box or box.property('expanded') != 'true':
                    break
                placeholder = box.findChild(QFrame, 'cardRenderPlaceholder')
                existing_img = box.findChild(QLabel, 'cardRenderImg')
                existing_err = box.findChild(QFrame, 'cardErrorBadge')
                if existing_err:
                    box.layout().removeWidget(existing_err)
                    existing_err.deleteLater()
                if placeholder:
                    layout = box.layout()
                    idx = layout.indexOf(placeholder)
                    placeholder.hide()
                    layout.removeWidget(placeholder)
                    placeholder.deleteLater()
                    img_lbl = QLabel()
                    img_lbl.setObjectName('cardRenderImg')
                    img_lbl.setPixmap(scaled_pix)
                    layout.insertWidget(idx, img_lbl)
                elif existing_img:
                    existing_img.setPixmap(scaled_pix)
                else:
                    layout = box.layout()
                    img_lbl = QLabel()
                    img_lbl.setObjectName('cardRenderImg')
                    img_lbl.setPixmap(scaled_pix)
                    layout.insertWidget(max(0, layout.count() - 1), img_lbl)
                box.adjustSize()
                item.setSizeHint(QSize(card_w, max(140, box.sizeHint().height())))
                break

    def on_queue_thumbnail_failed(self, question_id, error_message, key):
        self.compile_errors[question_id] = error_message
        if self.mode.currentIndex() != 1:
            return
        card_w = max(320, (self.cards.viewport().width() - 24) if self.cards.viewport().width() > 50 else 450)
        for i in range(self.cards.count()):
            item = self.cards.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == question_id:
                box = self.cards.itemWidget(item)
                if not box or box.property('expanded') != 'true':
                    break
                placeholder = box.findChild(QFrame, 'cardRenderPlaceholder')
                if placeholder:
                    layout = box.layout()
                    idx = layout.indexOf(placeholder)
                    placeholder.hide()
                    layout.removeWidget(placeholder)
                    placeholder.deleteLater()
                    err_box = QFrame()
                    err_box.setObjectName('cardErrorBadge')
                    err_l = QHBoxLayout(err_box)
                    err_l.setContentsMargins(6, 2, 6, 2)
                    err_l.setSpacing(6)
                    err_lbl = QLabel(f"⚠️ Render lỗi: {error_message[:60]}…")
                    err_lbl.setStyleSheet("color: #dc2626; font-size: 11px;")
                    err_lbl.setToolTip(error_message)
                    retry_btn = QPushButton("Thử lại")
                    retry_btn.setStyleSheet("background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; border-radius: 4px; padding: 1px 6px; font-size: 11px;")
                    retry_btn.clicked.connect(lambda _, qid=question_id: (self.select_single_id(qid), self.w.ensure_preview_visible(), self.w.compile_current()))
                    err_l.addWidget(err_lbl, 1)
                    err_l.addWidget(retry_btn)
                    layout.insertWidget(idx, err_box)
                    box.adjustSize()
                    item.setSizeHint(QSize(card_w, max(140, box.sizeHint().height())))
                break

    def on_cards_scroll_settled(self):
        if not hasattr(self.w, 'render_queue') or self.mode.currentIndex() != 1:
            return
        vp_rect = self.cards.viewport().rect()
        visible_keys = set()
        config = self.w.compiler_config()
        for i in range(self.cards.count()):
            item = self.cards.item(i)
            item_rect = self.cards.visualItemRect(item)
            if item_rect.intersects(vp_rect):
                qid = item.data(Qt.ItemDataRole.UserRole)
                if qid in self.expanded_ids:
                    q = next((x for x in self.w.table_model.rows if x.id == qid), None)
                    if q:
                        k = self.key(q, q.latex_source, config)
                        thumb_key = hashlib.sha256(str(k).encode('utf-8')).hexdigest()
                        visible_keys.add(thumb_key)
        if visible_keys:
            self.w.render_queue.update_priority(visible_keys, RenderPriority.VIEWPORT)

    def card_selected(self,row):
        if 0<=row<len(self.w.table_model.rows):
            self.w.table.setCurrentIndex(self.w.table_model.index(row,0))
            self.select(row)
            q = self.w.table_model.rows[row]
            if hasattr(self.w, 'render_queue') and q.id in self.expanded_ids:
                try:
                    config = self.w.compiler_config()
                    k = self.key(q, q.latex_source, config)
                    thumb_key = hashlib.sha256(str(k).encode('utf-8')).hexdigest()
                    self.w.render_queue.update_priority({thumb_key}, RenderPriority.SELECTED)
                except Exception:
                    pass
    def ids(self):
        if self.mode.currentIndex()==1 and self.w.tabs.currentIndex()==0:return [i.data(Qt.ItemDataRole.UserRole) for i in self.cards.selectedItems()]
        return self.w.selected_exam_ids()

    def update_batch_bar(self):
        selected_ids = self.ids()
        count = len(selected_ids)
        if count > 0:
            self.batch_count_lbl.setText(f"Đã chọn <b>{count}</b> câu hỏi:")
            self.batch_bar.show()
        else:
            self.batch_bar.hide()

    def clear_selection(self):
        self.cards.clearSelection()
        self.w.table.clearSelection()
        self.update_batch_bar()

    def batch_change_level(self):
        selected_ids = self.ids()
        if not selected_ids:
            QMessageBox.information(self.w, "Chưa chọn câu", "Vui lòng chọn ít nhất một câu hỏi để đổi mức độ.")
            return
        levels = [('Nhận biết (NB)', 'NB'), ('Thông hiểu (TH)', 'TH'), ('Vận dụng (VD)', 'VD'), ('Vận dụng cao (VDC)', 'VDC')]
        labels = [l[0] for l in levels]
        chosen, ok = QInputDialog.getItem(self.w, "Đổi mức độ nhận thức", f"Chọn mức độ mới cho {len(selected_ids)} câu hỏi đã chọn:", labels, 0, False)
        if not ok: return
        new_lvl = next(l[1] for l in levels if l[0] == chosen)
        try:
            for qid in selected_ids:
                LibraryService(self.w.services).save_metadata(qid, {'cognitive_level': new_lvl})
            self.w.refresh_status()
            self.w.statusBar().showMessage(f"Đã đổi mức độ {len(selected_ids)} câu thành: {chosen}")
        except Exception as error:
            QMessageBox.warning(self.w, "Lỗi đổi mức độ", str(error))

    def select_single_id(self, qid):
        for i in range(self.cards.count()):
            item = self.cards.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == qid:
                self.cards.setCurrentItem(item)
                break
        self.selected_id = qid

    def open_editor_dialog(self, qid):
        from latex_question_studio.ui.question_editor_dialog import QuestionEditorDialog
        dlg = QuestionEditorDialog(qid, self.w.services, parent=self.w)
        dlg.question_saved.connect(self.on_question_saved)
        dlg.exec()

    def on_question_saved(self, qid):
        self.w.refresh_status()
        self.sync_cards()
        self.w.compile_current()
        self.w.statusBar().showMessage(f"Đã cập nhật câu hỏi #{qid[:8]}.")

    def preview_action(self):
        if not self.selected_id:
            if self.mode.currentIndex()==1 and self.cards.count()>0:
                self.cards.setCurrentRow(max(0,self.cards.currentRow()))
            elif len(self.w.table_model.rows)>0:
                self.w.table.selectRow(max(0,self.w.table.currentIndex().row()))
        self.w.ensure_preview_visible()
        self.w.compile_current()

    def edit(self):
        if not self.selected_id:
            if self.mode.currentIndex()==1 and self.cards.count()>0:
                self.cards.setCurrentRow(max(0,self.cards.currentRow()))
            elif len(self.w.table_model.rows)>0:
                self.w.table.selectRow(max(0,self.w.table.currentIndex().row()))
        q=self.current_question()
        if q:
            self.open_editor_dialog(q.id)
    def copy(self):
        for qid in self.ids():
            q=self.w.services.questions.get(qid)
            new=self.w.services.questions.create(q.latex_source)
            m=LibraryService(self.w.services).metadata(qid);m.pop('archived',None)
            LibraryService(self.w.services).save_metadata(new.id,{**m,'question_type':q.question_type,'cognitive_level':q.cognitive_level})
        self.w.refresh_status()
    def archive(self):
        from PySide6.QtWidgets import QMessageBox
        ids=self.ids()
        if not ids:return
        if QMessageBox.question(self.w,'Lưu trữ',f'Lưu trữ {len(ids)} câu, giữ dữ liệu và lịch sử?')!=QMessageBox.StandardButton.Yes:return
        for editor,q in list(self.w.editors.items()):
            if q.id in ids and editor.document().isModified():
                self.w.tabs.setCurrentWidget(editor)
                if not self.w.save_question_editor():return
        for qid in ids:LibraryService(self.w.services).save_metadata(qid,{'archived':True})
        for editor,q in list(self.w.editors.items()):
            if q.id in ids:
                self.w.editors[editor]=self.w.services.questions.get(q.id);self.w.close_tab(self.w.tabs.indexOf(editor))
        self.w.refresh_status()
    def key(self,q,source,config):
        # Include references and revision. Compiler retains the authoritative disk cache.
        from pathlib import Path
        with self.w.services.database.connect() as c:
            paths=[self.w.services.config.data_dir/r[0] for r in c.execute('SELECT a.relative_path FROM question_assets qa JOIN assets a ON a.id=qa.asset_id WHERE qa.question_id=?',(q.id,))]
        if config.get('preamble_file'):paths.append(Path(config['preamble_file']))
        signatures=tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) if p.exists() else (str(p),None,None) for p in paths)
        from latex_question_studio.preview.compiler import Compiler
        try:
            preamble,dependencies=Compiler(self.w.services.config.data_dir,preamble_file=config.get('preamble_file') or None).profile()
            profile_signature=(preamble,tuple(sorted(dependencies.items())))
        except (ValueError,OSError) as error:
            profile_signature=str(error)
        return q.id,q.revision,source,json.dumps(config,sort_keys=True),signatures,profile_signature
    def cached(self,q,source,config):
        k = self.key(q,source,config)
        if k in self.cache:
            return self.cache[k]
        if hasattr(self.w, 'thumbnail_manager'):
            try:
                import hashlib
                thumb_key = hashlib.sha256(str(k).encode('utf-8')).hexdigest()
                res = self.w.thumbnail_manager.get(thumb_key)
                if res:
                    data, fmt, path = res
                    from latex_question_studio.preview.compiler import CompileResult
                    result = CompileResult(True, None, f"Thumbnail từ disk cache ({fmt.upper()}).", cache_hit=True)
                    return (result, data, 1)
            except Exception:
                pass
        return None

    def remember(self,q,source,config,result,image,pages):
        key=self.key(q,source,config);self.cache[key]=(result,image,pages);self.cache.move_to_end(key)
        while len(self.cache)>40:self.cache.popitem(last=False)
        pix=QPixmap();pix.loadFromData(image);self.images[q.id]=(q.revision,source,pix)
        while len(self.images)>40:self.images.pop(next(iter(self.images)))
        if hasattr(self.w, 'thumbnail_manager') and image:
            try:
                import hashlib
                thumb_key = hashlib.sha256(str(key).encode('utf-8')).hexdigest()
                self.w.thumbnail_manager.save(thumb_key, image, prefer_webp=True)
            except Exception:
                pass
        if self.mode.currentIndex()==1:self.sync_cards()
    def display_image(self,image):
        pix=QPixmap();pix.loadFromData(image);self.original=pix;self.fit()
    def fit(self):
        if self.original:
            width=max(100,self.scroll.viewport().width()-12);self.w.preview.setMinimumSize(0,0);self.w.preview.setPixmap(self.original.scaledToWidth(min(width,self.original.width()),Qt.TransformationMode.SmoothTransformation))

    def goto_error(self):
        editor=self.w.tabs.currentWidget()
        if editor not in self.w.editors:return
        match=re.search(r'(?:l\.|line\s+)(\d+)',self.errors.toPlainText())
        if not match:return
        from latex_question_studio.preview.compiler import Compiler
        config=self.w.compiler_config()
        try:preamble,_=Compiler(self.w.services.config.data_dir,preamble_file=config.get('preamble_file') or None).profile()
        except (ValueError,OSError):return
        line=int(match.group(1))-(preamble.count('\n')+2)
        if not 1<=line<=editor.blockCount():
            self.w.statusBar().showMessage('Lỗi thuộc preamble / tệp phụ; chưa xác định dòng trong câu.');return
        block=editor.document().findBlockByNumber(line-1)
        if block.isValid():
            from PySide6.QtGui import QTextCursor
            editor.setTextCursor(QTextCursor(block));editor.setFocus();editor.centerCursor()
    def update_tasks(self):
        from shiboken6 import isValid
        if not isValid(self.tasks):return
        self.tasks.setPlainText('\n'.join(f'Tác vụ {i+1} · '+('Đang hủy' if job.cancelled.is_set() else 'Đang chạy') for i,job in enumerate(self.w.all_jobs)) or 'Không có tác vụ đang chạy.')

    def editor_text_changed(self,editor):
        if self.w.tabs.currentWidget() is not editor:return
        self.preview_timer.stop();self.w.cancel_preview();self.w.preview_generation+=1
        self.source.setPlainText(editor.toPlainText());self.original=None;self.w.preview.clear();self.w.preview.setText('Có thay đổi chưa biên dịch · F5 để cập nhật.');self.w.preview.setMinimumSize(0,0)

    def update_table_details(self):
        ids=[q.id for q in self.w.table_model.rows];labels={}
        if ids:
            with self.w.services.database.connect() as c:
                records=c.execute('SELECT question_id,data_json FROM question_metadata WHERE question_id IN ('+','.join('?' for _ in ids)+')',ids)
                for record in records:
                    m=json.loads(record['data_json']);labels[record['question_id']]=breadcrumb(self.nodes,m.get('taxonomy_id')) or m.get('topic') or m.get('lesson') or 'Chưa phân loại'
        self.w.table_model.classification_labels=labels
        if ids:self.w.table_model.dataChanged.emit(self.w.table_model.index(0,0),self.w.table_model.index(len(ids)-1,3))

    def update_scope(self,count):
        scope=breadcrumb(self.nodes,getattr(self.w,'selected_taxonomy',None)) or 'Toàn bộ CSDL'
        self.scope_label.setText('Phạm vi: '+scope)
        self.empty_hint.setVisible(count==0);self.all_button.setVisible(count==0)
        self.empty_hint.setText('Không có câu hỏi trong phạm vi hoặc bộ lọc đang chọn. Nhấn Xem tất cả câu để tìm câu chưa phân loại.')

    def show_all(self):
        self.w.tabs.setCurrentIndex(0);self.w.explorer.setCurrentItem(self.w.root_node);self.reset_filters()
