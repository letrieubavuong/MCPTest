"""Capture library navigation with synthetic questions and an owned Qt window."""
from pathlib import Path
import time,uuid,json
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QThreadPool
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.library import LibraryService
from latex_question_studio.ui.main_window import MainWindow
root=Path(__file__).resolve().parents[1];folder=root/'.runtime'/('library-fix-'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True)
app=QApplication([]);s=create_services(AppConfig.load(folder));library=LibraryService(s)
for source,lesson,level in [(r'\begin{ex}Tính $\frac{1}{2}+\frac{1}{3}$.\choice{$1$}{\True $\frac{5}{6}$}{$\frac{2}{5}$}{$\frac{1}{6}$}\loigiai{$\frac{5}{6}$.}\end{ex}','01','TH'),(r'\begin{ex}Viết tập hợp $A$ gồm các số tự nhiên nhỏ hơn $5$.\loigiai{$A=\{0;1;2;3;4\}$.}\end{ex}','01','NB'),(r'\begin{ex}Viết số $125$ theo cấu tạo thập phân.\loigiai{$125=100+20+5$.}\end{ex}','02','TH')]:
 from latex_question_studio.parsing.latex import parse_questions
 q=s.questions.create(source,question_type=parse_questions(source)[0].question_type);library.save_metadata(q.id,{'taxonomy_id':'curriculum:math6:lesson:'+lesson,'cognitive_level':level})
w=MainWindow(s);w.setWindowFlag(Qt.WindowType.FramelessWindowHint);w.resize(1366,768);w.show();w.explorer_dock.hide();w.show_page(2);w.show_page(0)
item=w.taxonomy_items['curriculum:math6:lesson:01'];ancestor=item
while ancestor:ancestor.setExpanded(True);ancestor=ancestor.parent()
w.explorer.setCurrentItem(item);w.explorer.scrollToItem(item);w.taxonomy_selected(item);w.table.selectRow(0)
def pump(seconds,until=None):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  app.processEvents();time.sleep(.01)
  if until and until():return
pump(.4);pump(15,lambda:w.preview_job is None and not w.library_ui.preview_timer.isActive())
out=root/'artifacts/library-fix';out.mkdir(exist_ok=True)
for theme in ('dark','light'):
 w.theme=theme;w.apply_theme();pump(.3);assert w.grab().save(str(out/f'library-{theme}-1366x768.png'))
 assert not w.explorer_dock.isHidden() and w.explorer_dock.width()>=240
w.taxonomy_selected(w.taxonomy_items['curriculum:math6:lesson:03']);pump(.3);w.grab().save(str(out/'library-empty-light-1366x768.png'))
report={'size':[w.width(),w.height()],'tree_visible':not w.explorer_dock.isHidden(),'tree_width':w.explorer_dock.width(),'empty_guidance_visible':w.library_ui.empty_hint.isVisible(),'profiles':sum(n['parent_id'] is None for n in library.taxonomy())}
(out/'acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8');w.close();QThreadPool.globalInstance().waitForDone(5000);print(json.dumps(report))
