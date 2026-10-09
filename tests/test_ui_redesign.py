from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox,QSplitter
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.editor import LatexEditor
from latex_question_studio.ui.import_dialog import ImportReview
from latex_question_studio.application.importing import ImportService


def test_shell_splitters_panels_and_editor_state(qtbot,tmp_path):
    s=create_services(AppConfig.load(tmp_path));q=s.questions.create(r'\begin{ex}A\end{ex}');w=MainWindow(s);qtbot.addWidget(w);w.show()
    assert w.drawer.width()==64 and w.styleSheet()==''
    assert w.library_split.count()==3 and w.library_vertical.count()==2
    e=w.open_question(q.id);e.insertPlainText('dirty ')
    for index in (1,2,4,3,0):w.show_page(index)
    assert e.document().isModified() and e.toPlainText().startswith('dirty ')
    e.document().setModified(False);w.library_split.setSizes([180,650,340]);w.preview_dock.hide();w.toggle_drawer();w.save_workspace()
    restored=MainWindow(s);qtbot.addWidget(restored);assert restored.sidebar_collapsed and restored.preview_dock.isHidden()
    restored.show();restored.toggle_drawer();assert not restored.explorer_dock.isHidden();w.close();restored.close()


def test_inline_filters_and_lazy_library_preview(qtbot,tmp_path,monkeypatch):
    s=create_services(AppConfig.load(tmp_path));s.questions.create(r'\begin{ex}Alpha $1+2$\end{ex}');s.questions.create(r'\begin{ex}Beta $3+4$\end{ex}')
    calls=[];monkeypatch.setattr(MainWindow,'compile_current',lambda self:calls.append(self.library_ui.selected_id))
    w=MainWindow(s);qtbot.addWidget(w);w.show();qtbot.wait(350);assert calls==[]
    w.library_ui.mode.setCurrentIndex(1);qtbot.wait(300);assert calls==[]
    w.library_ui.cards.setCurrentRow(0);qtbot.waitUntil(lambda:len(calls)>0);assert len(calls)==1
    w.library_ui.query.setText('Beta');qtbot.waitUntil(lambda:w.table_model.rowCount()==1)
    assert 'Beta' in w.table_model.rows[0].latex_source;w.library_ui.reset_filters();assert w.table_model.rowCount()==2;w.close()


def test_import_exclusion_persists_across_pages_and_commit(qtbot,tmp_path):
    s=create_services(AppConfig.load(tmp_path/'data'));path=tmp_path/'input.tex';path.write_text('\n'.join(r'\begin{ex}Câu '+str(i)+r'\end{ex}' for i in range(201)),encoding='utf-8')
    service=ImportService(s);batch,rows=service.stage([path]);review=ImportReview(rows,services=s);qtbot.addWidget(review);review.cancel_preview()
    review.table.item(0,0).setCheckState(Qt.CheckState.Unchecked);excluded=rows[0]['id'];review.change_page(1);review.cancel_preview();review.change_page(-1);review.cancel_preview()
    assert review.table.item(0,0).checkState()==Qt.CheckState.Unchecked and excluded not in review.selected_ids()
    assert service.commit(batch,selected_ids=review.selected_ids())==200
    assert len(s.questions.list_page(limit=500))==200
    with s.database.connect() as c:assert c.execute('SELECT status FROM import_items WHERE id=?',(excluded,)).fetchone()[0]!='committed'


def test_editor_inline_find_replace_indent_and_undo(qtbot):
    editor=LatexEditor();qtbot.addWidget(editor);editor.show();editor.setPlainText('    Alpha\nAlpha')
    editor.replace_text();assert editor.findbar.isVisible();editor.find_input.setText('Alpha');editor.replace_input.setText('Beta');editor.replace_all()
    assert editor.toPlainText()=='    Beta\nBeta';editor.undo();assert 'Alpha' in editor.toPlainText()
    editor.moveCursor(editor.textCursor().MoveOperation.Start);editor.moveCursor(editor.textCursor().MoveOperation.EndOfBlock);qtbot.keyClick(editor,Qt.Key.Key_Return)
    assert editor.toPlainText().splitlines()[1]=='    '
    editor.set_theme('light');assert editor.theme=='light';editor.hide_find();assert not editor.findbar.isVisible()


def test_exam_inspector_uses_pinned_source(qtbot,tmp_path):
    s=create_services(AppConfig.load(tmp_path));q=s.questions.create(r'\begin{ex}Original\end{ex}');w=MainWindow(s);qtbot.addWidget(w)
    snapshot={'title':'Demo','questions':[{'question_id':q.id,'source':r'\begin{ex}Pinned\end{ex}'}],'assets':{}}
    w.exam_page.show_snapshot(snapshot);w.exam_page.preview_selected(0);w.exam_page.preview.cancel()
    assert 'Pinned' in w.exam_page.preview.code.toPlainText() and 'Original' not in w.exam_page.preview.code.toPlainText()
    assert w.exam_page.workspace.count()==3;w.close()


