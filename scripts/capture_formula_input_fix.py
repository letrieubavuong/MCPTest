"""Reproduce the reported formula entry through the visual editor and actual PDF."""
from pathlib import Path
import time
import uuid
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
import pymupdf

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.parsing.visual import escape_text
from latex_question_studio.ui.main_window import MainWindow

root=Path(__file__).resolve().parents[1]
output=root/'artifacts/formula-input-fix';output.mkdir(parents=True,exist_ok=True)
data=root/'.runtime'/('formula-input-fix-'+uuid.uuid4().hex[:8])
app=QApplication([]);services=create_services(AppConfig.load(data))
window=MainWindow(services);window.setWindowFlag(Qt.WindowType.FramelessWindowHint);window.resize(1366,768);window.show();window.show_page(4)
window.theme='light';window.apply_theme();page=window.lesson_page;page.new_lesson()
source=r'\subsection{NỘI DUNG BÀI GIẢNG}'+'\nCông thức tính gia tốc: '+r'$a=\dfrac{v^2-v_0^2}{2s}$'
page.editor.setPlainText(escape_text(source));page.sync_visual();assert page.save()
app.processEvents();assert window.grab().save(str(output/'recovery-action.png'))
page.recover_formula_input();assert page.editor.toPlainText()==source
deadline=time.monotonic()+30
while not page.visual_editor.images and time.monotonic()<deadline:app.processEvents();time.sleep(.025)
assert page.visual_editor.images
assert window.grab().save(str(output/'visual-formula.png'))
for theme in ('light','dark'):
    window.theme=theme;window.apply_theme()
    for width,height in ((1024,768),(1366,768),(1600,900)):
        window.resize(width,height);app.processEvents()
        assert window.grab().save(str(output/f'visual-{theme}-{width}.png'))
window.theme='light';window.apply_theme();window.resize(1366,768);app.processEvents()
assert window.grab().save(str(output/'visual-formula.png'))
page.audience.setCurrentIndex(1);page.start_preview()
deadline=time.monotonic()+30
while not page.pdf and time.monotonic()<deadline:app.processEvents();time.sleep(.025)
assert page.pdf,page.status.text()
with pymupdf.open(page.pdf) as pdf:text=''.join(p.get_text() for p in pdf)
assert 'dfrac' not in text and 'subsection' not in text and 'Bài giảng mới' not in text
app.processEvents();assert window.grab().save(str(output/'current-item-pdf.png'))
(output/'verification.json').write_text(json.dumps({'source':source,'source_is_tex':page.editor.toPlainText()==source,'pdf_has_literal_tex':False,'pdf_scope':'current item','pdf_text':text,'synthetic_data':str(data)},ensure_ascii=False,indent=2),encoding='utf-8')
print('Visual input and current-item student PDF verified')
window.close();app.processEvents()
