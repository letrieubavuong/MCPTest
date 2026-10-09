from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QTableWidget,QTableWidgetItem,QPlainTextEdit,QPushButton,QLabel

class ImportReview(QWidget):
    accepted = Signal()
    rejected = Signal()
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xem trước nhập dữ liệu")
        self.resize(1000,700)
        self.results = results
        layout = QVBoxLayout(self)
        errors = sum(bool(r['errors']) for r in results)
        duplicates = sum(r.get('duplicate',r.get('parsed',{}).get('duplicate_suggestion',False)) for r in results)
        layout.addWidget(QLabel(f"{len(results)} mục • {len(results)-errors} sẵn sàng • {errors} lỗi • {duplicates} gợi ý trùng (giữ cả hai) • Chỉ ghi mục hợp lệ sau xác nhận"))
        self.table = QTableWidget(len(results),3)
        self.table.setHorizontalHeaderLabels(["File","Loại","Lỗi / vị trí"])
        for i,r in enumerate(results):
            for j,text in enumerate((r['path'],r['parsed'].get('type','unknown'),'; '.join(f"Dòng {e['line']}:{e['column']} {e['message']}" for e in r['errors']))):
                self.table.setItem(i,j,QTableWidgetItem(text))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.currentCellChanged.connect(self.show_source)
        layout.addWidget(self.table)
        self.source = QPlainTextEdit()
        self.source.setReadOnly(True)
        layout.addWidget(self.source)
        button = QPushButton("Ghi các câu hợp lệ vào ngân hàng")
        button.clicked.connect(self.accepted.emit)
        layout.addWidget(button)
        cancel = QPushButton("Đóng — giữ hàng chờ")
        cancel.clicked.connect(self.rejected.emit)
        layout.addWidget(cancel)

    def show_source(self,row,*args):
        if row>=0:self.source.setPlainText(self.results[row]['source'])
