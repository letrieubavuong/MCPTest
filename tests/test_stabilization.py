from dataclasses import replace
import json
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService


def test_student_tex_removes_answers_not_only_pdf_macro(tmp_path):
    s=create_services(AppConfig.load(tmp_path/'data'));exam=ExamService(s)
    source=r'\begin{ex}% PRIVATE COMMENT'+ '\n'+r'Question\choice{a}{\True b}{c}{d}\loigiai{PRIVATE SOLUTION}\end{ex}'
    q=s.questions.create(source);_,snapshot=exam.generate('Test',manual_ids=[q.id])
    text=exam.export_tex(snapshot,tmp_path/'student.tex').read_text(encoding='utf-8')
    body=text.split(r'\begin{document}',1)[1]
    assert 'PRIVATE' not in body and r'\True' not in body and r'\loigiai' not in body
    assert 'PRIVATE SOLUTION' in exam.export_tex(snapshot,tmp_path/'teacher.tex',solutions=True).read_text(encoding='utf-8')
    assert s.questions.get(q.id).latex_source==source


def test_student_unknown_macro_rejected_instead_of_exposing_answer(tmp_path):
    s=create_services(AppConfig.load(tmp_path));exam=ExamService(s)
    q=s.questions.create(r'\begin{ex}\MyAnswer{private}\end{ex}');_,snapshot=exam.generate('Test',manual_ids=[q.id])
    with pytest.raises(ValueError,match='Macro'):exam.content(snapshot)
    assert 'MyAnswer' in exam.content(snapshot,solutions=True)


def test_analysis_cache_metadata_source_version_and_sql_statistics(tmp_path,monkeypatch):
    from latex_question_studio.persistence import analysis
    from latex_question_studio.application.library import LibraryService
    s=create_services(AppConfig.load(tmp_path));e=ExamService(s)
    q=s.questions.create(r"\begin{ex}Question\end{ex}",cognitive_level='NB')
    invalid=s.questions.create(r"\begin{ex}Broken {\end{ex}",cognitive_level='TH')
    archived=s.questions.create(r"\begin{ex}Archived\end{ex}",cognitive_level='VD')
    LibraryService(s).save_metadata(archived.id,{'archived':True})
    unknown=s.questions.create(r"\begin{ex}Unknown\end{ex}")
    calls=[];original=analysis.parse_questions
    monkeypatch.setattr(analysis,'parse_questions',lambda source:(calls.append(source),original(source))[1])
    result=e.statistics();assert result=={'counts':{'NB':1,'TH':0,'VD':0,'VDC':0,'unclassified':1},'invalid':1,'total':2}
    LibraryService(s).save_metadata(q.id,{'cognitive_level':'TH'})
    assert e.statistics()['counts']['TH']==1 and calls==[]
    assert e.statistics(exclude_ids=[q.id])['total']==1
    with s.database.transaction() as c:
        c.execute('UPDATE questions SET latex_source=? WHERE id=?',(r"\begin{ex}Changed\end{ex}",q.id))
    assert e.statistics()['total']==2 and len(calls)==1
    monkeypatch.setattr(analysis,'PARSER_VERSION',analysis.PARSER_VERSION+1)
    assert e.statistics()['total']==2 and len(calls)==4
    with pytest.raises(ValueError,match='Thiếu nguồn'):
        e.generate('Insufficient',matrix=[{'filters':{'cognitive_level':'TH'},'count':2}])


def test_different_ids_duplicate_warning_seed_and_cancel(tmp_path):
    s=create_services(AppConfig.load(tmp_path));e=ExamService(s)
    source=r"\begin{ex}Q $2+2$\choice{a}{\True b}{c}{d}\end{ex}"
    ids=[s.questions.create(source,question_type='mcq').id for _ in range(2)]
    _,a=e.generate('Test',manual_ids=ids,seed=4);_,b=e.generate('Test',manual_ids=ids,seed=4)
    assert a==b and a['duplicate_warnings'][0]['kind']=='exact'
    assert len({q['question_id'] for q in a['questions']})==2
    for q in a['questions']:
        assert q['answer']['correct_letter']==chr(65+q['permutation'].index(1))
    with pytest.raises(InterruptedError):e.generate('Cancel',manual_ids=ids,cancelled=lambda:True)
    assert len(e.history())==2


