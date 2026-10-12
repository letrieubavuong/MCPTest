import shutil
from copy import deepcopy

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtGui import QTextCursor

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.parsing.visual import escape_text, encode_visual_input, formula_source, recover_literal_tex
from latex_question_studio.ui.wysiwyg import VisualLatexEditor
from latex_question_studio.ui.main_window import MainWindow


EXPRESSION=r'a=\dfrac{v^2-v_0^2}{2s}'
SAMPLE=r'\subsection{NỘI DUNG BÀI GIẢNG}'+'\nCông thức tính gia tốc: $'+EXPRESSION+'$'


def test_tex_paste_is_recognized_instead_of_printed_as_literal_text(qtbot):
    editor=VisualLatexEditor(None,None,lambda: {});qtbot.addWidget(editor)
    editor.set_source('')
    mime=QMimeData();mime.setText(SAMPLE);editor.insertFromMimeData(mime)
    assert editor.source()==SAMPLE and editor.serialized()==SAMPLE
    assert any(run.kind=='math' for run in editor.runs)
    assert any(run.style.get('bold') for run in editor.runs)


@pytest.mark.parametrize('prefix',['','Existing text: '])
def test_typing_a_complete_formula_promotes_it_to_a_math_object(qtbot,prefix):
    editor=VisualLatexEditor(None,None,lambda: {});qtbot.addWidget(editor);editor.show()
    editor.set_source(prefix);editor.moveCursor(QTextCursor.MoveOperation.End)
    qtbot.keyClicks(editor,'$'+EXPRESSION+'$')
    assert editor.source()==prefix+'$'+EXPRESSION+'$'
    assert editor.serialized()==editor.source()
    assert any(run.kind=='math' for run in editor.runs)


def test_plain_symbols_and_currency_stay_plain_text():
    assert encode_visual_input('50% & $money {text}')==escape_text('50% & $money {text}')
    assert encode_visual_input('Cost $5')==escape_text('Cost $5')
    assert formula_source(EXPRESSION)=='$'+EXPRESSION+'$'
    assert formula_source('$'+EXPRESSION+'$')=='$'+EXPRESSION+'$'


def test_recovery_is_scoped_and_keeps_correct_tex_and_literal_symbols():
    before=escape_text(SAMPLE)+'\n'+escape_text('50% & $money {text}')
    recovered=recover_literal_tex(before)
    assert recovered==SAMPLE+'\n'+escape_text('50% & $money {text}')
    correct=r'$\{x\}$ and \textbf{a\_b} and \%'
    assert recover_literal_tex(correct)==correct


def test_user_can_recover_saved_literal_input_and_undo(qtbot,tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'));window=MainWindow(services);qtbot.addWidget(window)
    page=window.lesson_page;page.new_lesson();page.editor.setPlainText(escape_text(SAMPLE));assert page.save()
    original=deepcopy(page.doc);revision=page.doc['revision']
    assert page.recover_button.isVisibleTo(page.work.widget(0))
    page.recover_formula_input()
    assert page.editor.toPlainText()==SAMPLE
    assert page.save() and page.doc['revision']>revision
    assert page.service.get(original['id'])['blocks'][0]['source']==SAMPLE
    page.visual_editor.history.undo()
    assert page.editor.toPlainText()==escape_text(SAMPLE)
    window.close()


@pytest.mark.skipif(not shutil.which('pdflatex'),reason='pdfLaTeX unavailable')
def test_screenshot_formula_renders_in_both_editor_and_current_item_pdf(qtbot,tmp_path):
    import pymupdf
    services=create_services(AppConfig.load(tmp_path/'data'));window=MainWindow(services);qtbot.addWidget(window);window.show();window.show_page(4)
    page=window.lesson_page;page.new_lesson()
    mime=QMimeData();mime.setText(SAMPLE);page.visual_editor.insertFromMimeData(mime)
    assert page.editor.toPlainText()==SAMPLE
    qtbot.waitUntil(lambda:bool(page.visual_editor.images),timeout=30000)
    key=next(key for key,run in enumerate(page.visual_editor.runs) if run.kind=='math')
    size=page.visual_editor.image_size(page.visual_editor.runs[key],page.visual_editor.images[key])
    assert 28<size.height()<=80
    assert page.preview_scope.currentIndex()==0
    page.start_preview();qtbot.waitUntil(lambda:page.pdf is not None,timeout=30000)
    with pymupdf.open(page.pdf) as pdf:
        text=''.join(p.get_text() for p in pdf)
    assert 'dfrac' not in text and 'subsection' not in text
    assert 'Bài giảng mới' not in text and 'PHƯƠNG PHÁP GIẢI' not in text
    assert '2s' in text
    page.preview_scope.setCurrentIndex(1);page.start_preview();qtbot.waitUntil(lambda:page.pdf is not None,timeout=30000)
    with pymupdf.open(page.pdf) as pdf:whole=''.join(p.get_text() for p in pdf)
    assert 'Bài giảng mới' in whole
    window.close()
