import sqlite3
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.search import SearchService
from latex_question_studio.domain.curriculum import ROOT_ID,chapter_id,lesson_id
from latex_question_studio.persistence.database import Database,MIGRATIONS
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.metadata_dialog import MetadataDialog


def test_khtn6_upgrade_structure_and_no_reseed_on_reopen(tmp_path):
    path=tmp_path/'schema7.db'
    with sqlite3.connect(path) as c:
        for version in range(1,8):
            for sql in MIGRATIONS[version]:c.execute(sql)
            c.execute('PRAGMA user_version='+str(version))
        c.execute("INSERT INTO taxonomy_nodes(id,kind,name) VALUES ('custom','subject','Toán riêng')")
        c.execute("INSERT INTO questions VALUES ('old','giữ nguyên','essay','',NULL,NULL,1,'now','now')")
    db=Database(path);db.initialize()
    assert db.last_backup.is_file()
    with sqlite3.connect(db.last_backup) as c:assert c.execute('PRAGMA user_version').fetchone()[0]==7
    expected_ranges=[range(1,9),range(9,12),range(12,16),range(16,18),range(18,22),range(22,25),range(25,40),range(40,46),range(46,52),range(52,56)]
    with db.connect() as c:
        assert c.execute('SELECT latex_source FROM questions').fetchone()[0]=='giữ nguyên'
        assert c.execute('SELECT count(*) FROM taxonomy_nodes').fetchone()[0]==174
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(ROOT_ID,)).fetchone()[0]=='KHTN 6'
        for number,lessons in enumerate(expected_ranges,1):
            actual={r[0] for r in c.execute('SELECT id FROM taxonomy_nodes WHERE parent_id=?',(chapter_id(number),))}
            assert actual=={lesson_id(i) for i in lessons}
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(lesson_id(55),)).fetchone()[0]=='Bài 55: Ngân hà'
    with db.transaction() as c:c.execute('UPDATE taxonomy_nodes SET name=? WHERE id=?',('Tên tùy chỉnh',lesson_id(1)))
    db.initialize()
    with db.connect() as c:
        assert c.execute('SELECT count(*) FROM taxonomy_nodes').fetchone()[0]==174
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(lesson_id(1),)).fetchone()[0]=='Tên tùy chỉnh'


def test_question_classification_subtree_filters_and_counts(tmp_path):
    services=create_services(AppConfig.load(tmp_path));library=LibraryService(services);search=SearchService(services)
    q=services.questions.create(r'\begin{ex}Đo chiều dài\end{ex}','essay')
    other=services.questions.create(r'\begin{ex}Ngân hà\end{ex}','essay')
    library.save_metadata(q.id,{'taxonomy_id':lesson_id(5),'subject':'Toán','grade':'12','chapter':'sai'})
    library.save_metadata(other.id,{'taxonomy_id':lesson_id(55)})
    metadata=library.metadata(q.id)
    assert metadata['subject']=='Khoa học tự nhiên' and metadata['grade']=='6'
    assert metadata['chapter']=='Chương 1: Mở đầu về Khoa học tự nhiên'
    assert metadata['lesson']=='Bài 5: Đo chiều dài'
    assert {r.id for r in search.find(taxonomy_id=ROOT_ID)}=={q.id,other.id}
    assert [r.id for r in search.find(taxonomy_id=chapter_id(1))]==[q.id]
    assert [r.id for r in search.find(taxonomy_id=lesson_id(5))]==[q.id]
    nodes={r['id']:r for r in library.taxonomy()}
    assert nodes[ROOT_ID]['count']==2 and nodes[chapter_id(1)]['count']==1 and nodes[lesson_id(5)]['count']==1
    library.save_metadata(q.id,{'archived':True})
    nodes={r['id']:r for r in library.taxonomy()}
    assert nodes[ROOT_ID]['count']==1 and nodes[chapter_id(1)]['count']==0
    assert search.find(taxonomy_id=chapter_id(1))==[]


def test_csdl_menu_chapter_order_and_lesson_navigation(qtbot,tmp_path):
    services=create_services(AppConfig.load(tmp_path));library=LibraryService(services)
    q=services.questions.create(r'\begin{ex}Ngân hà\end{ex}','essay');library.save_metadata(q.id,{'taxonomy_id':lesson_id(55)})
    window=MainWindow(services);qtbot.addWidget(window);window.show()
    chapters=[a.menu() for a in window.khtn6_menu.actions() if a.menu()]
    assert [m.title().split(':')[0] for m in chapters]==[f'Chương {i}' for i in range(1,11)]
    first_lessons=[a.data() for a in chapters[0].actions() if str(a.data()).startswith(ROOT_ID+':lesson:')]
    assert first_lessons==[lesson_id(i) for i in range(1,9)]
    window.show_page(4)
    action=next(a for a in chapters[9].actions() if a.data()==lesson_id(55));action.trigger()
    assert window.pages.currentIndex()==0 and window.tabs.currentIndex()==0
    assert window.selected_taxonomy==lesson_id(55)
    assert [row.id for row in window.table_model.rows]==[q.id]
    assert 'Bài 55: Ngân hà' in window.database_status.text()
    assert window.taxonomy_items[chapter_id(10)].isExpanded()
    window.save_workspace();restored=MainWindow(services);qtbot.addWidget(restored)
    assert restored.selected_taxonomy==lesson_id(55)
    assert restored.taxonomy_items[chapter_id(10)].isExpanded()
    window.close();restored.close()


