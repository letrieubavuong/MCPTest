from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import shutil
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.lessons import LessonService, block, student_source
from latex_question_studio.application.library import LibraryService
from latex_question_studio.ui.main_window import MainWindow


def setup(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'))
    return services,LessonService(services)


def test_pinned_revision_local_edits_restore_and_concurrent_save(tmp_path):
    services,lessons=setup(tmp_path)
    q=services.questions.create(r'\begin{ex}Câu gốc\loigiai{Lời giải gốc}\end{ex}','essay')
    doc=lessons.create('Bài đạo hàm');old=deepcopy(doc)
    doc=lessons.insert_questions(doc,[q.id]);doc=lessons.save(doc)
    services.questions.update(replace(q,latex_source=r'\begin{ex}Bản mới ngân hàng\end{ex}'))
    b=doc['blocks'][-1]
    assert b['question']['revision']==1 and 'Câu gốc' in b['source']
    b['source']=r'\begin{ex}Sửa riêng trong bài\end{ex}'
    doc=lessons.save(doc)
    assert 'Bản mới' in services.questions.get(q.id).latex_source
    assert lessons.get(doc['id'])['blocks'][-1]['source']==b['source']
    with pytest.raises(ValueError,match='thay đổi'):lessons.save(old)
    restored=lessons.restore(doc['id'],1)
    assert restored['revision']==4 and len(restored['blocks'])==4
    assert len(lessons.history(doc['id']))==4


def test_sampling_pinned_results_and_repeat_policy(tmp_path):
    services,lessons=setup(tmp_path);doc=lessons.create()
    ids=[services.questions.create(r'\begin{ex}Câu '+str(i)+r'\end{ex}','essay').id for i in range(5)]
    selected,total=lessons.select(doc,count=3,seed=9)
    assert total==5 and selected==lessons.select(doc,count=3,seed=9)[0]
    doc=lessons.insert_questions(doc,selected)
    with pytest.raises(ValueError,match='Thiếu nguồn'):lessons.select(doc,count=3)
    with pytest.raises(ValueError,match='đã có'):lessons.insert_questions(doc,[selected[0]])
    repeated=lessons.insert_questions(doc,[selected[0]],allow_repeat=True)
    assert len(repeated['blocks'])==len(doc['blocks'])+1
    saved=lessons.save(doc)
    assert [b['question']['id'] for b in lessons.get(saved['id'])['blocks'] if b.get('question')]==selected


def test_student_policy_keeps_public_example_and_removes_private_data(tmp_path):
    _,lessons=setup(tmp_path);doc=lessons.create()
    doc['blocks'][0]['source']='Kiến thức cơ bản'
    example=doc['blocks'][2];example['source']=r'\begin{ex}Ví dụ\loigiai{PUBLIC EXAMPLE}\end{ex}'
    example['teacher_notes']='PRIVATE NOTE'
    exercise=block('exercise','Vận dụng',source=r'\begin{ex}Câu hỏi\choice{1}{\True 2}{3}{4}\loigiai{SECRET SOLUTION}% SECRET COMMENT'+'\n'+r'\end{ex}')
    private=block('theory','PRIVATE TITLE',source='PRIVATE BLOCK');private['policy']='private'
    doc['blocks'].extend([exercise,private])
    source,_=lessons.body(doc,'student')
    assert 'PUBLIC EXAMPLE' in source
    for secret in ('PRIVATE NOTE','PRIVATE TITLE','PRIVATE BLOCK','SECRET SOLUTION','SECRET COMMENT',r'\True'):
        assert secret not in source
    worksheet,_=lessons.body(doc,'student',worksheet=True)
    assert 'PUBLIC EXAMPLE' not in worksheet and 'Câu hỏi' in worksheet
    teacher,_=lessons.body(doc,'teacher')
    assert 'PRIVATE NOTE' in teacher and 'SECRET SOLUTION' in teacher
    with pytest.raises(ValueError,match='Macro chưa'):student_source(r'\newcommand{\answer}{secret}')


def test_tree_validation_and_missing_or_changed_asset(tmp_path):
    _,lessons=setup(tmp_path);doc=lessons.create();b=doc['blocks'][0]
    b['parent']=b['id']
    with pytest.raises(ValueError,match='Cây'):lessons.save(doc)
    b['parent']=None;b['source']=r'\includegraphics{missing.png}'
    with pytest.raises(ValueError,match='Thiếu ảnh'):lessons.body(doc)
    image=Path(__file__).resolve().parents[1]/'examples/diagram.png'
    b['source']=lessons.attach_image(b,image)
    source,assets=lessons.body(doc)
    assert len(assets)==1
    next(iter(assets.values())).write_bytes(b'changed')
    with pytest.raises(ValueError,match='đổi bytes'):lessons.body(doc)


@pytest.mark.skipif(not shutil.which('pdflatex'),reason='pdfLaTeX required')
def test_real_export_student_pdf_assets_and_backup_restore(tmp_path):
    import pymupdf
    services,lessons=setup(tmp_path);doc=lessons.create('Bài giảng thử nghiệm')
    b=doc['blocks'][0];b['source']=r'Đạo hàm: $(x^2)\prime=2x$.'
    b['source']+='\n'+lessons.attach_image(b,Path(__file__).resolve().parents[1]/'examples/diagram.png')
    b['teacher_notes']='PRIVATE TEACHER'
    doc['blocks'][2]['source']=r'\begin{ex}Ví dụ mẫu\loigiai{PUBLIC EXAMPLE}\end{ex}'
    doc['blocks'].append(block('exercise','Bài tập',source=r'\begin{ex}Tính $2+2$.\shortans{PRIVATE ANSWER}\loigiai{PRIVATE SOLUTION}\end{ex}'))
    doc=lessons.save(doc)
    folder=lessons.export(doc,tmp_path/'Bộ xuất tiếng Việt','student')
    source=(folder/'main.tex').read_text(encoding='utf-8')
    assert 'PRIVATE' not in source and 'PUBLIC EXAMPLE' in source
    with pymupdf.open(folder/'bai-giang.pdf') as pdf:
        text=''.join(page.get_text() for page in pdf)
    assert 'PRIVATE' not in text and 'PUBLIC EXAMPLE' in text
    result=__import__('subprocess').run(['pdflatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape','main.tex'],cwd=folder,capture_output=True,timeout=30)
    assert result.returncode==0,result.stdout[-1200:]
    with services.database.connect() as c:managed=services.config.data_dir/c.execute('SELECT relative_path FROM lesson_exports').fetchone()[0]
    assert (managed/'bai-giang.pdf').exists()
    original_pdf=(managed/'bai-giang.pdf').read_bytes()
    backup=LibraryService(services).backup(tmp_path/'backup.zip')
    target=create_services(AppConfig.load(tmp_path/'restored'))
    LibraryService(target).restore_backup(backup)
    restored=LessonService(target).get(doc['id'])
    assert restored==doc
    assert (target.config.data_dir/managed.relative_to(services.config.data_dir)/'bai-giang.pdf').read_bytes()==original_pdf
    assert LessonService(target).body(restored,'student')[1]


def test_lesson_ui_embedded_preserves_titles_autosaves_and_uses_bank(qtbot,tmp_path):
    services,_=setup(tmp_path);q=services.questions.create(r'\begin{ex}Câu mẫu\end{ex}','essay')
    window=MainWindow(services);qtbot.addWidget(window);window.show();window.show_page(4)
    page=window.lesson_page;page.new_lesson()
    assert page.window() is window
    page.editor.setPlainText('Lý thuyết mới');page.block_title.setText('Kiến thức');page.changed()
    method=page.tree.topLevelItem(1);page.tree.setCurrentItem(method)
    assert method.text(0)=='Dạng 1: Phương pháp giải'
    assert page.tree.topLevelItem(0).text(0)=='Kiến thức'
    assert page.doc['blocks'][0]['source']=='Lý thuyết mới'
    page.search_bank();page.bank.item(0,0).setCheckState(__import__('PySide6.QtCore',fromlist=['Qt']).Qt.CheckState.Checked)
    page.insert_selected();assert page.doc['blocks'][-1]['question']['id']==q.id
    page.editor.setPlainText(r'\begin{ex}Sửa riêng\end{ex}')
    qtbot.waitUntil(lambda:not page.dirty,timeout=4000)
    assert services.questions.get(q.id).latex_source==r'\begin{ex}Câu mẫu\end{ex}'
    key=page.doc['id'];window.show_page(0);window.show_page(4)
    assert page.doc['id']==key and 'Sửa riêng' in page.editor.toPlainText()
    window.close()
    reopened=MainWindow(services);qtbot.addWidget(reopened)
    assert reopened.lesson_page.doc['id']==key
    assert reopened.lesson_page.doc['blocks'][-1]['source']==r'\begin{ex}Sửa riêng\end{ex}'
    reopened.close()

def test_close_from_lesson_page_saves_dirty_bank_editor(qtbot,tmp_path,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    services,_=setup(tmp_path);q=services.questions.create(r'\begin{ex}Original\end{ex}')
    window=MainWindow(services);qtbot.addWidget(window)
    editor=window.open_question(q.id);editor.insertPlainText('Changed ')
    window.show_page(4);window.lesson_page.new_lesson()
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.StandardButton.Save)
    assert window.close()
    assert services.questions.get(q.id).latex_source.startswith('Changed ')


def test_schema6_upgrade_preserves_question_and_backups_before_lessons(tmp_path):
    from latex_question_studio.persistence.database import Database,MIGRATIONS
    import sqlite3
    path=tmp_path/'old.db'
    with sqlite3.connect(path) as c:
        for version in range(1,7):
            for sql in MIGRATIONS[version]:c.execute(sql)
            c.execute('PRAGMA user_version='+str(version))
        c.execute("INSERT INTO questions VALUES ('q','original','essay','',NULL,NULL,1,'now','now')")
    db=Database(path);db.initialize()
    assert db.last_backup.is_file()
    with sqlite3.connect(db.last_backup) as c:assert c.execute('PRAGMA user_version').fetchone()[0]==6
    with db.connect() as c:
        assert c.execute('SELECT latex_source FROM questions').fetchone()[0]=='original'
        assert c.execute('SELECT count(*) FROM lessons').fetchone()[0]==0


def test_lesson_preview_cancel_and_load_reject_stale_results(qtbot,tmp_path):
    from latex_question_studio.ui.jobs import Job
    services,_=setup(tmp_path);window=MainWindow(services);qtbot.addWidget(window)
    page=window.lesson_page;page.new_lesson()
    job=Job(lambda cancelled,progress:None);page.preview_job=job
    generation=page.preview_generation
    page.cancel_preview()
    assert job.cancelled.is_set() and page.preview_job is None and page.pdf is None
    page.preview_error(generation,'STALE ERROR')
    assert 'STALE ERROR' not in page.preview.text()
    page.preview.setText('OLD PDF CONTENT')
    page.load(page.doc)
    assert 'OLD PDF CONTENT' not in page.preview.text()
    window.close()
