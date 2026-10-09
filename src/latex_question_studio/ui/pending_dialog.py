import json
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QTableWidget,QTableWidgetItem,QPlainTextEdit,QPushButton,QLabel,QMessageBox
from latex_question_studio.application.importing import ImportService

class PendingDialog(QWidget):
    committed = Signal()
    def __init__(self,services,parent=None):
        super().__init__(parent);self.importer=ImportService(services)
        self.setWindowTitle('Hàng chờ — sửa bản làm việc, giữ byte nguồn gốc');self.resize(1000,720)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Chọn một mục, sửa source rồi Kiểm tra; chỉ mục hợp lệ mới được ghi.'))
        self.table=QTableWidget(0,2);self.table.setHorizontalHeaderLabels(['Nguồn','Trạng thái / lỗi']);self.table.horizontalHeader().setStretchLastSection(True);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);layout.addWidget(self.table)
        self.source=QPlainTextEdit();layout.addWidget(self.source)
        validate=QPushButton('Kiểm tra và lưu bản sửa');validate.clicked.connect(self.repair);layout.addWidget(validate)
        commit=QPushButton('Ghi mục đang chọn vào ngân hàng');commit.clicked.connect(self.commit);layout.addWidget(commit)
        self.table.currentCellChanged.connect(self.select);self.refresh()
    def refresh(self):
        self.rows=self.importer.pending();self.table.setRowCount(len(self.rows))
        for i,row in enumerate(self.rows):
            errors=json.loads(row['diagnostics_json'])
            self.table.setItem(i,0,QTableWidgetItem(row['original_path']))
            self.table.setItem(i,1,QTableWidgetItem(row['status']+' '+str(errors)))
        if self.rows:self.table.setCurrentCell(0,0);self.select(0)
    def select(self,row,*args):
        if 0<=row<len(self.rows):
            record=self.rows[row];self.source.setPlainText(record['working_source'] if record['working_source'] is not None else record['raw_source'])
    def repair(self):
        i=self.table.currentRow()
        if i<0:return
        try:
            errors=self.importer.repair(self.rows[i]['id'],self.source.toPlainText());self.refresh()
            if errors:QMessageBox.information(self,'Còn lỗi','; '.join(e['message'] for e in errors))
        except Exception as error:QMessageBox.warning(self,'Không thể sửa',str(error))
    def commit(self):
        i=self.table.currentRow()
        if i<0:return
        row=self.rows[i]
        if row['status']!='ready':QMessageBox.warning(self,'Còn lỗi','Kiểm tra và sửa lỗi trước khi ghi.');return
        self.importer.commit(row['batch_id'],{row['id']});self.refresh();self.committed.emit()
