from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QLineEdit,QSpinBox,QCheckBox,QTableWidget,QTableWidgetItem,QPushButton,QDialogButtonBox,QLabel,QSplitter,QTreeWidget,QTreeWidgetItem,QHBoxLayout,QComboBox,QToolBar

class ExamDialog(QWidget):
    submitted = Signal()
    use_selection = Signal()
    def __init__(self,manual_ids,parent=None,services=None,run_job=None):
        super().__init__(parent);self.manual_ids=list(manual_ids);self.services=services;self.scope=None;self.run_job=run_job;self.stats_generation=0;self.stats_job=None;self.available=None;self.snapshot=None
        from latex_question_studio.ui.components.workspace import Workspace,CommandToolbar
        from latex_question_studio.ui.panels.question_preview import QuestionPreview
        from PySide6.QtWidgets import QListWidget,QHeaderView
        layout=QVBoxLayout(self);layout.setContentsMargins(8,8,8,8);layout.setSpacing(6);layout.addWidget(QLabel('RA ĐỀ THI'))
        self.toolbar=CommandToolbar('Ra đề thi',self);layout.addWidget(self.toolbar)
        self.generate_action=self.toolbar.command('exam','Tạo đề',self.submitted.emit,True)
        self.select_action=self.toolbar.command('bank','Lấy câu đang chọn từ CSDL',self.use_selection.emit)
        self.toolbar.addSeparator()
        self.scope_action=self.toolbar.command('chapter','Thêm phạm vi và số câu vào ma trận',self.add_scope_rows);self.scope_action.setEnabled(bool(services))
        self.add_action=self.toolbar.command('topic','Thêm hàng ma trận',self.add_row)
        self.remove_action=self.toolbar.command('close','Xóa hàng ma trận đang chọn',self.remove_row)
        self.refresh_action=self.toolbar.command('preview','Cập nhật thống kê nguồn',self.refresh_statistics);self.refresh_action.setEnabled(bool(services))
        self.options=QWidget();form=QHBoxLayout(self.options);form.setContentsMargins(0,0,0,0)
        self.title=QLineEdit('Đề kiểm tra');self.title.setPlaceholderText('Tên đề');form.addWidget(self.title,2)
        self.seed=QSpinBox();self.seed.setRange(0,2_000_000_000);self.seed.setValue(2027);self.seed.setToolTip('Seed để tái lập lựa chọn');form.addWidget(QLabel('Seed'));form.addWidget(self.seed)
        self.shuffle_questions=QCheckBox('Xáo câu');self.shuffle_questions.setChecked(True);form.addWidget(self.shuffle_questions)
        self.shuffle_options=QCheckBox('Xáo phương án');self.shuffle_options.setToolTip('Giữ đúng đáp án khi xáo');self.shuffle_options.setChecked(True);form.addWidget(self.shuffle_options);layout.addWidget(self.options)
        self.selection_label=QLabel();layout.addWidget(self.selection_label)
        self.workspace=Workspace('examSplit');layout.addWidget(self.workspace,1)
        left=QWidget();lb=QVBoxLayout(left);lb.setContentsMargins(0,0,0,0)
        self.tree=QTreeWidget();self.tree.setHeaderLabel('PHẠM VI NGUỒN CÂU');self.tree.setExpandsOnDoubleClick(True);lb.addWidget(self.tree);self.workspace.addWidget(left)
        center=QWidget();box=QVBoxLayout(center);box.setContentsMargins(0,0,0,0);self.workspace.addWidget(center)
        self.scope_label=QLabel('Toàn ngân hàng');self.scope_label.setWordWrap(True);box.addWidget(self.scope_label)
        self.question_type=QComboBox()
        for text,value in [('Tất cả loại',''),('Trắc nghiệm','mcq'),('Đúng / sai','true_false'),('Trả lời ngắn','short_answer'),('Tự luận','essay')]:self.question_type.addItem(text,value)
        box.addWidget(self.question_type)
        self.stats=QTableWidget(4,3);self.stats.setHorizontalHeaderLabels(['Mức độ','Có thể lấy','Cần lấy']);self.targets={}
        for i,(level,label) in enumerate([('NB','Nhận biết'),('TH','Thông hiểu'),('VD','Vận dụng'),('VDC','Vận dụng cao')]):
            self.stats.setItem(i,0,QTableWidgetItem(label));spin=QSpinBox();spin.setRange(0,500);self.targets[level]=spin;self.stats.setCellWidget(i,2,spin);spin.valueChanged.connect(self.update_shortage)
        self.stats.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.stats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.stats.setMaximumHeight(185);box.addWidget(self.stats)
        self.stats_note=QLabel();self.stats_note.setWordWrap(True);box.addWidget(self.stats_note)
        self.shortage=QLabel();self.shortage.setWordWrap(True);box.addWidget(self.shortage)
        self.matrix=QTableWidget(0,7);self.matrix.setHorizontalHeaderLabels(['Môn','Khối','Loại','Mức độ','Số câu','Phạm vi CSDL','Nguồn']);self.matrix.horizontalHeader().setMinimumSectionSize(45);self.matrix.setColumnWidth(5,150)
        for i in (0,1,2,3,4,6):self.matrix.setColumnWidth(i,65)
        self.matrix.horizontalHeader().setStretchLastSection(True);box.addWidget(self.matrix,1)
        self.matrix_summary=QLabel('Ma trận: 0 câu');self.matrix_summary.setWordWrap(True);box.addWidget(self.matrix_summary);self.matrix.itemChanged.connect(self.update_matrix_summary)
        right=QWidget();rb=QVBoxLayout(right);rb.setContentsMargins(0,0,0,0);rb.addWidget(QLabel('CÂU ĐÃ CHỌN / CẤU TRÚC ĐỀ'))
        self.chosen=QListWidget();self.chosen.setMaximumHeight(180);rb.addWidget(self.chosen)
        self.preview=QuestionPreview(services,run_job);rb.addWidget(self.preview,1);self.workspace.addWidget(right);self.workspace.setSizes([260,620,420]);self.chosen.currentRowChanged.connect(self.preview_selected)
        self.nodes=[];self.tree_items={}
        if services:
            from latex_question_studio.application.library import LibraryService
            from latex_question_studio.ui.icons import icon
            self.nodes=LibraryService(services).taxonomy();items={n['id']:QTreeWidgetItem([n['name']+f" ({n.get('question_count',0)})"]) for n in self.nodes}
            all_item=QTreeWidgetItem(['Toàn ngân hàng']);self.tree.addTopLevelItem(all_item)
            for n in self.nodes:
                item=items[n['id']];item.setData(0,Qt.ItemDataRole.UserRole,n['id']);item.setIcon(0,icon('subject' if n['kind'] in ('subject','grade') else 'chapter' if n['kind']=='chapter' else 'topic','#579bd4'));items.get(n['parent_id'],all_item).addChild(item)
            all_item.setExpanded(True);self.tree_items=items;self.tree.itemClicked.connect(self.select_scope)
        self.question_type.currentIndexChanged.connect(self.refresh_statistics)
        self.set_manual_ids(manual_ids)
        if services:self.refresh_statistics()

    def update_shortage(self,*args):
        if not self.available:return
        missing=[f'{level}: thiếu {spin.value()-self.available["counts"][level]}' for level,spin in self.targets.items() if spin.value()>self.available['counts'][level]]
        self.shortage.setText(' · '.join(missing) if missing else 'Nguồn đáp ứng số lượng đang chọn trong phạm vi này.')
        self.shortage.setStyleSheet('color:#d88a37' if missing else '')

    def show_snapshot(self,snapshot):
        from latex_question_studio.ui.pages.library import readable
        self.snapshot=snapshot;self.chosen.blockSignals(True);self.chosen.clear()
        for i,q in enumerate(snapshot['questions'],1):self.chosen.addItem(f'{i}. '+readable(q['source'])[:100])
        self.chosen.blockSignals(False)
        if self.chosen.count():self.chosen.setCurrentRow(0)

    def preview_selected(self,index):
        if index<0:self.preview.set_source('');return
        if self.snapshot:
            q=self.snapshot['questions'][index];self.preview.set_source(q['source'],self.snapshot.get('assets',{}));return
        if not self.services or index>=len(self.manual_ids):return
        q=self.services.questions.get(self.manual_ids[index])
        if not q:return
        with self.services.database.connect() as c:
            assets={r['original_reference']:self.services.config.data_dir/r['relative_path'] for r in c.execute('SELECT qa.original_reference,a.relative_path FROM question_assets qa JOIN assets a ON a.id=qa.asset_id WHERE qa.question_id=?',(q.id,))}
        self.preview.set_source(q.latex_source,assets)

    def set_manual_ids(self, ids):
        self.manual_ids=list(ids);self.snapshot=None
        if hasattr(self,'chosen'):
            from latex_question_studio.ui.pages.library import readable
            self.chosen.blockSignals(True);self.chosen.clear()
            if self.services:
                for i,qid in enumerate(ids,1):
                    q=self.services.questions.get(qid)
                    if q:self.chosen.addItem(f'{i}. '+readable(q.latex_source)[:100])
            self.chosen.blockSignals(False);self.preview.set_source('')
        self.selection_label.setText(f'Đã chọn {len(ids)} câu thủ công; các hàng bên dưới lấy thêm câu không trùng.')
        if hasattr(self,'stats'):self.refresh_statistics()
    def add_row(self):
        i=self.matrix.rowCount();self.matrix.insertRow(i)
        for j in range(7):self.matrix.setItem(i,j,QTableWidgetItem('1' if j==4 else ''))
    def values(self):
        rows=[]
        for i in range(self.matrix.rowCount()):
            values=[self.matrix.item(i,j).text().strip() for j in range(5)]
            rows.append({'filters':dict(zip(['subject','grade','question_type','cognitive_level'],values[:4])),'count':int(values[4]),'taxonomy_id':self.matrix.item(i,5).data(Qt.ItemDataRole.UserRole)})
        return dict(title=self.title.text(),manual_ids=self.manual_ids,matrix=rows,seed=self.seed.value(),shuffle_questions=self.shuffle_questions.isChecked(),shuffle_options=self.shuffle_options.isChecked())

    def select_scope(self,item,*args):
        self.scope=item.data(0,Qt.ItemDataRole.UserRole)
        from latex_question_studio.domain.curriculum import breadcrumb
        self.scope_label.setText(breadcrumb(self.nodes,self.scope) or 'Toàn ngân hàng');self.refresh_statistics()

    def cancel_statistics(self):
        self.stats_generation+=1
        if self.stats_job:self.stats_job.cancelled.set()
        self.stats_job=None

    def refresh_statistics(self,*args):
        if not self.services:return
        from latex_question_studio.application.exams import ExamService
        self.cancel_statistics();generation=self.stats_generation
        scope=self.scope;kind=self.question_type.currentData();manual=list(self.manual_ids)
        def apply(result):
            if generation!=self.stats_generation:return
            self.stats_job=None;self.available=result;self.scope_action.setEnabled(True)
            for i,level in enumerate(('NB','TH','VD','VDC')):self.stats.setItem(i,1,QTableWidgetItem(str(result['counts'][level])))
            self.update_shortage()
            self.stats_note.setText(f"Tổng {result['total']} câu hợp lệ • {result['counts']['unclassified']} chưa gán mức độ • {result['invalid']} source lỗi không tính. Đã loại câu chọn thủ công; các phạm vi chồng nhau có thể dùng chung nguồn.")
        if not self.run_job:apply(ExamService(self.services).statistics(scope,kind,manual));return
        self.available=None;self.scope_action.setEnabled(False);self.stats_note.setText('Đang thống kê nguồn câu…')
        from latex_question_studio.ui.jobs import Job
        job=Job(lambda cancelled,progress:ExamService(self.services).statistics(scope,kind,manual,cancelled));self.stats_job=job
        job.signals.completed.connect(apply)
        def failed(message):
            if generation!=self.stats_generation:return
            self.stats_job=None;self.stats_note.setText('Thống kê đã dừng: '+message)
        job.signals.failed.connect(failed);self.run_job(job)

    def closeEvent(self,event):
        self.cancel_statistics();self.preview.cancel();super().closeEvent(event)

    def add_scope_rows(self):
        from latex_question_studio.domain.curriculum import classification,breadcrumb
        values=classification(self.nodes,self.scope)
        if not self.run_job:self.refresh_statistics()
        if self.available is None:return
        for level,count in ((level,spin.value()) for level,spin in self.targets.items()):
            if not count:continue
            self.add_row();i=self.matrix.rowCount()-1
            texts=[values.get('subject',''),values.get('grade',''),self.question_type.currentData(),level,str(count),breadcrumb(self.nodes,self.scope) or 'Toàn ngân hàng',str(self.available['counts'][level])]
            for j,text in enumerate(texts):self.matrix.item(i,j).setText(text);self.matrix.item(i,j).setToolTip(text)
            self.matrix.item(i,5).setData(Qt.ItemDataRole.UserRole,self.scope);self.matrix.item(i,5).setFlags(self.matrix.item(i,5).flags() & ~Qt.ItemFlag.ItemIsEditable)
        for spin in self.targets.values():spin.setValue(0)

    def update_matrix_summary(self,*args):
        totals={level:0 for level in ('NB','TH','VD','VDC')};total=0
        for i in range(self.matrix.rowCount()):
            count_item=self.matrix.item(i,4);level_item=self.matrix.item(i,3)
            try:count=int(count_item.text()) if count_item else 0
            except ValueError:count=0
            total+=count
            if level_item and level_item.text() in totals:totals[level_item.text()]+=count
        self.matrix_summary.setText('Ma trận: '+str(total)+' câu • '+' • '.join(f'{level}: {count}' for level,count in totals.items()))

    def remove_row(self):
        if self.matrix.currentRow()>=0:
            self.matrix.removeRow(self.matrix.currentRow());self.update_matrix_summary()
