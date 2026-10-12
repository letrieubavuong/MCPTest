from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow

root=Path(__file__).resolve().parents[1];data=root/'.runtime/lesson-workspace-data';data.mkdir(parents=True,exist_ok=True);out=root/'artifacts/lesson-workspace';out.mkdir(parents=True,exist_ok=True)
app=QApplication([]);services=create_services(AppConfig.load(data));library=LibraryService(services)
for index in range(4):
    q=services.questions.create(r'\begin{ex}Ví dụ bài giảng '+str(index+1)+r' với $x^2+1$.\end{ex}','essay',cognitive_level=('NB','TH','VD','VDC')[index]);library.save_metadata(q.id,{'taxonomy_id':'curriculum:math6:lesson:01'})
window=MainWindow(services);window.resize(1366,768);window.show();window.show_page(4);window.lesson_page.new_lesson();window.lesson_page.search_bank();app.processEvents();time.sleep(.2);window.grab().save(str(out/'lesson-workspace-1366x768.png'));window.close();app.processEvents()
