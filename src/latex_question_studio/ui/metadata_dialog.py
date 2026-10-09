from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QFormLayout,QLineEdit,QComboBox,QDialogButtonBox,QLabel

class MetadataDialog(QDialog):
    def __init__(self, metadata, taxonomy, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Phân loại và nhãn")
        layout=QFormLayout(self)
        self.fields={}
        for key,label in [('subject','Môn'),('grade','Khối'),('chapter','Chương'),('lesson','Bài'),('topic','Chủ đề'),('tags','Nhãn, cách nhau dấu phẩy'),('source','Nguồn')]:
            value=metadata.get(key,'')
            if isinstance(value,list):value=', '.join(value)
            field=QLineEdit(str(value));layout.addRow(label,field);self.fields[key]=field
        self.taxonomy=QComboBox();self.taxonomy.addItem("Chưa phân loại",None)
        from latex_question_studio.domain.curriculum import breadcrumb
        for node in taxonomy:
            label=breadcrumb(taxonomy,node['id'])
            self.taxonomy.addItem(label,node['id'])
            self.taxonomy.setItemData(self.taxonomy.count()-1,label,Qt.ItemDataRole.ToolTipRole)
        self.taxonomy_nodes=taxonomy
        self.taxonomy.setMinimumContentsLength(30)
        self.taxonomy.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.taxonomy.setCurrentIndex(max(0,self.taxonomy.findData(metadata.get('taxonomy_id'))))
        layout.addRow("Cây phân loại",self.taxonomy)
        self.taxonomy.currentIndexChanged.connect(self.apply_classification)
        self.resize(720,460)
        self.choices={}
        for key,label,values in [('question_type','Loại câu',['','unknown','mcq','true_false','short_answer','essay']),('difficulty_legacy','Mức độ cũ',['','0','1','2','3','4']),('cognitive_level','Nhận thức',['','NB','TH','VD','VDC'])]:
            combo=QComboBox();combo.addItems(values);combo.setCurrentText(str(metadata.get(key) if metadata.get(key) is not None else ''));layout.addRow(label,combo);self.choices[key]=combo
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addRow(buttons)

    def apply_classification(self,*args):
        from latex_question_studio.domain.curriculum import classification
        for key,value in classification(self.taxonomy_nodes,self.taxonomy.currentData()).items():
            if key in self.fields:self.fields[key].setText(value)

    def values(self):
        data={key:field.text().strip() for key,field in self.fields.items()}
        data['tags']=[s.strip() for s in data['tags'].split(',') if s.strip()]
        data['taxonomy_id']=self.taxonomy.currentData()
        data.update({k:v.currentText() for k,v in self.choices.items()})
        data['difficulty_legacy']=int(data['difficulty_legacy']) if data['difficulty_legacy'] else None
        data['cognitive_level']=data['cognitive_level'] or None
        return data
