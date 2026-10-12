from PySide6.QtCore import Qt, Signal,QTimer,QThreadPool,QEvent
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QSplitter,QTreeWidget,QTreeWidgetItem,QTableWidget,QTableWidgetItem,QPlainTextEdit,QPushButton,QLabel,QComboBox,QLineEdit,QMessageBox,QInputDialog,QToolBar,QTabWidget,QScrollArea,QListWidget,QListWidgetItem,QFileDialog,QMenu
from PySide6.QtGui import QPixmap
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.library import LibraryService
from latex_question_studio.domain.curriculum import breadcrumb
from latex_question_studio.ui.icons import icon

class ImportReview(QWidget):
    accepted=Signal()
    rejected=Signal()
    def __init__(self,results,parent=None,services=None):
        super().__init__(parent);self.results=results;self.services=services;self.page_offset=0;self.page_size=200;self.visible_indices=[];self.excluded_ids=set();self.rendering_rows=False
        self.setWindowTitle('Duyệt nhập và phân loại câu hỏi')
        layout=QVBoxLayout(self)
        self.preview_generation=0;self.preview_job=None;self.preview_pages=[];self.preview_index=0
        self.preview_timer=QTimer(self);self.preview_timer.setSingleShot(True);self.preview_timer.setInterval(200);self.preview_timer.timeout.connect(self.compile_preview)
        self.toolbar=QToolBar('Phân loại và nhập',self);self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly);layout.addWidget(self.toolbar)
        def action(name,text,callback):
            result=self.toolbar.addAction(icon(name,'#4ba3eb'),text);result.setToolTip(text);result.triggered.connect(callback);return result
        action('topic','Thêm dạng dưới bài đang chọn',self.add_topic)
        self.level=QComboBox();self.level.setToolTip('Mức độ nhận thức để gán cho câu đã chọn')
        for label,value in [('Chưa gán mức độ',None),('Nhận biết','NB'),('Thông hiểu','TH'),('Vận dụng','VD'),('Vận dụng cao','VDC')]:self.level.addItem(label,value)
        self.toolbar.addWidget(self.level).setToolTip(self.level.toolTip())
        action('subject','Gán bài/dạng và mức độ cho câu đã chọn',self.assign_selected)
        action('chapter','Gán bài/dạng và mức độ cho toàn bộ danh sách',lambda:self.assign_rows(list(range(len(self.results)))))
        self.toolbar.addSeparator()
        self.previous_action=action('chapter','Trang câu hỏi trước',lambda:self.change_page(-1))
        self.next_action=action('subject','Trang câu hỏi tiếp',lambda:self.change_page(1))
        self.page_label=QLabel();self.toolbar.addWidget(self.page_label).setToolTip('Duyệt danh sách nhập: tối đa 200 câu mỗi trang')
        self.toolbar.addSeparator();action('preview','Biên dịch lại preview câu đang chọn',self.compile_preview)
        action('import','Chọn lại ảnh/tài nguyên đang chọn',self.choose_asset)
        action('chapter','Thêm thư mục tìm kiếm tài nguyên',self.add_search_dir)
        self.confirm_action=action('save','Nhập câu đã chọn',self.accepted.emit)
        self.confirm_action.setProperty('primary',True)
        self.toolbar.widgetForAction(self.confirm_action).setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon);self.toolbar.widgetForAction(self.confirm_action).setProperty('primary',True)
        action('close','Đóng duyệt nhập, giữ phân loại trong hàng chờ',self.rejected.emit)
        self.table_placeholder=None
        errors=sum(bool(r['errors']) for r in results)
        from latex_question_studio.ui.import_workflow import StatsStrip
        self.stats_strip=StatsStrip();layout.addWidget(self.stats_strip);self.summary=QLabel();layout.addWidget(self.summary)
        from latex_question_studio.ui.components.workspace import Workspace
        split=Workspace("importSplit");self.workspace=split;layout.addWidget(split,1)
        left=QWidget();box=QVBoxLayout(left);self.tree_search=QLineEdit();self.tree_search.setPlaceholderText('Tìm môn, bài, dạng…');box.addWidget(self.tree_search)
        self.tree=QTreeWidget();self.tree.setHeaderLabel('CSDL • Môn → Chương → Bài → Dạng');self.tree.setExpandsOnDoubleClick(True);box.addWidget(self.tree)
        split.addWidget(left)
        center=QWidget();box=QVBoxLayout(center)
        self.only_missing=QComboBox();self.only_missing.addItems(['Tất cả câu','Chưa gán bài','Chưa gán dạng','Chưa gán mức độ','Chỉ câu hợp lệ','Chỉ câu có lỗi','Chỉ câu thiếu tài nguyên','Chỉ câu gợi ý trùng']);box.addWidget(self.only_missing)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(['Tệp / câu','Loại','Bài / dạng','Mức độ','Trạng thái','Lỗi / gợi ý trùng'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.table.horizontalHeader().setStretchLastSection(True);self.table.setColumnWidth(0,155);self.table.setColumnWidth(2,250);box.addWidget(self.table)
        from PySide6.QtWidgets import QHeaderView
        self.table.horizontalHeader().setStretchLastSection(False);self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        for column,width in [(0,105),(1,85),(3,65),(4,120),(5,170)]:self.table.setColumnWidth(column,width)
        self.table.setWordWrap(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.inclusion_menu)
        split.addWidget(center)
        right=QWidget();box=QVBoxLayout(right);self.details=QLabel('Chọn câu để xem preview và phân loại');self.details.setWordWrap(True);box.addWidget(self.details)
        self.resource_list=QListWidget();self.resource_list.setMinimumHeight(80);self.resource_list.setToolTip('Tài nguyên được phát hiện trong câu đang chọn');box.addWidget(self.resource_list)
        self.preview_tabs=QTabWidget();box.addWidget(self.preview_tabs)
        preview_panel=QWidget();pv=QVBoxLayout(preview_panel);pv.setContentsMargins(0,0,0,0)
        self.preview_status=QLabel('Chọn câu để xem preview');self.preview_status.setWordWrap(True);pv.addWidget(self.preview_status)
        self.preview_scroll=QScrollArea();self.preview_scroll.setWidgetResizable(True);self.preview_scroll.viewport().installEventFilter(self);self.preview_image=QLabel();self.preview_image.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft);self.preview_scroll.setWidget(self.preview_image);pv.addWidget(self.preview_scroll,1)
        navigation=QHBoxLayout();previous=QPushButton('‹');previous.setToolTip('Trang preview trước');previous.clicked.connect(lambda:self.show_preview_page(self.preview_index-1));navigation.addWidget(previous)
        self.preview_page_label=QLabel('0 / 0');navigation.addWidget(self.preview_page_label);following=QPushButton('›');following.setToolTip('Trang preview sau');following.clicked.connect(lambda:self.show_preview_page(self.preview_index+1));navigation.addWidget(following);pv.addLayout(navigation)
        self.preview_tabs.addTab(preview_panel,'Xem trước')
        source_panel=QWidget();sp_box=QVBoxLayout(source_panel);sp_box.setContentsMargins(4,4,4,4);sp_box.setSpacing(4)
        sp_top=QHBoxLayout();sp_top.addWidget(QLabel('Mã LaTeX của câu:'),1)
        self.repair_source_btn=QPushButton('Lưu & Phân tích lại');self.repair_source_btn.setProperty('primary',True);self.repair_source_btn.setToolTip('Lưu và phân tích lại mã LaTeX cho câu này');self.repair_source_btn.clicked.connect(self.repair_current_question);sp_top.addWidget(self.repair_source_btn)
        sp_box.addLayout(sp_top)
        self.source=QPlainTextEdit();self.source.setPlaceholderText('Mã LaTeX của câu hỏi...');sp_box.addWidget(self.source,1)
        self.preview_tabs.addTab(source_panel,'Mã LaTeX')
        split.addWidget(right);split.setSizes([280,580,500])
        self.table.currentCellChanged.connect(self.show_source);self.only_missing.currentIndexChanged.connect(self.filter_changed);self.tree_search.textChanged.connect(self.filter_tree)
        self.table.itemChanged.connect(self.inclusion_changed)
        self.refresh_tree();self.refresh_rows()
        self.update_stats()
        if results:self.table.setCurrentCell(0,0)

    def update_stats(self):
        total=len(self.results);errors=sum(bool(r.get('errors')) for r in self.results);missing=sum('MISSING_ASSET' in e.get('message','') or 'AMBIGUOUS_ASSET' in e.get('message','') for r in self.results for e in r.get('errors',[]));self.stats_strip.set_values(total,total-errors,missing,errors-missing)

    def inclusion_menu(self,position):
        menu=QMenu(self.table)
        action=menu.addAction('Bỏ / chọn lại các câu đang chọn',self.toggle_inclusion)
        action.setEnabled(bool(self.table.selectionModel().selectedRows()))
        menu.addSeparator()
        menu.addAction('Chọn tất cả các câu',self.select_all_rows)
        menu.addAction('Bỏ chọn tất cả',self.deselect_all_rows)
        menu.addAction('Chỉ chọn các câu hợp lệ (sẵn sàng)',self.select_valid_only)
        menu.addAction('Bỏ chọn các câu gợi ý trùng',self.deselect_duplicates)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def select_all_rows(self):
        self.excluded_ids.clear();self.refresh_rows()

    def deselect_all_rows(self):
        self.excluded_ids.update(r['id'] for r in self.results);self.refresh_rows()

    def select_valid_only(self):
        self.excluded_ids.clear()
        for r in self.results:
            if self.status_for(r)!='READY' or r.get('duplicate') or r.get('parsed',{}).get('duplicate_suggestion'):
                self.excluded_ids.add(r['id'])
        self.refresh_rows()

    def deselect_duplicates(self):
        for r in self.results:
            if r.get('duplicate') or r.get('parsed',{}).get('duplicate_suggestion'):
                self.excluded_ids.add(r['id'])
        self.refresh_rows()

    def repair_current_question(self):
        record=self._selected_record()
        if not record or not self.services:return
        new_source=self.source.toPlainText()
        if not new_source.strip():
            QMessageBox.warning(self,'Lỗi','Mã LaTeX không được để trống.');return
        try:
            from latex_question_studio.application.importing import ImportService, detect_cognitive_level
            errors=ImportService(self.services).repair(record['id'],new_source)
            record['source']=new_source
            record['errors']=errors
            detected=detect_cognitive_level(new_source)
            if detected:
                record['parsed'].setdefault('classification',{})['cognitive_level']=detected
            from latex_question_studio.parsing.latex import parse_questions
            parsed_items=parse_questions(new_source)
            if parsed_items:
                record['parsed']['type']=parsed_items[0].question_type
                record['parsed']['solution']=parsed_items[0].solution
            self.refresh_rows()
            self.show_source(self.table.currentRow())
            self.compile_preview()
            if errors:
                QMessageBox.information(self,'Còn lỗi','; '.join(e['message'] for e in errors))
            else:
                self.summary.setText('Đã cập nhật câu hỏi thành công.')
        except Exception as error:
            QMessageBox.warning(self,'Không thể sửa',str(error))

    def refresh_tree(self,selected=None):
        self.nodes=LibraryService(self.services).taxonomy() if self.services else []
        self.tree.clear();self.items={}
        icons={kind:icon(name,color) for kind,name,color in [('subject','subject','#4ba3eb'),('grade','subject','#4ba3eb'),('chapter','chapter','#e7ad4b'),('lesson','topic','#55bca3'),('topic','topic','#55bca3')]}
        for node in self.nodes:
            item=QTreeWidgetItem([node['name']]);item.setData(0,Qt.ItemDataRole.UserRole,node['id']);item.setIcon(0,icons.get(node['kind'],icons['topic']));item.setToolTip(0,breadcrumb(self.nodes,node['id']));self.items[node['id']]=item
        for node in self.nodes:
            item=self.items[node['id']];parent=self.items.get(node['parent_id'])
            if parent:parent.addChild(item)
            else:self.tree.addTopLevelItem(item)
        if selected in self.items:
            item=self.items[selected];self.tree.setCurrentItem(item)
            while item:item.setExpanded(True);item=item.parent()
        self.filter_tree(self.tree_search.text())

    def filter_tree(self,text):
        text=text.casefold().strip()
        for node in self.nodes:
            item=self.items[node['id']];match=not text or text in breadcrumb(self.nodes,node['id']).casefold();item.setHidden(not match)
            if match and text:
                parent=item.parent()
                while parent:parent.setHidden(False);parent.setExpanded(True);parent=parent.parent()

    def filter_changed(self,*args):
        self.page_offset=0;self.refresh_rows()

    def change_page(self,direction):
        self.page_offset=max(0,self.page_offset+direction*self.page_size);self.refresh_rows()

    def refresh_rows(self,*args):
        eligible=[]
        for i,r in enumerate(self.results):
            values=r['parsed'].get('classification',{})
            conds=[True,not values.get('lesson'),not values.get('topic'),not values.get('cognitive_level'),self.status_for(r)=='READY',bool(r.get('errors')),self.status_for(r) in ('MISSING_ASSET','AMBIGUOUS_ASSET'),bool(r.get('duplicate') or r.get('parsed',{}).get('duplicate_suggestion'))]
            idx=self.only_missing.currentIndex()
            if conds[idx] if 0<=idx<len(conds) else True:eligible.append(i)
        if self.page_offset>=len(eligible):self.page_offset=max(0,((len(eligible)-1)//self.page_size)*self.page_size)
        self.visible_indices=eligible[self.page_offset:self.page_offset+self.page_size]
        self.rendering_rows=True
        self.table.setRowCount(len(self.visible_indices))
        for row,i in enumerate(self.visible_indices):
            r=self.results[i];values=r['parsed'].get('classification',{});label=breadcrumb(self.nodes,values.get('taxonomy_id'))
            texts=[f"{__import__('pathlib').Path(r['path']).name} • câu {i+1}",{'mcq':'Trắc nghiệm','essay':'Tự luận','short_answer':'Trả lời ngắn','true_false':'Đúng / sai'}.get(r['parsed'].get('type'),'Chưa xác định'),label or 'Chưa gán',values.get('cognitive_level') or 'Chưa gán',self.status_for(r),'; '.join(e['message'] for e in r['errors'])+(' • Gợi ý trùng' if r.get('duplicate',r['parsed'].get('duplicate_suggestion')) else '')]
            for j,text in enumerate(texts):self.table.setItem(row,j,QTableWidgetItem(text));self.table.item(row,j).setToolTip(text)
            check=self.table.item(row,0);check.setFlags(check.flags()|Qt.ItemFlag.ItemIsUserCheckable);check.setCheckState(Qt.CheckState.Unchecked if r['id'] in self.excluded_ids else Qt.CheckState.Checked)
        self.rendering_rows=False;self.update_stats();self.update_summary()
        self.page_label.setText(f'{self.page_offset+1 if eligible else 0}–{self.page_offset+len(self.visible_indices)} / {len(eligible)}')
        self.previous_action.setEnabled(self.page_offset>0);self.next_action.setEnabled(self.page_offset+self.page_size<len(eligible))
        if self.visible_indices:self.table.setCurrentCell(0,0);self.show_source(0)
        else:self.show_source(-1)

    def show_source(self,row,*args):
        self.preview_generation+=1
        if self.preview_job:self.preview_job.cancelled.set()
        self.preview_pages=[];self.preview_original=None;self.preview_image.clear();self.preview_page_label.setText('0 / 0');self.preview_status.setText('Đang chuẩn bị preview…');self.preview_timer.start()
        if not 0<=row<len(self.visible_indices):
            self.preview_timer.stop();self.source.clear();self.preview_status.setText('Không có câu trong phạm vi đang lọc');return
        r=self.results[self.visible_indices[row]];self.source.setPlainText(r['source']);v=r['parsed'].get('classification',{})
        self.resource_list.clear()
        for asset in r['parsed'].get('assets',[]):
            item=QListWidgetItem(f"{asset.get('resolution_status','RESOLVED')} · {asset.get('reference','')}");item.setData(Qt.ItemDataRole.UserRole,asset.get('reference',''));item.setToolTip(asset.get('source_context',''));self.resource_list.addItem(item)
        self.resource_list.addItem(QListWidgetItem(f"{len(r['parsed'].get('assets',[]))} tài nguyên · {len(r['errors'])} lỗi"))
        self.details.setText((breadcrumb(self.nodes,v.get('taxonomy_id')) or 'Chưa phân loại')+' • '+(v.get('cognitive_level') or 'Chưa gán mức độ'))

    def assign_selected(self):
        self.assign_rows(sorted({self.visible_indices[index.row()] for index in self.table.selectionModel().selectedRows()}))

    def assign_rows(self,rows):
        item=self.tree.currentItem()
        if not rows or not item or not self.services:QMessageBox.information(self,'Chưa chọn','Chọn câu hỏi và bài hoặc dạng trên cây.');return
        node_id=item.data(0,Qt.ItemDataRole.UserRole);node=next(n for n in self.nodes if n['id']==node_id)
        if node['kind'] not in ('lesson','topic'):QMessageBox.information(self,'Chọn bài hoặc dạng','Hãy chọn bài hoặc dạng dưới bài.');return
        from latex_question_studio.domain.curriculum import classification
        values={**classification(self.nodes,node_id),'taxonomy_id':node_id,'cognitive_level':self.level.currentData()}
        changed=[i for i in rows if self.results[i]['parsed'].get('classification',{}).get('taxonomy_id') and self.results[i]['parsed']['classification'].get('taxonomy_id')!=node_id]
        if changed:
            message=f"Gán lại {len(changed)} câu đã có phân loại thành:\n{breadcrumb(self.nodes,node_id)}\nMức độ: {self.level.currentText()}"
            if QMessageBox.question(self,'Xác nhận thay phân loại',message)!=QMessageBox.StandardButton.Yes:return
        try:
            ImportService(self.services).assign_classification([self.results[i]['id'] for i in rows],node_id,self.level.currentData())
            for i in rows:self.results[i]['parsed']['classification']=values.copy()
            self.refresh_rows();self.show_source(self.table.currentRow());self.summary.setText(f'Đã gán {len(rows)} câu; phân loại đã lưu trong hàng chờ.')
        except Exception as error:QMessageBox.warning(self,'Không thể gán',str(error))

    def add_topic(self):
        item=self.tree.currentItem()
        if not item or not self.services:return
        node=next(n for n in self.nodes if n['id']==item.data(0,Qt.ItemDataRole.UserRole))
        lookup={n['id']:n for n in self.nodes}
        while node['kind']!='lesson' and node.get('parent_id') in lookup:node=lookup[node['parent_id']]
        if node['kind']!='lesson':QMessageBox.information(self,'Chọn bài','Chọn bài để thêm dạng.');return
        name,ok=QInputDialog.getText(self,'Thêm dạng',f"Dạng mới dưới {node['name']}:")
        if ok and name.strip():
            existing=next((n for n in self.nodes if n['parent_id']==node['id'] and n['name'].casefold()==name.strip().casefold()),None)
            selected=existing['id'] if existing else LibraryService(self.services).add_taxonomy(name,'topic',node['id'])
            self.refresh_tree(selected)

    def compile_preview(self,*args):
        if not self.services or self.table.currentRow()<0:return
        self.preview_timer.stop();self.preview_generation+=1;generation=self.preview_generation
        if self.preview_job:self.preview_job.cancelled.set()
        self.preview_status.setText('Đang biên dịch preview…')
        record=self.results[self.visible_indices[self.table.currentRow()]];source=record['source']
        from pathlib import Path
        import json
        from latex_question_studio.preview.compiler import Compiler
        from latex_question_studio.ui.jobs import Job
        config_path=self.services.config.data_dir/'compiler.json'
        try:config=json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
        except (ValueError,OSError):config={}
        assets={a['reference']:self.services.config.data_dir/a['relative_path'] for a in record['parsed'].get('assets',[])}
        compiler=Compiler(self.services.config.data_dir,engine=config.get('engine','pdflatex'),preamble_file=config.get('preamble_file') or None)
        def work(cancelled,progress):
            result=compiler.compile(source,assets,cancelled)
            pages=[]
            if result.ok and not cancelled():
                first,count=compiler.render(result.pdf);pages.append(first)
                for page in range(1,count):
                    if cancelled():break
                    pages.append(compiler.render(result.pdf,page)[0])
            return generation,result,pages
        job=Job(work);self.preview_job=job
        self.preview_jobs=[j for j in getattr(self,'preview_jobs',[]) if not j.finished.is_set()]+[job]
        job.signals.completed.connect(self.preview_ready)
        job.signals.failed.connect(lambda message,g=generation:self.preview_failed(g,message))
        QThreadPool.globalInstance().start(job)

    def preview_ready(self,payload):
        generation,result,pages=payload
        if generation!=self.preview_generation:return
        self.preview_job=None
        if not result.ok or not pages:
            self.preview_failed(generation,result.log);return
        self.preview_pages=pages;self.preview_status.setText('Preview câu hỏi và lời giải');self.show_preview_page(0)

    def preview_failed(self,generation,message):
        if generation!=self.preview_generation:return
        self.preview_job=None;self.preview_pages=[];self.preview_original=None;self.preview_image.clear();self.preview_status.setText('Không biên dịch được. Xem Source và tooltip để biết lỗi.');self.preview_status.setToolTip(message[-4000:])

    def show_preview_page(self,index):
        if not 0<=index<len(self.preview_pages):return
        self.preview_index=index;pixmap=QPixmap();pixmap.loadFromData(self.preview_pages[index]);self.preview_original=pixmap;self.fit_preview();self.preview_page_label.setText(f'{index+1} / {len(self.preview_pages)}')

    def cancel_preview(self):
        self.preview_timer.stop();self.preview_generation+=1
        for job in getattr(self,'preview_jobs',[]):job.cancelled.set()
        self.preview_job=None

    def closeEvent(self,event):
        self.cancel_preview()
        super().closeEvent(event)

    def fit_preview(self):
        pixmap=getattr(self,'preview_original',None)
        if pixmap is None or pixmap.isNull():return
        width=max(100,self.preview_scroll.viewport().width()-12)
        shown=pixmap.scaledToWidth(min(width,pixmap.width()),Qt.TransformationMode.SmoothTransformation)
        self.preview_image.setMinimumSize(0,0);self.preview_image.setPixmap(shown)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'preview_scroll'):QTimer.singleShot(0,self.fit_preview)

    def eventFilter(self,obj,event):
        if hasattr(self,'preview_scroll') and obj==self.preview_scroll.viewport() and event.type()==QEvent.Type.Resize:
            QTimer.singleShot(0,self.fit_preview)
        return super().eventFilter(obj,event)

    def selected_ids(self):
        return [r['id'] for r in self.results if r['id'] not in self.excluded_ids]

    @staticmethod
    def status_for(record):
        if record.get('duplicate',record.get('parsed',{}).get('duplicate_suggestion')): return 'DUPLICATE'
        if record.get('errors'):
            messages=' '.join(error.get('message','') for error in record['errors'])
            if 'AMBIGUOUS_ASSET' in messages:return 'AMBIGUOUS_ASSET'
            if 'MISSING_ASSET' in messages or 'Thiếu tài nguyên' in messages:return 'MISSING_ASSET'
            if 'NEEDS_REVIEW' in messages:return 'NEEDS_REVIEW'
            return 'INVALID_LATEX'
        return 'READY'

    def _selected_record(self):
        row=self.table.currentRow()
        return self.results[self.visible_indices[row]] if 0<=row<len(self.visible_indices) else None

    def choose_asset(self):
        record=self._selected_record();item=self.resource_list.currentItem()
        if not record or not item or not item.data(Qt.ItemDataRole.UserRole):
            QMessageBox.information(self,'Chọn tài nguyên','Chọn một tài nguyên trong inspector trước.');return
        reference=item.data(Qt.ItemDataRole.UserRole);path,_=QFileDialog.getOpenFileName(self,'Chọn lại tài nguyên','','Ảnh/PDF/TeX (*.png *.jpg *.jpeg *.pdf *.tex)')
        if not path:return
        from pathlib import Path
        from latex_question_studio.application.assets import AssetStore
        try:
            selected=Path(path);staged=AssetStore(self.services.config.data_dir).stage_bytes(selected.read_bytes(),selected.suffix,getattr(self,'batch_id','review-'+record['id']))
            for asset in record['parsed'].get('assets',[]):
                if asset.get('reference')==reference:
                    asset.update({'hash':staged['hash'],'relative_path':staged['relative_path'],'staging_path':staged['staging_path'],'bytes':staged['bytes'],'resolution_status':'RESOLVED','source_context':str(selected.parent.resolve()),'candidates':[str(selected.resolve())]})
            record['errors']=[error for error in record['errors'] if reference not in error.get('message','')]
            self.refresh_rows();self.show_source(self.table.currentRow());self.summary.setText('Đã chọn lại tài nguyên; kiểm tra preview rồi nhập câu hợp lệ.')
        except Exception as error:QMessageBox.warning(self,'Không thể chọn tài nguyên',str(error))

    def add_search_dir(self):
        folder=QFileDialog.getExistingDirectory(self,'Thêm thư mục tìm kiếm tài nguyên')
        if not folder:return
        record=self._selected_record()
        if not record:return
        from pathlib import Path
        from latex_question_studio.application.assets import AssetResolver,AssetStore
        try:
            graph=AssetResolver().resolve(record['source'],Path(folder))
            store=AssetStore(self.services.config.data_dir)
            for asset in record['parsed'].get('assets',[]):
                matches=[entry for entry in graph.by_reference().get(asset.get('reference'),()) if entry.dependency_type=='image']
                if matches and matches[0].resolution_status=='RESOLVED' and matches[0].selected_path:
                    selected=Path(matches[0].selected_path);staged=store.stage_bytes(selected.read_bytes(),selected.suffix,getattr(self,'batch_id','review-'+record['id']))
                    asset.update({'hash':staged['hash'],'relative_path':staged['relative_path'],'staging_path':staged['staging_path'],'bytes':staged['bytes'],'resolution_status':'RESOLVED','source_context':matches[0].source_context,'candidates':list(matches[0].candidates)})
            record['errors']=[error for error in record['errors'] if 'MISSING_ASSET' not in error.get('message','') and 'AMBIGUOUS_ASSET' not in error.get('message','')]
            self.refresh_rows();self.show_source(self.table.currentRow())
        except Exception as error:QMessageBox.warning(self,'Không thể thêm thư mục',str(error))
    def inclusion_changed(self,item):
        if self.rendering_rows or item.column()!=0:return
        record=self.results[self.visible_indices[item.row()]]
        if item.checkState()==Qt.CheckState.Checked:self.excluded_ids.discard(record['id'])
        else:self.excluded_ids.add(record['id'])
        self.update_summary()
    def toggle_inclusion(self):
        rows={index.row() for index in self.table.selectionModel().selectedRows()}
        for row in rows:
            item=self.table.item(row,0);item.setCheckState(Qt.CheckState.Unchecked if item.checkState()==Qt.CheckState.Checked else Qt.CheckState.Checked)
    def update_summary(self):
        errors=sum(bool(r['errors']) for r in self.results);dups=sum(bool(r.get('duplicate',r['parsed'].get('duplicate_suggestion'))) for r in self.results)
        self.summary.setText(f'{len(self.results)} câu · {len(self.results)-errors} hợp lệ · {errors} lỗi · {dups} gợi ý trùng · {len(self.selected_ids())} được chọn nhập')
        self.confirm_action.setEnabled(bool(self.selected_ids()))
