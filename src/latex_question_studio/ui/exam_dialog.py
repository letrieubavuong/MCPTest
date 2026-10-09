from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QLineEdit,QSpinBox,QCheckBox,QTableWidget,QTableWidgetItem,QPushButton,QDialogButtonBox,QLabel,QSplitter,QTreeWidget,QTreeWidgetItem,QHBoxLayout,QComboBox

class ExamDialog(QWidget):
    submitted = Signal()
    use_selection = Signal()
    def __init__(self,manual_ids,parent=None,services=None):
        super().__init__(parent);self.manual_ids=manual_ids;self.services=services;self.scope=None
        self.setWindowTitle("Tạo đề thủ công / Ma trận");self.resize(850,530)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('RA ĐỀ THI'));form=QFormLayout()
        self.title=QLineEdit('Đề kiểm tra');form.addRow('Tên đề',self.title)
        self.seed=QSpinBox();self.seed.setRange(0,2_000_000_000);self.seed.setValue(2027);form.addRow('Seed tái lập',self.seed)
        self.shuffle_questions=QCheckBox('Xáo câu');self.shuffle_questions.setChecked(True);form.addRow(self.shuffle_questions)
        self.shuffle_options=QCheckBox('Xáo phương án MCQ, giữ đáp án');self.shuffle_options.setChecked(True);form.addRow(self.shuffle_options)
        layout.addLayout(form)
        self.selection_label=QLabel();layout.addWidget(self.selection_label);self.set_manual_ids(manual_ids)
        select=QPushButton('Lấy câu đang chọn từ Xem CSDL');select.clicked.connect(self.use_selection.emit);layout.addWidget(select)
        if services:
            from latex_question_studio.application.library import LibraryService
            from latex_question_studio.ui.icons import icon
            split=QSplitter();layout.addWidget(split,1);self.tree=QTreeWidget();self.tree.setHeaderLabel('CSDL • chọn phạm vi ra đề');self.tree.setExpandsOnDoubleClick(True);split.addWidget(self.tree)
            self.nodes=LibraryService(services).taxonomy();items={n['id']:QTreeWidgetItem([n['name']]) for n in self.nodes}
            all_item=QTreeWidgetItem(['Toàn ngân hàng']);self.tree.addTopLevelItem(all_item)
            for n in self.nodes:
                item=items[n['id']];item.setData(0,Qt.ItemDataRole.UserRole,n['id']);item.setIcon(0,icon('subject' if n['kind'] in ('subject','grade') else 'chapter' if n['kind']=='chapter' else 'topic','#4ba3eb'))
                parent=items.get(n['parent_id'],all_item);parent.addChild(item)
            all_item.setExpanded(True);self.tree_items=items;self.tree.itemClicked.connect(self.select_scope)
            panel=QWidget();box=QVBoxLayout(panel);split.addWidget(panel);self.scope_label=QLabel('Toàn ngân hàng');self.scope_label.setWordWrap(True);box.addWidget(self.scope_label)
            self.question_type=QComboBox()
            for text,value in [('Tất cả loại',''),('Trắc nghiệm','mcq'),('Đúng / sai','true_false'),('Trả lời ngắn','short_answer'),('Tự luận','essay')]:self.question_type.addItem(text,value)
            self.question_type.currentIndexChanged.connect(self.refresh_statistics);box.addWidget(self.question_type)
            self.stats=QTableWidget(4,3);self.stats.setHorizontalHeaderLabels(['Mức độ','Có thể lấy','Số câu cần lấy']);self.targets={}
            for i,(level,label) in enumerate([('NB','Nhận biết'),('TH','Thông hiểu'),('VD','Vận dụng'),('VDC','Vận dụng cao')]):
                self.stats.setItem(i,0,QTableWidgetItem(label));spin=QSpinBox();spin.setRange(0,500);self.targets[level]=spin;self.stats.setCellWidget(i,2,spin)
            self.stats.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);box.addWidget(self.stats);self.stats_note=QLabel();self.stats_note.setWordWrap(True);box.addWidget(self.stats_note)
            refresh=QPushButton('Cập nhật thống kê');refresh.clicked.connect(self.refresh_statistics);box.addWidget(refresh)
            add=QPushButton('Thêm phạm vi và số câu vào ma trận');add.clicked.connect(self.add_scope_rows);box.addWidget(add)
            self.refresh_statistics()
        self.matrix=QTableWidget(0,7);self.matrix.setHorizontalHeaderLabels(['Môn','Khối','Loại câu','Mức độ','Số câu','Phạm vi CSDL','Có thể lấy']);self.matrix.setColumnWidth(5,260);layout.addWidget(self.matrix)
        self.matrix_summary=QLabel('Ma trận: 0 câu');layout.addWidget(self.matrix_summary);self.matrix.itemChanged.connect(self.update_matrix_summary)
        button=QPushButton('Thêm hàng ma trận');button.clicked.connect(self.add_row);layout.addWidget(button)
        remove=QPushButton('Xóa hàng ma trận đang chọn');remove.clicked.connect(lambda:self.matrix.removeRow(self.matrix.currentRow()) if self.matrix.currentRow()>=0 else None);layout.addWidget(remove)
        button=QPushButton('Tạo đề');button.clicked.connect(self.submitted.emit);layout.addWidget(button)
    def set_manual_ids(self, ids):
        self.manual_ids=list(ids)
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

    def refresh_statistics(self,*args):
        if not self.services:return
        from latex_question_studio.application.exams import ExamService
        self.available=ExamService(self.services).statistics(self.scope,self.question_type.currentData(),self.manual_ids)
        for i,level in enumerate(('NB','TH','VD','VDC')):self.stats.setItem(i,1,QTableWidgetItem(str(self.available['counts'][level])))
        self.stats_note.setText(f"Tổng {self.available['total']} câu hợp lệ • {self.available['counts']['unclassified']} chưa gán mức độ • {self.available['invalid']} source lỗi không tính. Đã loại câu chọn thủ công; các phạm vi chồng nhau có thể dùng chung nguồn.")

    def add_scope_rows(self):
        from latex_question_studio.domain.curriculum import classification,breadcrumb
        values=classification(self.nodes,self.scope);self.refresh_statistics()
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
