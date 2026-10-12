from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow

root=Path(__file__).resolve().parents[1];data=root/'.runtime/library-cards-data';data.mkdir(parents=True,exist_ok=True);out=root/'artifacts/library-cards';out.mkdir(parents=True,exist_ok=True)
app=QApplication([]);services=create_services(AppConfig.load(data));library=LibraryService(services)
for index,level in enumerate(('NB','TH','VD','VDC','NB','TH'),1):
    q=services.questions.create(r'\begin{ex}Câu hỏi minh họa số '+str(index)+r'. Tính giá trị biểu thức $x^2+1$.\end{ex}','essay',cognitive_level=level)
    library.save_metadata(q.id,{'taxonomy_id':'curriculum:math6:lesson:01'})
window=MainWindow(services);window.resize(1366,768);window.show();window.show_page(0);window.library_ui.mode.setCurrentIndex(1);window.apply_theme();app.processEvents();time.sleep(.25);window.grab().save(str(out/'library-cards-light-1366x768.png'));window.theme='dark';window.apply_theme();app.processEvents();time.sleep(.15);window.grab().save(str(out/'library-cards-dark-1366x768.png'));window.close();app.processEvents()
