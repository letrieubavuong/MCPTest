"""The lesson document is persisted as a structured set of TeX source files."""
from pathlib import Path
import shutil

import pytest

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.lessons import LessonService, block
from latex_question_studio.application.services import create_services


def setup(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'))
    return services,LessonService(services)


def test_new_lesson_has_theory_method_example_and_exercise_file_manifest(tmp_path):
    services,lessons=setup(tmp_path)
    doc=lessons.create('Cấu trúc bài')
    files=lessons.file_manifest(doc)
    assert [item['role'] for item in files]==['theory','method','exercise']
    assert files[0]['filename']=='theory.tex'
    assert files[1]['block_ids']==[doc['blocks'][1]['id'],doc['blocks'][2]['id']]
    assert files[2]['filename']=='bai-tap-van-dung.tex'
    with services.database.connect() as connection:
        rows=connection.execute('SELECT role,filename,locked FROM lesson_files WHERE lesson_id=? ORDER BY position',(doc['id'],)).fetchall()
        assert [(row['role'],row['filename'],row['locked']) for row in rows]==[(entry['role'],entry['filename'],1) for entry in files]


def test_legacy_document_gets_manifest_without_losing_blocks(tmp_path):
    services,lessons=setup(tmp_path)
    doc=lessons.create('Bài cũ')
    legacy=dict(doc);legacy.pop('files',None);legacy.pop('file_model_version',None)
    with services.database.transaction() as c:
        import json
        c.execute('UPDATE lessons SET document_json=? WHERE id=?',(json.dumps(legacy,ensure_ascii=False),doc['id']))
    restored=lessons.get(doc['id'])
    assert len(restored['blocks'])==len(doc['blocks'])
    assert {item['role'] for item in restored['files']}=={'theory','method','exercise'}


@pytest.mark.skipif(not shutil.which('pdflatex'),reason='pdfLaTeX required')
def test_export_writes_separate_tex_files_and_main_inputs_them(tmp_path):
    _,lessons=setup(tmp_path)
    doc=lessons.create('Bài có nhiều file')
    doc['blocks'][0]['source']='Nội dung lý thuyết'
    doc['blocks'][1]['source']='Phương pháp giải'
    doc['blocks'][2]['source']=r'\begin{ex}Ví dụ công khai\end{ex}'
    doc['blocks'].append(block('exercise','Bài tập vận dụng',source=r'\begin{ex}Bài tập\shortans{PRIVATE}\end{ex}'))
    doc=lessons.save(doc)
    folder=lessons.export(doc,tmp_path/'export','student')
    main=(folder/'main.tex').read_text(encoding='utf-8')
    files=lessons.file_manifest(doc)
    assert all((folder/item['filename']).is_file() for item in files)
    assert all(r'\input{'+item['filename'][:-4]+'}' in main for item in files)
    assert 'PRIVATE' not in main
    assert 'Ví dụ công khai' in (folder/next(item['filename'] for item in files if item['role']=='method')).read_text(encoding='utf-8')
    assert 'Bài tập' in (folder/'bai-tap-van-dung.tex').read_text(encoding='utf-8')


def test_file_sources_keep_method_examples_together(tmp_path):
    _,lessons=setup(tmp_path)
    doc=lessons.create('Dạng toán')
    method=doc['blocks'][1];example=doc['blocks'][2]
    method['source']='Các bước'
    example['source']=r'\begin{ex}Ví dụ\end{ex}'
    method_file=next(item for item in lessons.file_sources(doc) if item[0]['role']=='method')
    assert 'Các bước' in method_file[1] and 'Ví dụ' in method_file[1]


def test_exercise_file_records_pinned_revision_and_export_index(tmp_path):
    services,lessons=setup(tmp_path)
    question=services.questions.create(r'\begin{ex}Câu 1\end{ex}','essay')
    doc=lessons.insert_questions(lessons.create('Có bài tập'),[question.id])
    doc=lessons.save(doc)
    with services.database.connect() as connection:
        file=connection.execute("SELECT id,locked FROM lesson_files WHERE lesson_id=? AND role='exercise'",(doc['id'],)).fetchone()
        row=connection.execute('SELECT position,export_index,question_id,revision,source_snapshot,locked FROM lesson_file_exercises WHERE file_id=?',(file['id'],)).fetchone()
    assert tuple(row)==(0,1,question.id,question.revision,question.latex_source,1)
    unlocked=lessons.lock_file(doc,'exercise',False);lessons.save(unlocked)
    with services.database.connect() as connection:
        assert connection.execute("SELECT locked FROM lesson_files WHERE lesson_id=? AND role='exercise'",(doc['id'],)).fetchone()[0]==0
    with pytest.raises(ValueError,match='chốt file'):
        lessons.export(unlocked,tmp_path/'blocked-export','teacher')
