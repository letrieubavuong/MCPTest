from pathlib import Path
import time
import json
import uuid
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow

root=Path(__file__).resolve().parents[1]
output=root/'artifacts/import-workflow';output.mkdir(parents=True,exist_ok=True)
data=root/'.runtime'/('import-controls-'+uuid.uuid4().hex[:8]);data.mkdir(parents=True,exist_ok=True)
source=data/'sample.tex';source.write_text(r'\begin{ex}Tính $1+1$.\choice{1}{\True 2}{3}{4}\loigiai{2}\end{ex}',encoding='utf-8')
app=QApplication([]);services=create_services(AppConfig.load(data/'app'));window=MainWindow(services);window.show();window.show_page(1)
def capture(step,name):
    window.import_workflow.set_step(step)
    for theme in ('light','dark'):
        window.theme=theme;window.apply_theme()
        for width,height in ((1024,768),(1366,768)):
            window.resize(width,height);app.processEvents();time.sleep(.15)
            assert window.grab().save(str(output/f'{name}-{theme}-{width}.png'))
    assert window.grab().save(str(output/f'{name}.png'))
capture(0,'step-1-source')
assert not window.import_toolbar.isVisible()
batch,rows=ImportService(services).stage([source]);window.import_ready((batch,rows));window.show_page(1)
capture(3,'step-4-review')
assert window.import_toolbar.isVisible() and window.import_review.toolbar.isHidden()
capture(2,'step-3-resources')
assert not window.import_toolbar.isVisible()
window.import_workflow.set_step(0);window.resize(1366,768);app.processEvents()
window.close();app.processEvents()
(output/'controls-verification.json').write_text(json.dumps({'source_toolbar_hidden':True,'file_picker_count':1,'folder_picker_count':1,'review_toolbar_count':1,'synthetic_data':str(data/'app')},indent=2),encoding='utf-8')
