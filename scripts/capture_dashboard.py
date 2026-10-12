from pathlib import Path
import time
import uuid
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.library import LibraryService
from latex_question_studio.ui.main_window import MainWindow

root=Path(__file__).resolve().parents[1];output=root/'artifacts/dashboard';output.mkdir(parents=True,exist_ok=True)
data_dir=root/'.runtime'/('dashboard-data-'+uuid.uuid4().hex[:8])
app=QApplication([]);services=create_services(AppConfig.load(data_dir))
subjects=('Toán','Vật lí','KHTN')
levels=('NB','TH','VD','VDC')
for index in range(24):
    source=rf'\begin{{ex}}Câu hỏi mẫu {index + 1}: tính giá trị biểu thức $x+{index}$.\end{{ex}}'
    question=services.questions.create(source,'mcq',cognitive_level=levels[index % len(levels)])
    LibraryService(services).save_metadata(question.id,{'subject':subjects[index % len(subjects)],'grade':'8','chapter':'Chương mẫu'})
archived=services.questions.list_page(limit=1)[0]
LibraryService(services).save_metadata(archived.id,{'archived':True})
window=MainWindow(services);window.show();window.open_dashboard()
for theme in ('light','dark'):
    window.theme=theme;window.apply_theme()
    for width,height in ((1024,768),(1366,768),(1600,900)):
        window.resize(width,height);app.processEvents();time.sleep(.2)
        assert window.grab().save(str(output/f'{theme}-{width}x{height}.png'))
window.close();app.processEvents()