def test_three_sizes_two_themes_and_panel_toggle(qtbot,tmp_path):
    w=MainWindow(create_services(AppConfig.load(tmp_path)));qtbot.addWidget(w);w.setWindowFlag(Qt.WindowType.FramelessWindowHint);w.show()
    for theme in ('light','dark'):
        w.theme=theme;w.apply_theme()
        for width,height in [(1366,768),(1600,900),(1920,1080)]:
            w.resize(width,height)
            for index in (0,1,2,4,3):
                w.show_page(index);qtbot.wait(10);assert (w.width(),w.height())==(width,height)
                page=w.pages.currentWidget();assert page.width()<width
    w.toggle_drawer();assert not w.explorer_dock.isHidden() and w.explorer_dock.width()>=240;w.toggle_drawer();assert not w.explorer_dock.isHidden();w.close()


def test_theme_does_not_dirty_or_cancel_lesson_preview(qtbot,tmp_path):
    w=MainWindow(create_services(AppConfig.load(tmp_path)));qtbot.addWidget(w);w.lesson_page.new_lesson();w.lesson_page.save()
    generation=w.lesson_page.preview_generation;revision=w.lesson_page.doc['revision'];w.toggle_theme()
    assert not w.lesson_page.dirty and w.lesson_page.preview_generation==generation and w.lesson_page.doc['revision']==revision
    w.close()


def test_card_selection_survives_cached_render_and_archive_revision(qtbot,tmp_path,monkeypatch):
    from PySide6.QtGui import QImage,QColor
    from PySide6.QtCore import QBuffer,QIODevice
    from latex_question_studio.preview.compiler import CompileResult
    s=create_services(AppConfig.load(tmp_path));q=s.questions.create(r'\begin{ex}A\end{ex}');w=MainWindow(s);qtbot.addWidget(w);w.show()
    w.library_ui.mode.setCurrentIndex(1);w.library_ui.cards.setCurrentRow(0);w.library_ui.preview_timer.stop()
    image=QImage(100,60,QImage.Format.Format_RGB32);image.fill(QColor('white'));buf=QBuffer();buf.open(QIODevice.OpenModeFlag.WriteOnly);image.save(buf,'PNG');data=bytes(buf.data())
    result=CompileResult(True,tmp_path/'sample.pdf','cache',True)
    w.library_ui.remember(q,q.latex_source,w.compiler_config(),result,data,1)
    assert w.selected_exam_ids()==[q.id]
    editor=w.open_question(q.id);w.library_ui.preview_timer.stop();w.cancel_preview()
    monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.StandardButton.Yes)
    w.library_ui.archive();assert editor not in w.editors and w.table_model.rowCount()==0
    assert s.questions.get(q.id).revision>q.revision;w.close()


def test_library_rejects_stale_preview(qtbot,tmp_path):
    from latex_question_studio.preview.compiler import CompileResult
    s=create_services(AppConfig.load(tmp_path));one=s.questions.create(r'\begin{ex}One\end{ex}');two=s.questions.create(r'\begin{ex}Two\end{ex}')
    w=MainWindow(s);qtbot.addWidget(w);w.library_ui.selected_id=one.id;old=w.preview_generation
    w.library_ui.select(1);w.library_ui.preview_timer.stop();text=w.preview.text()
    w.preview_ready((old,one.id,one.latex_source,CompileResult(False,None,'OLD'),None,0,0))
    assert w.preview.text()==text and 'OLD' not in w.library_ui.errors.toPlainText();w.close()


def test_library_tree_recovers_hidden_layout_and_selecting_lesson_shows_list(qtbot,tmp_path):
    from latex_question_studio.application.library import LibraryService
    s=create_services(AppConfig.load(tmp_path));q=s.questions.create(r'\begin{ex}A\end{ex}');lesson='curriculum:math6:lesson:01'
    LibraryService(s).save_metadata(q.id,{'taxonomy_id':lesson,'cognitive_level':'TH'})
    w=MainWindow(s);qtbot.addWidget(w);w.show();editor=w.open_question(q.id);editor.insertPlainText('draft ')
    w.explorer_dock.hide();w.save_workspace();editor.document().setModified(False)
    restored=MainWindow(s);qtbot.addWidget(restored);restored.show()
    assert not restored.explorer_dock.isHidden() and restored.explorer_dock.width()>=240
    w.taxonomy_selected(w.taxonomy_items[lesson]);assert w.tabs.currentIndex()==0 and w.table_model.rowCount()==1
    assert editor.toPlainText().startswith('draft ') and w.tabs.indexOf(editor)>0
    assert 'Bài 1' in w.library_ui.scope_label.text()
    assert w.table_model.data(w.table_model.index(0,2))=='TH'
    assert 'Bài 1' in w.table_model.data(w.table_model.index(0,3))
    w.close();restored.close()


def test_library_main_commands_have_labels_and_tree_survives_page_switch(qtbot,tmp_path):
    w=MainWindow(create_services(AppConfig.load(tmp_path)));qtbot.addWidget(w);w.show()
    labels={a.text() for a in w.library_ui.toolbar.actions()}
    assert {'Nhập TeX','Sửa câu','Phân loại','Xem trước','Cây CSDL'}<=labels
    w.show_page(2);w.toggle_drawer();w.show_page(0)
    assert not w.explorer_dock.isHidden()
    w.library_ui.show_all();assert w.library_ui.scope_label.text()=='Phạm vi: Toàn bộ CSDL'
    assert w.library_ui.empty_hint.isVisible() and w.library_ui.all_button.isVisible()
    w.close()
