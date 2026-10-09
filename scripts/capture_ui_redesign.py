"""Capture owned Qt windows with synthetic questions, never the user's bank."""
from pathlib import Path
import json,time,uuid
from PySide6.QtWidgets import QApplication,QToolBar
from PySide6.QtCore import QThreadPool,Qt
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.import_dialog import ImportReview
root=Path(__file__).resolve().parents[1];folder=root/'.runtime'/('ui-fixture-'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True)
app=QApplication([]);services=create_services(AppConfig.load(folder))
source=r'\begin{ex}Tính $\frac{1}{2}+\frac{1}{3}$.\choice{$1$}{\True $\frac{5}{6}$}{$\frac{2}{5}$}{$\frac{1}{6}$}\loigiai{Quy đồng mẫu: $\frac{3}{6}+\frac{2}{6}=\frac{5}{6}$.}\end{ex}'
file=folder/'Cau hoi minh hoa.tex';file.write_text('\n'.join([source,r'\begin{ex}Tìm số nguyên $x$ biết $x+4=9$.\shortans{5}\loigiai{$x=5$.}\end{ex}',r'\begin{ex}Tính diện tích hình vuông cạnh $a=3$ cm.\loigiai{$S=a^2=9$ cm$^2$.}\end{ex}']),encoding='utf-8')
im=ImportService(services);batch,rows=im.stage([file]);im.assign_classification([r['id'] for r in rows],'curriculum:math6:lesson:01','TH');im.commit(batch)
for r in rows:r['parsed']['classification']={'taxonomy_id':'curriculum:math6:lesson:01','cognitive_level':'TH','subject':'Toán','grade':'6'}
w=MainWindow(services);w.setWindowFlag(Qt.WindowType.FramelessWindowHint);w.show();w.resize(1366,768)
def pump(seconds=.2,until=None):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  app.processEvents();time.sleep(.01)
  if until and until():return
w.import_ready((batch,rows));review=w.import_review;w.import_progress.setRange(0,100);w.import_progress.setValue(100);review.tree.setCurrentItem(review.items['curriculum:math6:lesson:01']);review.tree.expandToDepth(1)
w.lesson_page.new_lesson();w.lesson_page.editor.setPlainText(source);w.lesson_page.changed();w.lesson_page.save()
w.exam_page.set_manual_ids([q.id for q in services.questions.list_page()]);w.generate_exam();pump(15,lambda:getattr(w,'exam_job',None) is None)
w.show_page(0);w.table.selectRow(0);pump(15,lambda:w.preview_job is None and bool(w.preview.pixmap()))
editor=w.open_question(w.table_model.rows[0].id);pump(10,lambda:w.preview_job is None)
w.lesson_page.start_preview();pump(15,lambda:w.lesson_page.preview_job is None)
pump(15,lambda:review.preview_job is None and not review.preview_timer.isActive())
out=root/'artifacts'/'ui-redesign';out.mkdir(parents=True,exist_ok=True);measurements=[]
for theme in ['dark','light']:
 w.theme=theme;w.apply_theme()
 for width,height in [(1366,768),(1600,900),(1920,1080)]:
  w.resize(width,height);pump(.3)
  for name,index in [('csdl',0),('editor',0),('import',1),('exam',2),('lessons',4),('settings',3)]:
   w.show_page(index)
   if index==0:w.tabs.setCurrentIndex(0 if name=='csdl' else 1)
   pump(.3)
   if index==0:pump(8,lambda:w.preview_job is None and not w.library_ui.preview_timer.isActive())
   path=out/f'{name}-{theme}-{width}x{height}.png';assert w.grab().save(str(path))
   toolbars=[{'title':bar.windowTitle(),'width':bar.width(),'height':bar.height()} for bar in w.pages.currentWidget().findChildren(QToolBar) if bar.isVisible()]
   measurements.append({'screen':name,'theme':theme,'requested':[width,height],'actual':[w.width(),w.height()],'toolbar':toolbars,'image':path.name})
w.show_page(0);w.tabs.setCurrentIndex(0);w.library_ui.mode.setCurrentIndex(1);w.library_ui.cards.setCurrentRow(0);w.resize(1366,768);pump(8,lambda:w.preview_job is None and not w.library_ui.preview_timer.isActive());w.grab().save(str(out/'cards-light-1366x768.png'))
# Contact sheet uses only synthetic captures for visual inspection; originals remain available.
from PySide6.QtGui import QImage,QPainter,QColor,QFont
for theme in ('dark','light'):
 sheet=QImage(960,840,QImage.Format.Format_RGB32);sheet.fill(QColor('#eeeeee'));painter=QPainter(sheet);painter.setFont(QFont('Segoe UI',11))
 for i,name in enumerate(('csdl','editor','import','exam','lessons','settings')):
  x=(i%2)*480;y=(i//2)*280;painter.drawText(x+8,y+20,name+' · '+theme);capture=QImage(str(out/f'{name}-{theme}-1366x768.png'));painter.drawImage(x,y+25,capture.scaled(480,250,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
 painter.end();sheet.save(str(out/f'contact-{theme}.png'))
(out/'measurements.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2),encoding='utf-8')
w.close();QThreadPool.globalInstance().waitForDone(5000)
print(json.dumps({'screenshots':len(measurements)+1,'wrong_size':[m for m in measurements if m['requested']!=m['actual']]},ensure_ascii=False))
