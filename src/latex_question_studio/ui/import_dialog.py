from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QSplitter,QTreeWidget,QTreeWidgetItem,QTableWidget,QTableWidgetItem,QPlainTextEdit,QPushButton,QLabel,QComboBox,QLineEdit,QMessageBox,QInputDialog
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.library import LibraryService
from latex_question_studio.domain.curriculum import breadcrumb
from latex_question_studio.ui.icons import icon

class ImportReview(QWidget):
    accepted=Signal()
    rejected=Signal()
    def __init__(self,results,parent=None,services=None):
        super().__init__(parent);self.results=results;self.services=services
        self.setWindowTitle('Duyệt nhập và phân loại câu hỏi')
        layout=QVBoxLayout(self)
        errors=sum(bool(r['errors']) for r in results)
        self.summary=QLabel(f'{len(results)} câu • {errors} lỗi • Phân loại được lưu trong hàng chờ trước khi nhập.');layout.addWidget(self.summary)
        split=QSplitter();layout.addWidget(split,1)
        left=QWidget();box=QVBoxLayout(left);self.tree_search=QLineEdit();self.tree_search.setPlaceholderText('Tìm môn, bài, dạng…');box.addWidget(self.tree_search)
        self.tree=QTreeWidget();self.tree.setHeaderLabel('CSDL • Môn → Chương → Bài → Dạng');self.tree.setExpandsOnDoubleClick(True);box.addWidget(self.tree)
        add=QPushButton('Thêm dạng dưới bài');box.addWidget(add);add.clicked.connect(self.add_topic)
        split.addWidget(left)
        center=QWidget();box=QVBoxLayout(center)
        self.only_missing=QComboBox();self.only_missing.addItems(['Tất cả câu','Chưa gán bài','Chưa gán dạng','Chưa gán mức độ']);box.addWidget(self.only_missing)
        self.table=QTableWidget(len(results),5);self.table.setHorizontalHeaderLabels(['File / câu','Loại','Bài / dạng','Mức độ','Lỗi / gợi ý trùng'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.table.horizontalHeader().setStretchLastSection(True);self.table.setColumnWidth(0,155);self.table.setColumnWidth(2,250);box.addWidget(self.table)
        controls=QHBoxLayout();self.level=QComboBox()
        for label,value in [('Chưa gán mức độ',None),('Nhận biết','NB'),('Thông hiểu','TH'),('Vận dụng','VD'),('Vận dụng cao','VDC')]:self.level.addItem(label,value)
        controls.addWidget(self.level);assign=QPushButton('Gán cho câu đã chọn');assign.clicked.connect(self.assign_selected);controls.addWidget(assign)
        all_button=QPushButton('Gán toàn bộ danh sách');all_button.clicked.connect(lambda:self.assign_rows(list(range(len(self.results)))));controls.addWidget(all_button);box.addLayout(controls);split.addWidget(center)
        right=QWidget();box=QVBoxLayout(right);self.details=QLabel('Chọn câu để xem source và phân loại');self.details.setWordWrap(True);box.addWidget(self.details);self.source=QPlainTextEdit();self.source.setReadOnly(True);box.addWidget(self.source);split.addWidget(right);split.setSizes([300,650,350])
        button=QPushButton('Ghi các câu hợp lệ vào ngân hàng');button.clicked.connect(self.accepted.emit);layout.addWidget(button)
        cancel=QPushButton('Đóng — giữ hàng chờ');cancel.clicked.connect(self.rejected.emit);layout.addWidget(cancel)
        self.table.currentCellChanged.connect(self.show_source);self.only_missing.currentIndexChanged.connect(self.refresh_rows);self.tree_search.textChanged.connect(self.filter_tree)
        self.refresh_tree();self.refresh_rows()
        if results:self.table.setCurrentCell(0,0)

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

    def refresh_rows(self,*args):
        for i,r in enumerate(self.results):
            values=r['parsed'].get('classification',{});label=breadcrumb(self.nodes,values.get('taxonomy_id'))
            texts=[f"{r['path']} • câu {i+1}",r['parsed'].get('type','unknown'),label or 'Chưa gán',values.get('cognitive_level') or 'Chưa gán','; '.join(e['message'] for e in r['errors'])+(' • Gợi ý trùng' if r.get('duplicate',r['parsed'].get('duplicate_suggestion')) else '')]
            for j,text in enumerate(texts):self.table.setItem(i,j,QTableWidgetItem(text));self.table.item(i,j).setToolTip(text)
            missing=[True,not values.get('lesson'),not values.get('topic'),not values.get('cognitive_level')][self.only_missing.currentIndex()];self.table.setRowHidden(i,not missing)

    def show_source(self,row,*args):
        if row<0:return
        r=self.results[row];self.source.setPlainText(r['source']);v=r['parsed'].get('classification',{})
        self.details.setText((breadcrumb(self.nodes,v.get('taxonomy_id')) or 'Chưa phân loại')+' • '+(v.get('cognitive_level') or 'Chưa gán mức độ'))

    def assign_selected(self):
        self.assign_rows(sorted({index.row() for index in self.table.selectionModel().selectedRows()}))

    def assign_rows(self,rows):
        item=self.tree.currentItem()
        if not rows or not item or not self.services:QMessageBox.information(self,'Chưa chọn','Chọn câu hỏi và bài hoặc dạng trên cây.');return
        node_id=item.data(0,Qt.ItemDataRole.UserRole);node=next(n for n in self.nodes if n['id']==node_id)
        if node['kind'] not in ('lesson','topic'):QMessageBox.information(self,'Chọn bài hoặc dạng','Hãy chọn bài hoặc dạng dưới bài.');return
        from latex_question_studio.domain.curriculum import classification
        values={**classification(self.nodes,node_id),'taxonomy_id':node_id,'cognitive_level':self.level.currentData()}
        changed=[i for i in rows if self.results[i]['parsed'].get('classification') and self.results[i]['parsed']['classification']!=values]
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