def test_schema15_upgrade_preserves_all_authoritative_tables(tmp_path):
    from latex_question_studio.application.library import LibraryService
    from latex_question_studio.persistence.database import Database
    s=create_services(AppConfig.load(tmp_path));q=s.questions.create(r"\begin{ex}Giữ nguyên\end{ex}")
    LibraryService(s).save_metadata(q.id,{'taxonomy_id':'curriculum:math6:lesson:01','tags':['giữ dấu']})
    from latex_question_studio.application.importing import ImportService
    from latex_question_studio.application.lessons import LessonService
    from PySide6.QtGui import QImage,QColor
    image=QImage(20,20,QImage.Format.Format_RGB32);image.fill(QColor('blue'));image.save(str(tmp_path/'asset.png'))
    sourcefile=tmp_path/'archive.tex';sourcefile.write_text(r'\begin{ex}\includegraphics{asset.png}\loigiai{Giữ lời giải}\end{ex}',encoding='utf-8')
    im=ImportService(s);batch,_=im.stage([sourcefile]);im.commit(batch)
    ExamService(s).generate('Snapshot preserved',manual_ids=[q.id]);LessonService(s).create('Bài giảng giữ nguyên')
    files={p:p.read_bytes() for name in ('assets','sources') for p in (s.config.data_dir/name).rglob('*') if p.is_file()}
    with s.database.transaction() as c:
        c.execute("UPDATE taxonomy_nodes SET name='Tên bài riêng' WHERE id='curriculum:math6:lesson:01'")
        c.execute('DROP TRIGGER analysis_invalidate')
        for table in ('question_analysis','curriculum_order','curriculum_profiles'):c.execute('DROP TABLE '+table)
        for index in ('ix_qt_taxonomy','ix_questions_cognitive','ix_metadata_subject_grade','ix_metadata_archived'):c.execute('DROP INDEX '+index)
        c.execute('PRAGMA user_version=15')
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        before={t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}
    db=Database(s.database.path);db.initialize();assert db.last_backup.is_file()
    with db.connect() as c:
        for table,rows in before.items():assert [tuple(r) for r in c.execute('SELECT * FROM '+table)]==rows
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
    assert all(p.read_bytes()==raw for p,raw in files.items())
    import sqlite3
    with sqlite3.connect(db.last_backup) as c:assert c.execute('PRAGMA user_version').fetchone()[0]==15


def test_external_catalog_coexists_and_dynamic_menu(tmp_path,qtbot):
    from latex_question_studio.application.library import LibraryService
    from latex_question_studio.domain.catalog import builtin_catalog
    from latex_question_studio.ui.main_window import MainWindow
    s=create_services(AppConfig.load(tmp_path));lib=LibraryService(s)
    profile={'root_id':'curriculum:newbook','subject':'Toán','grade':'7','book':'Bộ sách riêng','version':'2026',
      'nodes':[{'id':'curriculum:newbook','parent_id':None,'kind':'subject','name':'TOÁN 7 riêng','code':'NEW','display_order':1000},
      {'id':'curriculum:newbook:lesson:1','parent_id':'curriculum:newbook','kind':'lesson','name':'Bài riêng','code':'NEW1','display_order':1001}]}
    path=tmp_path/'catalog.json';path.write_text(json.dumps({'schema_version':1,'profiles':[profile]},ensure_ascii=False),encoding='utf-8')
    backup=lib.install_curriculum(path);assert backup.is_file()
    q=s.questions.create(r"\begin{ex}Example\end{ex}");lib.save_metadata(q.id,{'taxonomy_id':'curriculum:newbook:lesson:1'})
    assert lib.metadata(q.id)['subject']=='Toán' and lib.metadata(q.id)['grade']=='7'
    w=MainWindow(s);qtbot.addWidget(w);assert w.newbook_menu.title()=='TOÁN 7 riêng'
    assert len(builtin_catalog()['profiles'])==14
    profile['version']='different';path.write_text(json.dumps({'schema_version':1,'profiles':[profile]}),encoding='utf-8')
    with pytest.raises(ValueError,match='ID chương trình'):lib.install_curriculum(path)
    assert lib.metadata(q.id)['taxonomy_id']=='curriculum:newbook:lesson:1'