def test_metadata_picker_has_context_and_syncs_curriculum(qtbot,tmp_path):
    services=create_services(AppConfig.load(tmp_path));dialog=MetadataDialog({},LibraryService(services).taxonomy());qtbot.addWidget(dialog)
    index=dialog.taxonomy.findData(lesson_id(19));dialog.taxonomy.setCurrentIndex(index)
    label=dialog.taxonomy.currentText()
    assert 'KHTN 6' in label and 'Chương 5' in label and 'Bài 19' in label
    values=dialog.values()
    assert values['subject']=='Khoa học tự nhiên' and values['grade']=='6'
    assert values['chapter']=='Chương 5: Tế bào'
    assert values['lesson']=='Bài 19: Cấu tạo và chức năng các thành phần của tế bào'

def test_math6_structure_practice_order_and_navigation(qtbot,tmp_path):
    from latex_question_studio.domain.curriculum import MATH_ROOT_ID,math_chapter_id,math_lesson_id
    services=create_services(AppConfig.load(tmp_path));library=LibraryService(services)
    nodes=library.taxonomy();math=[n for n in nodes if n['id'].startswith(MATH_ROOT_ID)]
    assert len(math)==55
    ranges=[range(1,8),range(8,13),range(13,18),range(18,21),range(21,23),range(23,28),range(28,32),range(32,38),range(38,44)]
    for chapter,indices in enumerate(ranges,1):
        actual={n['id'] for n in math if n['parent_id']==math_chapter_id(chapter) and ':lesson:' in n['id']}
        assert actual=={math_lesson_id(i) for i in indices}
    q=services.questions.create(r'\begin{ex}Phân số\end{ex}','essay');library.save_metadata(q.id,{'taxonomy_id':math_lesson_id(25)})
    assert library.metadata(q.id)['subject']=='Toán'
    assert library.metadata(q.id)['grade']=='6'
    assert library.metadata(q.id)['chapter']=='Chương 6: Phân số'
    window=MainWindow(services);qtbot.addWidget(window)
    chapters=[a.menu() for a in window.math6_menu.actions() if a.menu()]
    assert len(chapters)==9
    actions=[a for a in chapters[5].actions() if a.data() and a.data()!=math_chapter_id(6)]
    assert [a.data() for a in actions]==[math_lesson_id(23),math_lesson_id(24),MATH_ROOT_ID+':practice13',math_lesson_id(25),math_lesson_id(26),math_lesson_id(27)]
    actions[3].trigger()
    assert window.selected_taxonomy==math_lesson_id(25)
    assert [row.id for row in window.table_model.rows]==[q.id]
    actions[2].trigger();window.new_question()
    created=window.editors[window.tabs.currentWidget()]
    assert library.metadata(created.id)['lesson']=='Luyện tập chung trang 13'
    window.close()


def test_khtn7_schema9_upgrade_and_menu(qtbot,tmp_path):
    from latex_question_studio.domain.curriculum import KHTN7_ROOT_ID,khtn7_chapter_id,khtn7_lesson_id
    path=tmp_path/'schema9.db'
    with sqlite3.connect(path) as c:
        for version in range(1,10):
            for sql in MIGRATIONS[version]:c.execute(sql)
        c.execute('PRAGMA user_version=9')
        c.execute("UPDATE taxonomy_nodes SET name='Tên riêng' WHERE id=?",(lesson_id(1),))
    db=Database(path);db.initialize();assert db.last_backup.is_file()
    with db.connect() as c:
        assert c.execute('SELECT count(*) FROM taxonomy_nodes').fetchone()[0]==173
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(lesson_id(1),)).fetchone()[0]=='Tên riêng'
        assert c.execute('SELECT id FROM taxonomy_nodes WHERE id=?',(khtn7_lesson_id(1),)).fetchone() is None
        ranges=[range(2,5),range(5,8),range(8,12),range(12,15),range(15,18),range(18,21),range(21,33),range(33,36),range(36,39),range(39,43)]
        for number,indices in enumerate(ranges,1):
            actual={r[0] for r in c.execute('SELECT id FROM taxonomy_nodes WHERE parent_id=?',(khtn7_chapter_id(number),))}
            assert actual=={khtn7_lesson_id(i) for i in indices}
    services=create_services(AppConfig.load(tmp_path/'app'));library=LibraryService(services)
    q=services.questions.create(r'\begin{ex}Nguyên tử\end{ex}','essay');library.save_metadata(q.id,{'taxonomy_id':khtn7_lesson_id(2)})
    values=library.metadata(q.id);assert values['subject']=='Khoa học tự nhiên' and values['grade']=='7'
    assert values['lesson']=='Bài 2: Nguyên tử'
    window=MainWindow(services);qtbot.addWidget(window)
    chapters=[a.menu() for a in window.khtn7_menu.actions() if a.menu()]
    assert [m.title().split(':')[0] for m in chapters]==[f'Chương {i}' for i in range(1,11)]
    next(a for a in chapters[0].actions() if a.data()==khtn7_lesson_id(2)).trigger()
    assert [row.id for row in window.table_model.rows]==[q.id]
    window.close()
