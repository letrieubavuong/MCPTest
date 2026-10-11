from copy import deepcopy
import shutil

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.parsing.visual import visual_runs
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.wysiwyg import VisualLatexEditor, TEX_OBJECT


CORPUS = [
    '', 'Văn bản tiếng Việt\nDòng hai\r\n\tGiữ khoảng trắng.',
    r'\section*{Lý thuyết}\textbf{Đậm \textit{nghiêng}} và $x_{12}^2$.',
    r'\begin{ex}Tính $1+1$.\choice{1}{\True 2}{3}{4}\loigiai{Hai.}\end{ex}',
    r'\begin{ex}\choiceTF{\True A}{B}{\True C}{D}\end{ex}',
    r'\begin{vidu*}\shortans[oly]{$\frac12$}\hdan{Giải}\end{vidu*}',
    r'\newcommand{\private}[1]{#1}\MyMacro[opaque]{\textbf{x}}',
    r'\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}',
    r'\includegraphics[width=.5\linewidth]{asset.png}',
    r'\verb|$%\fake{opaque}| and \verb*|\begin{ex}|',
    '% preserved comment\n' + r'\begin{itemize}\item A\item B\end{itemize}',
    r'Escapes: \% \$ \{ \} \_ \& \# and $a+\$b$.',
    r'\[\begin{pmatrix}1&2\\3&4\end{pmatrix}\]',
    r'\textbf{incomplete', r'Unclosed $math',
]


@pytest.mark.parametrize('source', CORPUS)
def test_visual_projection_preserves_all_source_bytes(qtbot, source):
    runs = visual_runs(source)
    assert ''.join(run.raw for run in runs) == source
    editor = VisualLatexEditor(None, None, lambda: {})
    qtbot.addWidget(editor)
    editor.set_source(source)
    assert editor.document().documentLayout().handlerForObject(TEX_OBJECT) is not None
    assert editor.serialized() == source


def select_text(editor, text):
    cursor = editor.document().find(text)
    assert not cursor.isNull()
    editor.setTextCursor(cursor)


def test_direct_visual_typing_formatting_undo_and_protected_answer(qtbot):
    editor = VisualLatexEditor(None, None, lambda: {})
    qtbot.addWidget(editor);editor.show()
    source = r'\begin{ex}Alpha\choice{one}{\True two}{three}{four}\loigiai{SECRET}\end{ex}'
    editor.set_source(source)
    select_text(editor, 'Alpha')
    qtbot.keyClicks(editor, 'Beta')
    assert editor.source() == source.replace('Alpha', 'Beta')
    assert editor.serialized() == editor.source()
    select_text(editor, 'Beta')
    editor.wrap_selection(r'\textbf{', '}')
    assert r'\textbf{Beta}' in editor.source()
    bold = editor.document().find('Beta').charFormat()
    assert bold.fontWeight() == QFont.Weight.Bold
    editor.history.undo()
    assert r'\textbf{Beta}' not in editor.source() and 'Beta' in editor.source()
    editor.history.redo()
    assert r'\textbf{Beta}' in editor.source()
    before = editor.source()
    editor.selectAll()
    qtbot.keyClick(editor, Qt.Key.Key_Backspace)
    assert editor.source() == before and editor.serialized() == before
    assert r'\True two' in editor.source() and r'\loigiai{SECRET}' in editor.source()


def test_paste_escapes_text_and_preserves_opaque_nodes(qtbot):
    from PySide6.QtCore import QMimeData
    editor = VisualLatexEditor(None, None, lambda: {})
    qtbot.addWidget(editor)
    source = r'Original \Custom{raw}{data} $x^2$'
    editor.set_source(source)
    select_text(editor, 'Original')
    data = QMimeData();data.setText('50% & $money {text}')
    editor.insertFromMimeData(data)
    assert editor.source().startswith(r'50\% \& \$money \{text\}')
    assert r'\Custom{raw}{data} $x^2$' in editor.source()


def test_insert_formula_replace_selection_and_unicode_source_offsets(qtbot):
    editor=VisualLatexEditor(None,None,lambda: {})
    qtbot.addWidget(editor)
    editor.set_source('Đây là 😀 ví dụ với Alpha.')
    select_text(editor,'Alpha');editor.insert_tex(r'$\frac{1}{2}$')
    assert editor.source()=='Đây là 😀 ví dụ với '+r'$\frac{1}{2}$'+'.'
    assert editor.serialized()==editor.source()
    editor.history.undo();assert editor.source()=='Đây là 😀 ví dụ với Alpha.'
    select_text(editor,'ví dụ');editor.wrap_selection(r'\textit{','}')
    assert editor.source()=='Đây là 😀 '+r'\textit{ví dụ}'+' với Alpha.'


def test_nested_styles_and_lists_are_visual_but_source_is_lossless(qtbot):
    editor=VisualLatexEditor(None,None,lambda: {})
    qtbot.addWidget(editor)
    source=r'\section*{Title}\begin{itemize}\item \textbf{One}\item Two\end{itemize}'
    editor.set_source(source)
    select_text(editor,'One');qtbot.keyClicks(editor,'Three')
    assert editor.source()==source.replace('One','Three')
    assert editor.serialized()==editor.source()


