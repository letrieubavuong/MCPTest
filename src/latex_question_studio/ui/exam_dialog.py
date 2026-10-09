from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QLineEdit,QSpinBox,QCheckBox,QTableWidget,QTableWidgetItem,QPushButton,QDialogButtonBox,QLabel

class ExamDialog(QWidget):
    submitted = Signal()
    use_selection = Signal()
    def __init__(self,manual_ids,parent=None):
        super().__init__(parent);self.manual_ids=manual_ids
        self.setWindowTitle("Tạo đề thủ công / Ma trận");self.resize(850,530)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('RA ĐỀ THI'));form=QFormLayout()
        self.title=QLineEdit('Đề kiểm tra');form.addRow('Tên đề',self.title)
        self.seed=QSpinBox();self.seed.setRange(0,2_000_000_000);self.seed.setValue(2027);form.addRow('Seed tái lập',self.seed)
        self.shuffle_questions=QCheckBox('Xáo câu');self.shuffle_questions.setChecked(True);form.addRow(self.shuffle_questions)
        self.shuffle_options=QCheckBox('Xáo phương án MCQ, giữ đáp án');self.shuffle_options.setChecked(True);form.addRow(self.shuffle_options)
        layout.addLayout(form)
        self.selection_label=QLabel();layout.addWidget(self.selection_label);self.set_manual_ids(manual_ids)
        select=QPushButton('Lấy câu đang chọn từ Xem CSDL');select.clicked.connect(self.use_selection.emit);layout.addWidget(select)
        self.matrix=QTableWidget(0,5);self.matrix.setHorizontalHeaderLabels(['Môn','Khối','Loại (mcq/essay/true_false/short_answer)','Nhận thức (NB/TH/VD/VDC)','Số câu']);layout.addWidget(self.matrix)
        button=QPushButton('Thêm hàng ma trận');button.clicked.connect(self.add_row);layout.addWidget(button)
        button=QPushButton('Tạo đề');button.clicked.connect(self.submitted.emit);layout.addWidget(button)
    def set_manual_ids(self, ids):
        self.manual_ids=list(ids)
        self.selection_label.setText(f'Đã chọn {len(ids)} câu thủ công; các hàng bên dưới lấy thêm câu không trùng.')
    def add_row(self):
        i=self.matrix.rowCount();self.matrix.insertRow(i)
        for j in range(5):self.matrix.setItem(i,j,QTableWidgetItem('1' if j==4 else ''))
    def values(self):
        rows=[]
        for i in range(self.matrix.rowCount()):
            values=[self.matrix.item(i,j).text().strip() for j in range(5)]
            rows.append({'filters':dict(zip(['subject','grade','question_type','cognitive_level'],values[:4])),'count':int(values[4])})
        return dict(title=self.title.text(),manual_ids=self.manual_ids,matrix=rows,seed=self.seed.value(),shuffle_questions=self.shuffle_questions.isChecked(),shuffle_options=self.shuffle_options.isChecked())
