"""Library presentation and inspector. Persistence/compilation reuse existing APIs."""
from collections import OrderedDict
import json,re
from PySide6.QtCore import Qt,QTimer,QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QComboBox,QTabWidget,QPlainTextEdit,QFormLayout,QPushButton,QListWidget,QListWidgetItem,QLabel,QStackedWidget,QHeaderView,QScrollArea)
from latex_question_studio.ui.components.workspace import CommandToolbar
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.search import SearchService
from latex_question_studio.persistence.questions import QuestionRepository
from latex_question_studio.domain.curriculum import classification,breadcrumb
TYPE_LABELS={'mcq':'Trắc nghiệm','true_false':'Đúng / sai','essay':'Tự luận','short_answer':'Trả lời ngắn','unknown':'Chưa xác định'}

def readable(source):
    # Display summary only. Never feed this transformed text to parser/export.
    s=re.sub(r'(?m)%[^\n]*','',source)
    s=re.split(r'\\(?:choiceTFt?|choice|shortans|loigiai|hdan)\b',s,maxsplit=1)[0]
    s=re.sub(r'\\(?:begin|end)\{[^}]*\}','',s)
    s=re.sub(r'\\(?:choiceTFt?|choice|loigiai|True|shortans)\b',' ',s)
    return re.sub(r'\s+',' ',s).strip()

