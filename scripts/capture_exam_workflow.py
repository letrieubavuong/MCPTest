from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow

root=Path(__file__).resolve().parents[1];data=root/'.runtime/exam-workflow-data';data.mkdir(parents=True,exist_ok=True);out=root/'artifacts/exam-workflow';out.mkdir(parents=True,exist_ok=True)
app=QApplication([]);services=create_services(AppConfig.load(data));library=LibraryService(services)
for index,level in enumerate(('NB','TH','VD','VDC','NB','TH'),1):
    q=services.questions.create(r'\begin{ex}Câu '+str(index)+r' tính $x^2+1$.\end{ex}','essay',cognitive_level=level);library.save_metadata(q.id,{'taxonomy_id':'curriculum:math6:lesson:01'})
window=MainWindow(services);window.resize(1366,768);window.show();window.show_page(2);window.exam_page.set_manual_ids([q.id for q in services.questions.list_page()[:3]]);window.exam_page.add_row();row=window.exam_page.matrix.rowCount()-1;window.exam_page.matrix.item(row,3).setText('NB');window.exam_page.matrix.item(row,4).setText('2');window.exam_page.update_matrix_summary();app.processEvents();time.sleep(.2);window.grab().save(str(out/'exam-select-1366x768.png'));window.close();app.processEvents()
