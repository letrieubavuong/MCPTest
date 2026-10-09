"""Reusable lazy preview with stale-result protection and native Qt rendering."""
import json
from PySide6.QtCore import Qt,QTimer,QThreadPool,QEvent
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QScrollArea,QTabWidget,QPlainTextEdit
from latex_question_studio.ui.components.workspace import CommandToolbar
from latex_question_studio.ui.jobs import Job
from latex_question_studio.preview.compiler import Compiler

class QuestionPreview(QWidget):
    def __init__(self,services,run_job=None,parent=None):
        super().__init__(parent);self.services=services;self.run_job=run_job;self.generation=0;self.job=None;self.jobs=[];self.source='';self.assets={};self.pdf=None;self.page=0;self.total=0;self.original=None
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        bar=CommandToolbar('Preview',self);bar.command('preview','Biên dịch bản đang xem',self.compile,True);bar.command('close','Hủy preview',self.cancel);bar.command('chapter','Trang trước',lambda:self.turn(-1));bar.command('subject','Trang sau',lambda:self.turn(1));layout.addWidget(bar)
        self.status=QLabel('Chọn câu để xem trước');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.viewport().installEventFilter(self);self.image=QLabel();self.image.setAlignment(Qt.AlignmentFlag.AlignTop);self.scroll.setWidget(self.image);self.tabs.addTab(self.scroll,'Xem trước')
        self.code=QPlainTextEdit();self.code.setReadOnly(True);self.tabs.addTab(self.code,'Mã LaTeX');self.errors=QPlainTextEdit();self.errors.setReadOnly(True);self.tabs.addTab(self.errors,'Lỗi')
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(250);self.timer.timeout.connect(self.compile)
    def set_source(self,source,assets=None):
        self.cancel();self.source=source;self.assets=dict(assets or {});self.code.setPlainText(source);self.original=None;self.image.clear();self.errors.clear()
        self.status.setText('Đang chuẩn bị xem trước…' if source else 'Chọn câu để xem trước')
        if source:self.timer.start()
    def cancel(self):
        self.timer.stop();self.generation+=1;self.pdf=None
        if self.job:self.job.cancelled.set()
        self.job=None
    def compile(self):
        if not self.source or not self.services:return
        self.cancel();generation=self.generation;source=self.source;assets=self.assets.copy();self.status.setText('Đang biên dịch…')
        path=self.services.config.data_dir/'compiler.json'
        try:config=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        except (ValueError,OSError):config={}
        compiler=Compiler(self.services.config.data_dir,engine=config.get('engine','pdflatex'),preamble_file=config.get('preamble_file') or None)
        def work(cancelled,progress):
            result=compiler.compile(source,assets,cancelled)
            image,pages=Compiler.render(result.pdf) if result.ok and not cancelled() else (None,0)
            return generation,result,image,pages
        job=Job(work);self.job=job;self.jobs=[j for j in self.jobs if not j.finished.is_set()]+[job];job.signals.completed.connect(self.ready)
        job.signals.failed.connect(lambda error:self.failed(generation,error))
        self.run_job(job) if self.run_job else QThreadPool.globalInstance().start(job)
    def failed(self,generation,message):
        if generation!=self.generation:return
        self.job=None;self.errors.setPlainText(message);self.status.setText('Biên dịch lỗi — xem tab Lỗi')
    def ready(self,payload):
        generation,result,image,total=payload
        if generation!=self.generation:return
        self.job=None;self.errors.setPlainText(result.log)
        if not result.ok or not image:self.failed(generation,result.log);return
        self.pdf=result.pdf;self.page=0;self.total=total;self.show_image(image)
    def show_image(self,image):
        pix=QPixmap();pix.loadFromData(image);self.original=pix;self.fit();self.status.setText(f'Xem trước · Trang {self.page+1}/{self.total}')
    def fit(self):
        if self.original:self.image.setMinimumSize(0,0);self.image.setPixmap(self.original.scaledToWidth(max(100,self.scroll.viewport().width()-12),Qt.TransformationMode.SmoothTransformation))
    def turn(self,direction):
        target=self.page+direction
        if not self.pdf or not 0<=target<self.total:return
        generation=self.generation;pdf=self.pdf;self.page=target
        job=Job(lambda cancelled,progress:(generation,target,Compiler.render(pdf,target)[0]));self.jobs.append(job)
        job.signals.completed.connect(lambda value:self.show_image(value[2]) if value[0]==self.generation and value[1]==self.page else None)
        self.run_job(job) if self.run_job else QThreadPool.globalInstance().start(job)
    def resizeEvent(self,event):super().resizeEvent(event);QTimer.singleShot(0,self.fit)
    def closeEvent(self,event):self.cancel();super().closeEvent(event)

    def eventFilter(self,obj,event):
        if hasattr(self,'scroll') and obj==self.scroll.viewport() and event.type()==QEvent.Type.Resize:QTimer.singleShot(0,self.fit)
        return super().eventFilter(obj,event)
