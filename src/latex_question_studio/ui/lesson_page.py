"""Embedded lesson authoring workspace, including a bank picker and PDF preview."""
from copy import deepcopy
import json
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QSplitter, QTreeWidget, QTreeWidgetItem, QFormLayout,
    QPlainTextEdit, QTabWidget, QScrollArea, QTableWidget, QTableWidgetItem,
    QSpinBox, QCheckBox, QFileDialog, QMessageBox, QInputDialog, QStyle)
from latex_question_studio.application.lessons import LessonService, KINDS, POLICIES, block
from latex_question_studio.application.search import SearchService
from latex_question_studio.ui.editor import LatexEditor
from latex_question_studio.ui.jobs import Job
from latex_question_studio.preview.compiler import Compiler


class LessonPage(QWidget):
    def __init__(self, services, run_job, compiler_config, parent=None):
        super().__init__(parent)
        self.services=services;self.service=LessonService(services)
        self.run_job=run_job;self.compiler_config=compiler_config
        self.doc=None;self.current_id=None;self.loading=False;self.dirty=False
        self.preview_generation=0;self.preview_job=None;self.pdf=None;self.pdf_page=0
        self.setObjectName('lessonPage')
        layout=QVBoxLayout(self)
        heading=QLabel('BÀI GIẢNG  /  Lý thuyết · Dạng toán · Ví dụ · Vận dụng')
        layout.addWidget(heading)
        toolbar=QHBoxLayout()
        self.lesson_list=QComboBox();self.lesson_list.setMinimumWidth(230)
        self.lesson_list.currentIndexChanged.connect(self.open_selected)
        toolbar.addWidget(self.lesson_list,1)
        self.button(toolbar,'Tạo bài',self.new_lesson,QStyle.StandardPixmap.SP_FileIcon)
        self.button(toolbar,'Nhân bản',self.duplicate)
        self.button(toolbar,'Lưu',self.save,QStyle.StandardPixmap.SP_DialogSaveButton)
        self.button(toolbar,'Lịch sử',self.history)
        layout.addLayout(toolbar)
        self.title=QLineEdit();self.title.setPlaceholderText('Tên bài giảng')
        self.title.textEdited.connect(self.changed);layout.addWidget(self.title)
        splitter=QSplitter();layout.addWidget(splitter,1)
        outline=QWidget();ol=QVBoxLayout(outline);ol.setContentsMargins(0,0,0,0)
        self.tree=QTreeWidget();self.tree.setHeaderLabel('CẤU TRÚC BÀI')
        self.tree.currentItemChanged.connect(self.select_block);ol.addWidget(self.tree,1)
        self.kind=QComboBox()
        for key,label in KINDS.items():self.kind.addItem(label,key)
        ol.addWidget(self.kind)
        self.button(ol,'Thêm mục cùng cấp',lambda:self.add_block(False))
        self.button(ol,'Thêm mục con',lambda:self.add_block(True))
        row=QHBoxLayout();self.button(row,'↑',lambda:self.move(-1));self.button(row,'↓',lambda:self.move(1));ol.addLayout(row)
        self.button(ol,'Xóa mục',self.remove_block)
        splitter.addWidget(outline)
        self.work=QTabWidget();splitter.addWidget(self.work)
        edit=QWidget();el=QVBoxLayout(edit);el.setContentsMargins(5,5,5,5)
        self.block_title=QLineEdit();self.block_title.setPlaceholderText('Tên mục');self.block_title.textEdited.connect(self.changed)
        el.addWidget(self.block_title)
        self.origin=QLabel();self.origin.setWordWrap(True);el.addWidget(self.origin)
        self.policy=QComboBox()
        for key,label in POLICIES.items():self.policy.addItem(label,key)
        self.policy.currentIndexChanged.connect(self.changed);el.addWidget(self.policy)
        self.editor=LatexEditor();self.editor.textChanged.connect(self.changed);el.addWidget(self.editor,3)
        self.button(el,'Chèn hình PNG/JPG/PDF',self.attach_image)
        el.addWidget(QLabel('Ghi chú riêng giáo viên (không đưa vào bản học sinh)'))
        self.notes=QPlainTextEdit();self.notes.setMaximumHeight(100);self.notes.textChanged.connect(self.changed);el.addWidget(self.notes)
        self.work.addTab(edit,'Biên tập TeX')
        self.build_picker();self.work.addTab(self.picker,'Chèn từ ngân hàng')
        preview=QWidget();pl=QVBoxLayout(preview);pl.setContentsMargins(0,0,0,0)
        self.audience=QComboBox();self.audience.addItem('Bản giáo viên','teacher');self.audience.addItem('Bản học sinh','student');pl.addWidget(self.audience)
        self.worksheet=QCheckBox('Chỉ xuất phiếu bài tập');pl.addWidget(self.worksheet)
        self.button(pl,'Xem trước toàn bài',self.start_preview,QStyle.StandardPixmap.SP_FileDialogContentsView)
        self.button(pl,'Hủy tác vụ preview',self.cancel_preview)
        self.preview=QLabel('Tạo hoặc chọn bài để bắt đầu.');self.preview.setAlignment(Qt.AlignmentFlag.AlignTop);self.preview.setWordWrap(True)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.preview);pl.addWidget(scroll,1)
        row=QHBoxLayout();self.button(row,'← Trang',lambda:self.turn_page(-1));self.button(row,'Trang →',lambda:self.turn_page(1));pl.addLayout(row)
        self.export_button=self.button(pl,'Xuất bộ TeX + PDF',self.export,QStyle.StandardPixmap.SP_DialogSaveButton)
        splitter.addWidget(preview);splitter.setSizes([230,650,350])
        self.status=QLabel('Tạo bài từ mẫu hoặc mở một bài đã lưu.');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.autosave=QTimer(self);self.autosave.setSingleShot(True);self.autosave.setInterval(1500);self.autosave.timeout.connect(self.save)
        self.reload_list()
        if self.lesson_list.count():self.open_selected()

    def button(self, layout, text, callback, icon=None):
        b=QPushButton(text);b.clicked.connect(callback)
        if icon:
            from latex_question_studio.ui.icons import icon as svg_icon
            name={QStyle.StandardPixmap.SP_FileIcon:'lesson',QStyle.StandardPixmap.SP_DialogSaveButton:'save',QStyle.StandardPixmap.SP_FileDialogContentsView:'preview'}.get(icon,'lesson')
            b.setProperty('iconName',name);b.setIcon(svg_icon(name,'#ffffff'))
        layout.addWidget(b);return b

    def changed(self,*args):
        if self.loading or self.doc is None:return
        self.cancel_preview()
        self.dirty=True;self.status.setText('Có thay đổi • Tự lưu sau khi dừng nhập…');self.autosave.start()

    def current_block(self):
        return next((b for b in self.doc['blocks'] if b['id']==self.current_id),None) if self.doc else None

    def flush(self):
        if not self.doc:return
        self.doc['title']=self.title.text()
        b=self.current_block()
        if b:
            b.update(title=self.block_title.text(),source=self.editor.toPlainText(),policy=self.policy.currentData(),teacher_notes=self.notes.toPlainText())
            from PySide6.QtWidgets import QTreeWidgetItemIterator
            iterator=QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                item=iterator.value()
                if item.data(0,Qt.ItemDataRole.UserRole)==b['id']:
                    item.setText(0,b['title'] or KINDS[b['kind']]);break
                iterator+=1

    def reload_list(self, selected=None):
        self.lesson_list.blockSignals(True);self.lesson_list.clear()
        for row in self.service.list():self.lesson_list.addItem(row['title'],row['id'])
        if selected:self.lesson_list.setCurrentIndex(self.lesson_list.findData(selected))
        self.lesson_list.blockSignals(False)

    def open_selected(self,*args):
        key=self.lesson_list.currentData()
        if not key:return
        if self.doc and key==self.doc['id']:return
        if self.dirty and not self.save():
            self.reload_list(self.doc['id']);return
        self.load(self.service.get(key))

    def load(self,doc):
        self.cancel_preview();self.pdf=None
        self.preview.setPixmap(QPixmap());self.preview.setMinimumSize(0,0);self.preview.setText('Bấm Xem trước toàn bài để biên dịch bài đang mở.')
        self.loading=True;self.doc=doc;self.current_id=None
        self.title.setText(doc['title']);self.dirty=False;self.autosave.stop()
        self.refresh_tree();self.loading=False
        if self.tree.topLevelItemCount():self.tree.setCurrentItem(self.tree.topLevelItem(0))
        self.status.setText(f"Đã mở revision {doc['revision']} • Câu được ghim theo phiên bản, không tự đổi theo ngân hàng.")

    def reset_after_restore(self):
        self.cancel_preview();self.autosave.stop();self.loading=True
        self.doc=None;self.current_id=None;self.dirty=False
        self.tree.clear();self.title.clear();self.editor.clear();self.notes.clear();self.block_title.clear();self.origin.clear()
        self.pdf=None;self.preview.setPixmap(QPixmap());self.preview.setMinimumSize(0,0);self.preview.setText('Chọn hoặc tạo bài.')
        self.loading=False;self.reload_list();self.open_selected()

    def new_lesson(self):
        if self.dirty and not self.save():return
        doc=self.service.create();self.reload_list(doc['id']);self.load(doc)

    def duplicate(self):
        if not self.doc:return
        if not self.save():return
        import uuid
        doc=deepcopy(self.doc);doc['id']=str(uuid.uuid4());doc['revision']=0;doc['title']+=' (bản sao)'
        doc=self.service.save(doc);self.reload_list(doc['id']);self.load(doc)

    def save(self):
        self.autosave.stop()
        if not self.doc:return True
        if not self.dirty:return True
        self.flush()
        try:self.doc=self.service.save(self.doc)
        except Exception as error:self.status.setText('Chưa lưu: '+str(error));return False
        self.dirty=False;self.reload_list(self.doc['id'])
        self.status.setText(f"Đã lưu revision {self.doc['revision']} • Bản ngân hàng không bị thay đổi.")
        return True

    def refresh_tree(self,selected=None):
        self.tree.blockSignals(True);self.tree.clear()
        items={}
        for b in self.doc['blocks']:
            item=QTreeWidgetItem([b['title'] or KINDS[b['kind']]])
            item.setData(0,Qt.ItemDataRole.UserRole,b['id']);item.setToolTip(0,KINDS[b['kind']]);items[b['id']]=item
        for b in self.doc['blocks']:
            parent=items.get(b['parent'])
            if parent:parent.addChild(items[b['id']])
            else:self.tree.addTopLevelItem(items[b['id']])
        self.tree.expandAll();self.tree.blockSignals(False)
        self.current_id=None
        if selected in items:self.tree.setCurrentItem(items[selected])

    def select_block(self,item,previous=None):
        if self.loading:return
        self.flush();self.loading=True
        self.current_id=item.data(0,Qt.ItemDataRole.UserRole) if item else None
        b=self.current_block()
        self.block_title.setText(b['title'] if b else '')
        self.editor.setPlainText(b['source'] if b else '')
        self.notes.setPlainText(b['teacher_notes'] if b else '')
        self.policy.setCurrentIndex(max(0,self.policy.findData(b['policy'] if b else 'full')))
        q=b.get('question') if b else None
        self.origin.setText(('Nguồn '+q['id'][:8]+' • revision '+str(q['revision'])+' • sửa tại đây chỉ đổi bản trong bài') if q else 'Nội dung riêng của bài giảng')
        self.loading=False

    def add_block(self,child=False):
        if not self.doc:self.new_lesson()
        self.flush();current=self.current_block()
        parent=current['id'] if child and current else (current['parent'] if current else None)
        kind=self.kind.currentData();b=block(kind,KINDS[kind],parent)
        self.doc['blocks'].append(b);self.refresh_tree(b['id']);self.changed()

    def move(self,direction):
        if not self.doc:return
        self.flush();b=self.current_block()
        if not b:return
        siblings=[x for x in self.doc['blocks'] if x['parent']==b['parent']]
        index=siblings.index(b);target=index+direction
        if not 0<=target<len(siblings):return
        blocks=self.doc['blocks'];i=blocks.index(b);j=blocks.index(siblings[target]);blocks[i],blocks[j]=blocks[j],blocks[i]
        self.refresh_tree(b['id']);self.changed()

    def remove_block(self):
        b=self.current_block()
        if not b:return
        if QMessageBox.question(self,'Xóa mục','Xóa mục và các mục con khỏi bản nháp? Lịch sử đã lưu vẫn giữ.')!=QMessageBox.StandardButton.Yes:return
        removing={b['id']}
        while True:
            extra={x['id'] for x in self.doc['blocks'] if x['parent'] in removing}
            if extra<=removing:break
            removing|=extra
        self.doc['blocks']=[x for x in self.doc['blocks'] if x['id'] not in removing]
        self.refresh_tree();self.loading=True;self.current_id=None;self.editor.clear();self.block_title.clear();self.notes.clear();self.loading=False;self.changed()

    def attach_image(self):
        b=self.current_block()
        if not b:return
        path,_=QFileDialog.getOpenFileName(self,'Chèn hình','','Hình (*.png *.jpg *.jpeg *.pdf)')
        if not path:return
        try:self.editor.insertPlainText('\n'+self.service.attach_image(b,path)+'\n')
        except Exception as error:self.status.setText(str(error))

    def history(self):
        if not self.doc or not self.save():return
        rows=self.service.history(self.doc['id']);labels=[f"Revision {r['revision']} • {r['created_at']}" for r in rows]
        label,ok=QInputDialog.getItem(self,'Khôi phục bài','Chọn bản để phục hồi thành revision mới:',labels,0,False)
        if ok:self.load(self.service.restore(self.doc['id'],rows[labels.index(label)]['revision']))

    def build_picker(self):
        self.picker=QWidget();layout=QVBoxLayout(self.picker)
        self.query=QLineEdit();self.query.setPlaceholderText('Tìm nội dung / nguồn / nhãn trong ngân hàng');layout.addWidget(self.query)
        row=QHBoxLayout();self.filters={}
        for key,label in (('subject','Môn'),('grade','Khối'),('topic','Chủ đề')):
            combo=QComboBox();combo.addItem('Tất cả '+label.lower(),'');self.filters[key]=combo;row.addWidget(combo)
        self.question_type=QComboBox()
        for label,key in [('Mọi loại',''),('Trắc nghiệm','mcq'),('Đúng / Sai','true_false'),('Trả lời ngắn','short_answer'),('Tự luận','essay')]:self.question_type.addItem(label,key)
        row.addWidget(self.question_type);layout.addLayout(row)
        self.cognitive=QComboBox()
        for label,key in [('Mọi mức nhận thức',''),('Nhận biết','NB'),('Thông hiểu','TH'),('Vận dụng','VD'),('Vận dụng cao','VDC')]:self.cognitive.addItem(label,key)
        layout.addWidget(self.cognitive)
        self.button(layout,'Tìm / Làm mới danh mục',self.search_bank)
        self.bank=QTableWidget(0,3);self.bank.setHorizontalHeaderLabels(['Chọn','Nội dung nguồn','Loại'])
        self.bank.setColumnWidth(0,45);self.bank.setColumnWidth(1,340);self.bank.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.bank.cellDoubleClicked.connect(self.preview_bank);layout.addWidget(self.bank,1)
        row=QHBoxLayout();self.insert_kind=QComboBox();self.insert_kind.addItem('Bài tập vận dụng','exercise');self.insert_kind.addItem('Ví dụ','example');row.addWidget(self.insert_kind)
        self.allow_repeat=QCheckBox('Cho phép lặp có chủ đích');row.addWidget(self.allow_repeat);layout.addLayout(row)
        self.button(layout,'Chèn các câu đã chọn vào mục hiện tại',self.insert_selected)
        row=QHBoxLayout();self.count=QSpinBox();self.count.setRange(1,100);self.count.setValue(3);row.addWidget(QLabel('Số câu'));row.addWidget(self.count)
        self.seed=QSpinBox();self.seed.setRange(0,2_000_000_000);self.seed.setValue(2027);row.addWidget(QLabel('Seed'));row.addWidget(self.seed);layout.addLayout(row)
        self.button(layout,'Trích lọc → xem và tick danh sách đề xuất',self.sample_bank)
        self.picker_status=QLabel('Lọc và chọn câu; double click để preview. Mở lại bài không tự rút câu mới.');self.picker_status.setWordWrap(True);layout.addWidget(self.picker_status)

    def bank_filters(self):
        return {**{key:combo.currentData() for key,combo in self.filters.items()},'question_type':self.question_type.currentData(),'cognitive_level':self.cognitive.currentData()}

    def search_bank(self):
        with self.services.database.connect() as c:
            metadata=[json.loads(r[0]) for r in c.execute('SELECT data_json FROM question_metadata')]
        for key,combo in self.filters.items():
            current=combo.currentData();combo.blockSignals(True)
            while combo.count()>1:combo.removeItem(1)
            for value in sorted({str(m[key]) for m in metadata if m.get(key)}):combo.addItem(value,value)
            combo.setCurrentIndex(max(0,combo.findData(current)));combo.blockSignals(False)
        self.show_bank(SearchService(self.services).find(self.query.text(),self.bank_filters(),limit=100))
        self.picker_status.setText('Hiển thị tối đa 100 kết quả. Trích lọc xét toàn bộ tập phù hợp, không chỉ trang này.')

    def show_bank(self,rows,checked=None):
        self.bank_rows=rows;self.bank.setRowCount(len(rows));checked=set(checked or [])
        labels={'mcq':'Trắc nghiệm','true_false':'Đúng / Sai','short_answer':'Trả lời ngắn','essay':'Tự luận'}
        for i,q in enumerate(rows):
            check=QTableWidgetItem();check.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Checked if q.id in checked else Qt.CheckState.Unchecked);self.bank.setItem(i,0,check)
            self.bank.setItem(i,1,QTableWidgetItem(q.latex_source.replace('\n',' ')[:160]));self.bank.setItem(i,2,QTableWidgetItem(labels.get(q.question_type,q.question_type)))

    def sample_bank(self):
        if not self.doc:return
        self.flush()
        try:
            ids,total=self.service.select(self.doc,self.query.text(),self.bank_filters(),self.count.value(),self.seed.value(),self.allow_repeat.isChecked())
            rows=[self.services.questions.get(qid) for qid in ids];self.show_bank(rows,ids)
            self.pending_recipe={'text':self.query.text(),'filters':self.bank_filters(),'count':self.count.value(),'seed':self.seed.value(),'ids':ids}
            self.picker_status.setText(f'Đề xuất {len(ids)} / {total} câu khả dụng. Xem lại rồi bấm Chèn; chưa thay đổi bài.')
        except Exception as error:self.picker_status.setText(str(error))

    def insert_selected(self):
        if not self.doc:self.new_lesson()
        self.flush()
        ids=[q.id for i,q in enumerate(getattr(self,'bank_rows',[])) if self.bank.item(i,0).checkState()==Qt.CheckState.Checked]
        if not ids:self.picker_status.setText('Chưa chọn câu.');return
        try:
            self.doc=self.service.insert_questions(self.doc,ids,self.insert_kind.currentData(),self.current_id,self.allow_repeat.isChecked())
            recipe=getattr(self,'pending_recipe',None)
            if recipe:self.doc['recipes'].append({**recipe,'inserted_ids':ids});self.pending_recipe=None
            self.refresh_tree(self.doc['blocks'][-1]['id']);self.changed();self.work.setCurrentIndex(0)
            self.status.setText(f'Đã chèn {len(ids)} câu, giữ nguyên source/revision ngân hàng. Có thể sửa riêng trong bài.')
        except Exception as error:self.picker_status.setText(str(error))

    def preview_bank(self,row,*args):
        if not 0<=row<len(getattr(self,'bank_rows',[])):return
        try:
            b=self.service.question_block(self.bank_rows[row].id,'example')
            doc={'title':'Xem câu ngân hàng','blocks':[b]}
            self.launch_preview(doc,'teacher',False)
        except Exception as error:self.status.setText(str(error))

    def start_preview(self):
        if not self.doc or not self.save():return
        self.launch_preview(deepcopy(self.doc),self.audience.currentData(),self.worksheet.isChecked())

    def launch_preview(self,doc,audience,worksheet):
        self.cancel_preview();self.preview_generation+=1;generation=self.preview_generation
        self.pdf=None;self.preview.setMinimumSize(0,0)
        config=self.compiler_config();self.preview.setText('Đang biên dịch…');self.preview.setPixmap(QPixmap())
        def work(cancelled,progress):
            source,assets=self.service.body(doc,audience,worksheet)
            compiler=Compiler(self.services.config.data_dir,engine=config.get('engine','pdflatex'),preamble_file=config.get('preamble_file') or None)
            result=compiler.compile(source,assets,cancelled)
            if not result.ok:raise ValueError(result.log[-1800:])
            data,pages=Compiler.render(result.pdf)
            return generation,result.pdf,data,pages
        job=Job(work);self.preview_job=job
        job.signals.completed.connect(self.preview_ready)
        job.signals.failed.connect(lambda error:self.preview_error(generation,error))
        self.run_job(job)

    def preview_error(self,generation,error):
        if generation!=self.preview_generation:return
        self.preview_job=None;self.preview.setText(error);self.status.setText('Preview chưa đạt; xem chi tiết bên phải.')

    def preview_ready(self,payload):
        generation,pdf,data,pages=payload
        if generation!=self.preview_generation:return
        self.preview_job=None;self.pdf=pdf;self.pdf_page=0;self.pdf_pages=pages;self.display_image(data)

    def display_image(self,data):
        pixmap=QPixmap();pixmap.loadFromData(data);scaled=pixmap.scaledToWidth(max(240,self.preview.parentWidget().width()-16),Qt.TransformationMode.SmoothTransformation)
        self.preview.setText('');self.preview.setMinimumSize(scaled.size());self.preview.setPixmap(scaled)
        self.status.setText(f'Preview • Trang {self.pdf_page+1}/{self.pdf_pages}')

    def turn_page(self,direction):
        target=self.pdf_page+direction
        if not self.pdf or not 0<=target<self.pdf_pages:return
        self.pdf_page=target;generation=self.preview_generation;pdf=self.pdf
        job=Job(lambda cancelled,progress:(generation,target,Compiler.render(pdf,page=target)[0]))
        job.signals.completed.connect(self.page_ready);job.signals.failed.connect(lambda error:self.preview_error(generation,error));self.run_job(job)

    def page_ready(self,payload):
        generation,target,data=payload
        if generation==self.preview_generation and target==self.pdf_page:self.display_image(data)

    def cancel_preview(self):
        if self.preview_job:
            self.preview_job.cancelled.set()
            self.preview_job=None
        self.pdf=None
        self.preview.setPixmap(QPixmap());self.preview.setMinimumSize(0,0)
        self.preview.setText('Preview chưa cập nhật. Bấm Xem trước toàn bài.')
        self.preview_generation+=1

    def export(self):
        if not self.doc or not self.save():return
        folder=QFileDialog.getExistingDirectory(self,'Chọn nơi lưu bộ bài giảng')
        if folder:self.export_to(folder)

    def export_to(self,folder):
        if not self.doc or not self.save():return
        if getattr(self,'export_job',None):return
        doc=deepcopy(self.doc);audience=self.audience.currentData();worksheet=self.worksheet.isChecked();config=self.compiler_config()
        job=Job(lambda cancelled,progress:self.service.export(doc,folder,audience,worksheet,engine=config.get('engine','pdflatex'),preamble_file=config.get('preamble_file') or None,cancelled=cancelled))
        self.export_job=job;self.export_button.setEnabled(False);self.status.setText('Đang xuất bộ TeX/PDF và tài nguyên…')
        job.signals.completed.connect(self.export_ready);job.signals.failed.connect(self.export_failed);self.run_job(job)

    def export_ready(self,path):
        self.export_job=None;self.export_button.setEnabled(True);self.status.setText('Đã xuất đầy đủ: '+str(path))

    def export_failed(self,error):
        self.export_job=None;self.export_button.setEnabled(True);self.status.setText('Xuất chưa đạt: '+error)