@pytest.mark.parametrize('macro,kind',[('choice','mcq'),('choiceTF','true_false'),('choiceTFt','true_false')])
def test_nested_multiline_math_tikz_comments_and_answer_macros(macro,kind):
    from latex_question_studio.parsing.latex import parse_questions
    source=r"\begin{ex}"+'\n% '+r'\end{ex} ignored'+'\n'+r"\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}"+'\n'+chr(92)+macro+r"{\frac{1}{\sqrt{2}}}{\True $\begin{aligned}x&=2\\y&=3\end{aligned}$}{\textbf{c}}{d}\loigiai{\frac{a}{b}}\end{ex}"
    item=parse_questions(source)[0]
    assert not item.diagnostics and item.source==source and item.question_type==kind
    assert item.answer['options'][1]['correct'] and item.solution==r"\frac{a}{b}"


def test_ambiguous_answer_macros_block_generation_and_preserve_raw(tmp_path):
    from latex_question_studio.parsing.latex import parse_questions
    source=r"\begin{ex}Q\choice{\True a}{b}{c}{d}\shortans{secret}\end{ex}"
    item=parse_questions(source)[0];assert item.diagnostics and item.source==source
    s=create_services(AppConfig.load(tmp_path));q=s.questions.create(source)
    with pytest.raises(ValueError,match='hợp lệ'):ExamService(s).generate('Ambiguous',manual_ids=[q.id])
    assert s.questions.get(q.id).latex_source==source


def test_inline_verbatim_star_and_macro_definition_not_question():
    from latex_question_studio.parsing.latex import parse_questions
    source=r"\newcommand{\fake}{\begin{ex}fake\end{ex}}"+'\n'+r"\begin{ex}\verb*|{\end{ex}| visible\end{ex}"
    items=parse_questions(source);assert len(items)==1 and not items[0].diagnostics
    assert items[0].source.startswith(r"\begin{ex}\verb*")


def test_import_cancel_rolls_back_and_duplicate_hash_lookup(tmp_path):
    from latex_question_studio.application.importing import ImportService,ImportCancelled
    s=create_services(AppConfig.load(tmp_path/'data'));im=ImportService(s)
    source=r"\begin{ex}Preserved\end{ex}"
    old=s.questions.create(source);path=tmp_path/'batch with spaces.tex';path.write_text(source+'\n'+source,encoding='utf-8')
    batch,rows=im.stage([path]);assert all(r['duplicate'] for r in rows)
    calls=[0]
    def cancel():calls[0]+=1;return calls[0]>=2
    with pytest.raises(ImportCancelled):im.commit(batch,cancelled=cancel)
    assert s.questions.count()==1
    assert len(im.pending())==2 and s.questions.get(old.id).latex_source==source
    assert im.commit(batch)==2


def test_duplicate_prefilter_matches_original_ratio(tmp_path):
    from difflib import SequenceMatcher
    from latex_question_studio.application.search import SearchService
    s=create_services(AppConfig.load(tmp_path));search=SearchService(s)
    q=s.questions.create(r"\begin{ex}Calculate 12+24\end{ex}")
    sources=[q.latex_source,q.latex_source.replace('24','25'),'z'*45,r"\begin{ex}Other text\end{ex}"]
    others=[s.questions.create(text) for text in sources]
    expected={o.id for o in others if SequenceMatcher(None,q.latex_source,o.latex_source,autojunk=False).ratio()>=.75}
    assert {r['id'] for r in search.duplicates(q.id)}==expected
    assert search.find('!!!',count_only=True)==0


