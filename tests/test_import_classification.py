import json
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.library import LibraryService
from latex_question_studio.ui.import_dialog import ImportReview


def staged(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'));path=tmp_path/'questions.tex'
    path.write_text(r"\begin{ex}Câu một\loigiai{Giải}\end{ex}"+'\n'+r"\begin{ex}Câu hai\loigiai{Giải}\end{ex}",encoding='utf-8')
    importer=ImportService(services);batch,results=importer.stage([path]);return services,importer,batch,results


def test_classification_persists_repair_commit_snapshot_and_atomic_failure(tmp_path):
    services,importer,batch,results=staged(tmp_path);library=LibraryService(services)
    topic=library.add_taxonomy('Tính điện trở','topic','curriculum:physics11:lesson:23')
    ids=[r['id'] for r in results];importer.assign_classification(ids,topic,'TH')
    with pytest.raises(ValueError):importer.assign_classification([ids[0],'missing'],topic,'VD')
    assert json.loads(importer.pending()[0]['parsed_json'])['classification']['cognitive_level']=='TH'
    importer.repair(ids[0],results[0]['source']);assert importer.commit(batch)==2
    assert importer.commit(batch)==0
    with services.database.connect() as c:
        rows=c.execute('SELECT * FROM questions').fetchall()
        for q in rows:
            values=library.metadata(q['id']);assert values['subject']=='Vật lí' and values['grade']=='11'
            assert values['topic']=='Tính điện trở' and values['lesson']=='Bài 23: Điện trở. Định luật Ôm'
            assert q['cognitive_level']=='TH'
            assert c.execute('SELECT taxonomy_id FROM question_taxonomy WHERE question_id=?',(q['id'],)).fetchone()[0]==topic
            snapshot=json.loads(c.execute('SELECT snapshot_json FROM question_revisions WHERE question_id=?',(q['id'],)).fetchone()[0]);assert snapshot['metadata']['taxonomy_id']==topic


def test_review_tree_assign_multiple_filter_and_reopen(qtbot,tmp_path):
    services,importer,batch,results=staged(tmp_path)
    review=ImportReview(results,services=services);qtbot.addWidget(review);review.show()
    review.tree.setCurrentItem(review.items['curriculum:math10:lesson:01']);review.level.setCurrentIndex(review.level.findData('NB'))
    review.assign_rows([0,1]);assert all(r['parsed']['classification']['grade']=='10' for r in results)
    review.only_missing.setCurrentIndex(1);assert review.table.rowCount()==0
    review.only_missing.setCurrentIndex(2);assert not review.table.isRowHidden(0)
    assert all(json.loads(r['parsed_json'])['classification']['cognitive_level']=='NB' for r in importer.pending())
    review.tree_search.setText('Mệnh đề');assert not review.items['curriculum:math10:lesson:01'].isHidden()
    review.close()


def test_review_toolbar_and_real_preview(qtbot,tmp_path):
    import shutil
    if not shutil.which('pdflatex'):pytest.skip('TeX engine unavailable')
    services,importer,batch,results=staged(tmp_path)
    review=ImportReview(results,services=services);qtbot.addWidget(review);review.show()
    assert review.preview_tabs.tabText(0)=='Xem trước' and review.preview_tabs.tabText(1)=='Mã LaTeX'
    assert all(action.toolTip() for action in review.toolbar.actions() if not action.isSeparator())
    qtbot.waitUntil(lambda:bool(review.preview_pages),timeout=30000)
    assert not review.preview_image.pixmap().isNull()
    assert review.preview_page_label.text()=='1 / 1'
    review.close()


def test_review_ignores_stale_preview_result(qtbot,tmp_path):
    from types import SimpleNamespace
    services,importer,batch,results=staged(tmp_path);review=ImportReview(results,services=services);qtbot.addWidget(review)
    generation=review.preview_generation;review.show_source(1)
    review.preview_ready((generation,SimpleNamespace(ok=True),[b'invalid old image']))
    assert review.preview_pages==[]
    review.close()
