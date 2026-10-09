"""Capture only an owned Qt window using synthetic, non-personal question content."""
from pathlib import Path
import uuid
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.library import LibraryService
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.import_dialog import ImportReview
root=Path(__file__).resolve().parents[1];folder=root/'.runtime'/('visual-stabilization-'+uuid.uuid4().hex[:6]);folder.mkdir(parents=True)
app=QApplication([]);s=create_services(AppConfig.load(folder))
source=r'\begin{ex}Tính $\frac{1}{2}+\frac{1}{3}$.\choice{$1$}{\True $\frac{5}{6}$}{$\frac{2}{5}$}{$\frac{1}{6}$}\loigiai{Quy đồng mẫu: $\frac{3}{6}+\frac{2}{6}=\frac{5}{6}$.}\end{ex}'
file=folder/'synthetic.tex';file.write_text(source+'\n'+r'\begin{ex}Tìm số nguyên $x$ biết $x+4=9$.\shortans{5}\loigiai{$x=9-4=5$.}\end{ex}',encoding='utf-8')
im=ImportService(s);batch,rows=im.stage([file]);im.assign_classification([r['id'] for r in rows],'curriculum:math6:lesson:01','TH')
# Reload staged classification for the review without touching any real bank.
import json
for r in rows:r['parsed']['classification']={'taxonomy_id':'curriculum:math6:lesson:01','subject':'Toán','grade':'6','cognitive_level':'TH'}
im.commit(batch);w=MainWindow(s);w.resize(1366,768);w.show();w.show_page(1)
review=ImportReview(rows,services=s);w.replace_import_content(review)
review.tree.setCurrentItem(review.items['curriculum:math6:lesson:01']);review.tree.expandToDepth(1)
out=root/'artifacts';out.mkdir(exist_ok=True)
def import_shot():
 assert w.grab().save(str(out/'stabilization-import.png'))
 w.show_page(2);w.exam_page.set_manual_ids([q.id for q in s.questions.list_page()]);w.generate_exam()
 QTimer.singleShot(1000,exam_shot)
def exam_shot():
 assert w.grab().save(str(out/'stabilization-exam.png'))
 w.close();app.quit()
QTimer.singleShot(5500,import_shot);app.exec()
print('Synthetic UI screenshots captured.')