class LibraryWorkspace:
    def __init__(self,w,library,scroll):
        self.w=w;self.cache=OrderedDict();self.images={};self.original=None;self.scroll=scroll;self.selected_id=None;self.loading=False
        layout=library.layout();layout.setContentsMargins(8,8,8,8);layout.setSpacing(6)
        self.toolbar=CommandToolbar('Thư viện',w.library_control)
        frame=QWidget();outer=QVBoxLayout(frame);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0);outer.addWidget(self.toolbar);outer.addWidget(w.library_vertical,1);w.library_control.setCentralWidget(frame)
        self.toolbar.command('import','Nhập TeX',lambda:w.show_page(1),True)
        self.toolbar.command('topic','Câu mới',w.new_question)
        self.toolbar.command('lesson','Sửa câu',self.edit)
        self.toolbar.command('subject','Phân loại',w.edit_metadata)
        self.toolbar.command('preview','Xem trước',w.compile_current,True)
        self.toolbar.command('save','Lưu câu · Ctrl+S',w.save_current)
        self.toolbar.addSeparator()
        self.toolbar.command('bank','Lấy vào đề',lambda:(w.use_exam_selection(),w.show_page(2)))
        from PySide6.QtWidgets import QToolButton,QMenu
        more=QToolButton();more.setText('Thao tác khác');more.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        menu=QMenu(more);menu.addAction('Sao chép câu đã chọn',self.copy);menu.addAction('Lưu trữ câu đã chọn',self.archive)
        menu.addAction('Trang trước · Alt+Left',w.previous_page);menu.addAction('Trang tiếp · Alt+Right',w.next_page)
        menu.addAction('Đi tới dòng lỗi LaTeX',self.goto_error);menu.addAction('Mở / ẩn nhật ký',w.log_dock.toggleViewAction().trigger)
        more.setMenu(menu);more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup);self.toolbar.addWidget(more)
        for action in self.toolbar.actions():
            button=self.toolbar.widgetForAction(action)
            if hasattr(button,'setToolButtonStyle'):button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.scope_label=QLabel('Phạm vi: Toàn bộ CSDL');self.scope_label.setWordWrap(True)
        self.guide=QLabel('1. Chọn bài / dạng bên trái   →   2. Chọn câu ở giữa   →   3. Xem trước hoặc sửa / phân loại')
        self.guide.setWordWrap(True);outer.insertWidget(1,self.guide)
        row=QHBoxLayout();self.query=QLineEdit();self.query.setPlaceholderText('Tìm nhanh nội dung, nguồn hoặc nhãn…');self.query.setClearButtonEnabled(True);layout.insertWidget(0,self.scope_label);layout.insertWidget(1,self.query)
        self.kind=QComboBox();self.kind.addItem('Mọi loại','')
        for key,label in TYPE_LABELS.items():self.kind.addItem(label,key)
        self.level=QComboBox();self.level.addItem('Mọi mức độ','')
        for key,label in [('NB','Nhận biết'),('TH','Thông hiểu'),('VD','Vận dụng'),('VDC','Vận dụng cao')]:self.level.addItem(label,key)
        self.state=QComboBox()
        for label,key in [('Đang sử dụng','active'),('Chưa phân loại','unclassified'),('Source lỗi','invalid'),('Đã lưu trữ','archived')]:self.state.addItem(label,key)
        self.mode=QComboBox();self.mode.addItems(['Danh sách gọn','Thẻ preview'])
        for combo in (self.kind,self.level,self.state,self.mode):row.addWidget(combo)
        layout.insertLayout(2,row)
        layout.removeWidget(w.table);self.stack=QStackedWidget();self.stack.addWidget(w.table)
        self.cards=QListWidget();self.cards.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection);self.stack.addWidget(self.cards);layout.insertWidget(4,self.stack,1)
        w.table.setSelectionMode(w.table.SelectionMode.ExtendedSelection);w.table.setWordWrap(False)
        w.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);w.table.setColumnWidth(1,95);w.table.setColumnWidth(2,75);w.table.setColumnWidth(3,140)
        w.table.verticalHeader().setDefaultSectionSize(35)
        self.cards.currentRowChanged.connect(self.card_selected);self.cards.itemDoubleClicked.connect(lambda *a:self.edit())
        w.table.selectionModel().currentRowChanged.connect(lambda current,old:self.select(current.row()))
        self.timer=QTimer(w);self.timer.setSingleShot(True);self.timer.setInterval(250);self.timer.timeout.connect(self.filters_changed)
        self.preview_timer=QTimer(w);self.preview_timer.setSingleShot(True);self.preview_timer.setInterval(250);self.preview_timer.timeout.connect(w.compile_current)
        self.query.textChanged.connect(lambda *a:self.timer.start())
        for combo in (self.kind,self.level,self.state):combo.currentIndexChanged.connect(self.filters_changed)
        self.mode.currentIndexChanged.connect(self.switch_mode)
        w.refresh_button.hide()
        self.inspector=QTabWidget();w.preview_dock.layout().replaceWidget(scroll,self.inspector);self.inspector.addTab(scroll,'Xem trước')
        metadata=QWidget();form=QFormLayout(metadata);self.meta_title=QLabel('Chọn câu hỏi');self.meta_title.setWordWrap(True);form.addRow(self.meta_title)
        self.taxonomy=QComboBox();self.taxonomy.setMinimumContentsLength(15);self.taxonomy.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);self.taxonomy.addItem('Chưa phân loại',None)
        nodes=LibraryService(w.services).taxonomy();self.nodes=nodes
        for n in nodes:
            if n['kind'] in ('lesson','topic'):self.taxonomy.addItem(breadcrumb(nodes,n['id']),n['id'])
        form.addRow('Bài / dạng',self.taxonomy)
        self.meta_level=QComboBox()
        for label,key in [('Chưa gán',''),('Nhận biết','NB'),('Thông hiểu','TH'),('Vận dụng','VD'),('Vận dụng cao','VDC')]:self.meta_level.addItem(label,key)
        form.addRow('Mức độ',self.meta_level);self.tags=QLineEdit();form.addRow('Nhãn',self.tags);self.origin=QLineEdit();form.addRow('Nguồn',self.origin)
        save=QPushButton('Lưu phân loại');save.setProperty('primary',True);save.clicked.connect(self.save_metadata);form.addRow(save)
        self.inspector.addTab(metadata,'Phân loại');self.source=QPlainTextEdit();self.source.setReadOnly(True);self.inspector.addTab(self.source,'Mã LaTeX');self.errors=QPlainTextEdit();self.errors.setReadOnly(True);self.inspector.addTab(self.errors,'Lỗi / nhật ký')
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
        self.toolbar.command('chapter','Cây CSDL',w.ensure_library_tree)
        self.toolbar.widgetForAction(self.toolbar.actions()[-1]).setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
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
            if self.w.pages.currentIndex()==0 and self.w.tabs.currentIndex()==0:self.preview_timer.start()
        else:self.source.clear();self.w.preview.setText('Chọn câu để xem trước.');self.meta_title.setText('Chọn câu hỏi')
    def load_metadata(self,q):
        m=LibraryService(self.w.services).metadata(q.id)
        self.taxonomy.setCurrentIndex(max(0,self.taxonomy.findData(m.get('taxonomy_id'))));self.meta_level.setCurrentIndex(max(0,self.meta_level.findData(q.cognitive_level or '')))
        self.tags.setText(', '.join(m.get('tags',[])));self.origin.setText(m.get('source',''));self.meta_title.setText(f'{TYPE_LABELS.get(q.question_type,q.question_type)} • Phiên bản {q.revision} • {q.id[:8]}')
    def save_metadata(self):
        q=self.current_question()
        if not q:return
        values=classification(self.nodes,self.taxonomy.currentData());values.update(taxonomy_id=self.taxonomy.currentData(),cognitive_level=self.meta_level.currentData() or None,tags=[x.strip() for x in self.tags.text().split(',') if x.strip()],source=self.origin.text().strip())
        try:
            LibraryService(self.w.services).save_metadata(q.id,values)
            for editor,old in self.w.editors.items():
                if old.id==q.id:self.w.editors[editor]=self.w.services.questions.get(q.id)
            self.w.refresh_status();self.w.statusBar().showMessage('Đã lưu phân loại')
        except Exception as error:self.errors.setPlainText(str(error));self.inspector.setCurrentWidget(self.errors)
    def filters_changed(self,*args):
        self.w.search_text=self.query.text();self.w.search_filters={'question_type':self.kind.currentData(),'cognitive_level':self.level.currentData()};self.w.offset=0;self.w.refresh_status(refresh_tree=False)
    def reset_filters(self):
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
        sql=('SELECT count(*)' if count_only else 'SELECT q.*')+' FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id'+join+' WHERE '+' AND '.join(where)
        if not count_only:sql+=' ORDER BY '+('bm25(questions_fts),q.id' if join else 'q.created_at,q.id')+' LIMIT ? OFFSET ?';args+=[100,w.offset]
        with w.services.database.connect() as c:
            return c.execute(sql,args).fetchone()[0] if count_only else [QuestionRepository._question(r) for r in c.execute(sql,args)]
    def switch_mode(self,index):
        self.stack.setCurrentIndex(index);self.sync_cards()
    def sync_cards(self):
        if self.mode.currentIndex()!=1:return
        selected={item.data(Qt.ItemDataRole.UserRole) for item in self.cards.selectedItems()};current=self.cards.currentItem().data(Qt.ItemDataRole.UserRole) if self.cards.currentItem() else None
        self.cards.blockSignals(True);self.cards.clear()
        for q in self.w.table_model.rows:
            item=QListWidgetItem(self.cards);item.setData(Qt.ItemDataRole.UserRole,q.id);item.setSizeHint(QSize(200,180));box=QWidget();layout=QVBoxLayout(box)
            title=QLabel(f'{TYPE_LABELS.get(q.question_type,q.question_type)} • {q.cognitive_level or "Chưa gán mức độ"} • {q.id[:8]}');layout.addWidget(title)
            label=QLabel();label.setWordWrap(True)
            if q.id in self.images and self.images[q.id][:2]==(q.revision,q.latex_source):label.setPixmap(self.images[q.id][2].scaled(QSize(max(100,self.cards.viewport().width()-30),125),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
            else:label.setText(readable(q.latex_source)[:240]+'\nChọn thẻ để tải bản render toán học.');label.setToolTip(q.latex_source)
            layout.addWidget(label,1);self.cards.setItemWidget(item,box)
            if q.id in selected:item.setSelected(True)
            if q.id==current:self.cards.setCurrentItem(item)
        self.cards.blockSignals(False)
    def card_selected(self,row):
        if 0<=row<len(self.w.table_model.rows):self.w.table.setCurrentIndex(self.w.table_model.index(row,0));self.select(row)
    def ids(self):
        if self.mode.currentIndex()==1 and self.w.tabs.currentIndex()==0:return [i.data(Qt.ItemDataRole.UserRole) for i in self.cards.selectedItems()]
        return self.w.selected_exam_ids()
    def edit(self):
        q=self.current_question()
        if q:self.w.open_question(q.id)
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
    def cached(self,q,source,config):return self.cache.get(self.key(q,source,config))
    def remember(self,q,source,config,result,image,pages):
        key=self.key(q,source,config);self.cache[key]=(result,image,pages);self.cache.move_to_end(key)
        while len(self.cache)>40:self.cache.popitem(last=False)
        pix=QPixmap();pix.loadFromData(image);self.images[q.id]=(q.revision,source,pix)
        while len(self.images)>40:self.images.pop(next(iter(self.images)))
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
        self.empty_hint.setText('Không có câu trong phạm vi / bộ lọc này. Chọn Nhập TeX để thêm câu, hoặc Xem tất cả câu để tìm câu chưa phân loại.')

    def show_all(self):
        self.w.tabs.setCurrentIndex(0);self.w.explorer.setCurrentItem(self.w.root_node);self.reset_filters()