def test_stale_inline_render_is_ignored_after_switching_source(qtbot,tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'));jobs=[]
    editor=VisualLatexEditor(services,jobs.append,lambda: {})
    qtbot.addWidget(editor);editor.set_source(r'$x^2$')
    job=jobs[0];generation=editor.generation
    editor.set_source('Next block')
    assert job.cancelled.is_set()
    job.signals.completed.emit((generation,[(0,'stale',b'not a png')]))
    assert editor.images=={} and editor.source()=='Next block'


def test_formula_object_can_be_opened_from_both_cursor_sides(qtbot,monkeypatch):
    editor=VisualLatexEditor(None,None,lambda: {})
    qtbot.addWidget(editor);editor.set_source(r'Text $x^2$ end')
    pieces=editor._pieces();key,_,position=next(piece for piece in pieces if piece[0] is not None and piece[0]>=0 and editor.runs[int(piece[0])].kind=='math')
    opened=[];monkeypatch.setattr(editor,'open_tex_dialog',opened.append)
    assert editor.edit_object(position) and editor.edit_object(position+1)
    assert opened==[key,key]


def test_lesson_switching_modes_preserves_undo_and_theme_does_not_dirty(qtbot,tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'))
    window=MainWindow(services);qtbot.addWidget(window)
    page=window.lesson_page;page.new_lesson()
    page.editor.setPlainText('Alpha');page.sync_visual();page.visual_sync.stop()
    select_text(page.visual_editor,'Alpha');qtbot.keyClicks(page.visual_editor,'Beta')
    assert page.save();revision=page.doc['revision']
    page.edit_mode.setCurrentIndex(1);page.edit_mode.setCurrentIndex(0)
    assert page.visual_editor.history.canUndo()
    window.toggle_theme();assert not page.dirty and page.doc['revision']==revision
    page.visual_editor.history.undo();assert page.editor.toPlainText()=='Alpha'
    assert page.dirty;page.save();window.close()


def test_lesson_visual_source_sync_autosave_block_switch_and_pinned_question(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path/'data'))
    window = MainWindow(services);qtbot.addWidget(window);window.show();window.show_page(4)
    page = window.lesson_page;page.new_lesson()
    assert page.edit_mode.currentIndex() == 0
    page.editor.setPlainText(r'\textbf{Alpha} \CustomMacro{untouched}')
    qtbot.waitUntil(lambda: 'Alpha' in page.visual_editor.toPlainText())
    select_text(page.visual_editor, 'Alpha');qtbot.keyClicks(page.visual_editor, 'Beta')
    assert page.editor.toPlainText() == r'\textbf{Beta} \CustomMacro{untouched}'
    qtbot.waitUntil(lambda: not page.dirty, timeout=4500)
    first = page.doc['blocks'][0]['id']
    assert services.database.path.is_file()
    assert page.service.get(page.doc['id'])['blocks'][0]['source'] == page.editor.toPlainText()
    page.tree.setCurrentItem(page.tree.topLevelItem(1))
    assert 'Beta' not in page.visual_editor.toPlainText()
    page.tree.setCurrentItem(page.tree.topLevelItem(0))
    assert 'Beta' in page.visual_editor.toPlainText() and page.current_id == first
    page.edit_mode.setCurrentIndex(1)
    page.editor.setPlainText('Source mode change')
    page.edit_mode.setCurrentIndex(0)
    assert 'Source mode change' in page.visual_editor.toPlainText()
    question = services.questions.create(r'\begin{ex}Pinned question\end{ex}', 'essay')
    page.search_bank()
    row = next(i for i, q in enumerate(page.bank_rows) if q.id == question.id)
    page.bank.item(row,0).setCheckState(Qt.CheckState.Checked)
    page.insert_selected()
    select_text(page.visual_editor, 'Pinned question');qtbot.keyClicks(page.visual_editor, 'Lesson copy')
    assert page.save()
    assert services.questions.get(question.id).latex_source == r'\begin{ex}Pinned question\end{ex}'
    key = page.doc['id'];window.close()
    restored = MainWindow(services);qtbot.addWidget(restored)
    assert 'Lesson copy' in restored.lesson_page.service.get(key)['blocks'][-1]['source']
    restored.close()


@pytest.mark.skipif(not shutil.which('pdflatex'), reason='pdfLaTeX unavailable')
def test_visual_formula_render_and_pdf_export(qtbot, tmp_path):
    import pymupdf
    services = create_services(AppConfig.load(tmp_path/'data'))
    window = MainWindow(services);qtbot.addWidget(window);window.show();window.show_page(4)
    page = window.lesson_page;page.new_lesson()
    page.editor.setPlainText(r'\textbf{Visible lesson} $\frac{1}{2}+\sqrt{4}$')
    qtbot.waitUntil(lambda: bool(page.visual_editor.images), timeout=30000)
    image = next(iter(page.visual_editor.images.values()))
    assert not image.isNull() and image.width()>5 and image.height()>5
    assert page.save()
    target = page.service.export(deepcopy(page.doc), tmp_path/'export')
    with pymupdf.open(target/'bai-giang.pdf') as pdf:
        assert 'Visible lesson' in ''.join(p.get_text() for p in pdf)
    window.close()