def test_student_export_does_not_copy_solution_image(tmp_path):
    from PySide6.QtGui import QImage,QColor
    from latex_question_studio.application.importing import ImportService
    s=create_services(AppConfig.load(tmp_path/'data'))
    for name,color in [('question.png','blue'),('solution.png','red')]:
        image=QImage(20,20,QImage.Format.Format_RGB32);image.fill(QColor(color));image.save(str(tmp_path/name))
    source=r"\begin{ex}\includegraphics{question.png}\loigiai{\includegraphics{solution.png} SECRET}\end{ex}"
    file=tmp_path/'q.tex';file.write_text(source,encoding='utf-8');im=ImportService(s);batch,_=im.stage([file]);im.commit(batch)
    exam=ExamService(s);_,snapshot=exam.generate('Test',manual_ids=[s.questions.list_page()[0].id])
    student=exam.export_tex(snapshot,tmp_path/'student/main.tex');teacher=exam.export_tex(snapshot,tmp_path/'teacher/main.tex',solutions=True)
    assert len(list((student.parent/'assets').glob('*')))==1
    assert len(list((teacher.parent/'assets').glob('*')))==2
    assert 'SECRET' not in student.read_text(encoding='utf-8') and s.questions.list_page()[0].latex_source==source


def test_cached_answer_matches_pinned_source_when_question_edited(tmp_path,monkeypatch):
    s=create_services(AppConfig.load(tmp_path));exam=ExamService(s)
    old=r"\begin{ex}Old\choice{a}{\True b}{c}{d}\end{ex}"
    new=r"\begin{ex}New longer\choice{a}{b}{c}{\True d}\end{ex}"
    q=s.questions.create(old,'mcq');get=s.questions.get
    def racing_get(qid):
        snapshot=get(qid)
        if snapshot.revision==1:s.questions.update(replace(snapshot,latex_source=new))
        return snapshot
    monkeypatch.setattr(s.questions,'get',racing_get)
    _,snapshot=exam.generate('Pinned',manual_ids=[q.id],shuffle_questions=False,shuffle_options=False)
    question=snapshot['questions'][0]
    assert question['original_source']==old and question['source'].replace('\n','')==old and question['revision']==1
    assert question['answer']['correct_letter']=='B' and get(q.id).latex_source==new


def test_import_reuses_validated_parse_and_falls_back_for_old_pending(tmp_path,monkeypatch):
    from latex_question_studio.application.importing import ImportService
    from latex_question_studio.persistence import analysis
    s=create_services(AppConfig.load(tmp_path/'data'));im=ImportService(s);path=tmp_path/'import.tex'
    path.write_text(r"\begin{ex}Q\choice{a}{\True b}{c}{d}\end{ex}",encoding='utf-8')
    batch,rows=im.stage([path]);calls=[];parse=analysis.parse_questions
    monkeypatch.setattr(analysis,'parse_questions',lambda src:(calls.append(src),parse(src))[1])
    assert im.commit(batch)==1 and calls==[]
    q=s.questions.list_page()[0];assert analysis.parsed(s.database,q.id)[0].answer['options'][1]['correct']
    batch,rows=im.stage([path])
    with s.database.transaction() as c:
        data=json.loads(c.execute('SELECT parsed_json FROM import_items WHERE id=?',(rows[0]['id'],)).fetchone()[0]);data.pop('analysis_version')
        c.execute('UPDATE import_items SET parsed_json=? WHERE id=?',(json.dumps(data),rows[0]['id']))
    assert im.commit(batch)==1 and len(calls)==1
