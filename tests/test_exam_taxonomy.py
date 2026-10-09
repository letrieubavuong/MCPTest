import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.exams import ExamService
from latex_question_studio.ui.exam_dialog import ExamDialog


def bank(tmp_path):
    services=create_services(AppConfig.load(tmp_path));library=LibraryService(services);ids=[]
    for i,(node,level,archived,source) in enumerate([('01','NB',False,'Câu một'),('01','TH',False,'Câu hai'),('02','NB',False,'Câu ba'),('01',None,False,'Câu bốn'),('01','NB',True,'Câu cũ')]):
        q=services.questions.create(r'\begin{ex}'+source+r'\loigiai{Giải}\end{ex}','essay');library.save_metadata(q.id,{'taxonomy_id':'curriculum:math10:lesson:'+node,'cognitive_level':level,'archived':archived});ids.append(q.id)
    return services,ids


def test_scope_statistics_exclude_manual_archived_and_generation(tmp_path):
    services,ids=bank(tmp_path);exam=ExamService(services);root='curriculum:math10'
    stats=exam.statistics(root,'essay',[ids[0]])
    assert stats['counts']=={'NB':1,'TH':1,'VD':0,'VDC':0,'unclassified':1}
    assert exam.statistics(root+':lesson:01')['counts']['NB']==1
    version,snapshot=exam.generate('Đề theo bài',matrix=[{'taxonomy_id':root+':lesson:01','filters':{'cognitive_level':'TH'},'count':1}],shuffle_options=False)
    assert [q['question_id'] for q in snapshot['questions']]==[ids[1]]
    with pytest.raises(ValueError,match='Thiếu nguồn'):exam.generate('Thiếu',matrix=[{'taxonomy_id':root+':lesson:01','filters':{'cognitive_level':'NB'},'count':2}])


def test_exam_tree_statistics_builds_scoped_matrix(qtbot,tmp_path):
    services,ids=bank(tmp_path);page=ExamDialog([],services=services);qtbot.addWidget(page)
    page.select_scope(page.tree_items['curriculum:math10:lesson:01']);assert page.stats.item(0,1).text()=='1'
    page.targets['NB'].setValue(1);page.targets['TH'].setValue(1);page.add_scope_rows()
    values=page.values();assert len(values['matrix'])==2
    assert all(row['taxonomy_id']=='curriculum:math10:lesson:01' for row in values['matrix'])
    assert [row['filters']['cognitive_level'] for row in values['matrix']]==['NB','TH']
    assert page.stats_note.text().find('chưa gán mức độ')>=0
