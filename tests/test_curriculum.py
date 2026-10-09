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
        assert c.execute('SELECT count(*) FROM taxonomy_nodes').fetchone()[0]==642
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(ROOT_ID,)).fetchone()[0]=='KHTN 6'
        for number,lessons in enumerate(expected_ranges,1):
            actual={r[0] for r in c.execute('SELECT id FROM taxonomy_nodes WHERE parent_id=?',(chapter_id(number),))}
            assert actual=={lesson_id(i) for i in lessons}
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(lesson_id(55),)).fetchone()[0]=='Bài 55: Ngân hà'
    with db.transaction() as c:c.execute('UPDATE taxonomy_nodes SET name=? WHERE id=?',('Tên tùy chỉnh',lesson_id(1)))
    db.initialize()
    with db.connect() as c:
        assert c.execute('SELECT count(*) FROM taxonomy_nodes').fetchone()[0]==642
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
        assert c.execute('SELECT count(*) FROM taxonomy_nodes').fetchone()[0]==641
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


def test_math7_upgrade_structure_navigation_and_metadata(qtbot,tmp_path):
    from latex_question_studio.domain.curriculum import MATH7_ROOT_ID,math7_chapter_id,math7_lesson_id
    path=tmp_path/'schema10.db'
    with sqlite3.connect(path) as c:
        for version in range(1,11):
            for sql in MIGRATIONS[version]:c.execute(sql)
        c.execute('PRAGMA user_version=10')
        c.execute("UPDATE taxonomy_nodes SET name='Tên riêng' WHERE id=?",(lesson_id(1),))
    db=Database(path);db.initialize();assert db.last_backup.is_file()
    with db.connect() as c:
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(lesson_id(1),)).fetchone()[0]=='Tên riêng'
        assert c.execute('SELECT count(*) FROM taxonomy_nodes WHERE id LIKE ?', (MATH7_ROOT_ID+'%',)).fetchone()[0]==48
        ranges=[range(1,5),range(5,8),range(8,12),range(12,17),range(17,20),range(20,24),range(24,29),range(29,31),range(31,36),range(36,38)]
        for number,indices in enumerate(ranges,1):
            actual={r[0] for r in c.execute('SELECT id FROM taxonomy_nodes WHERE parent_id=?',(math7_chapter_id(number),))}
            assert actual=={math7_lesson_id(i) for i in indices}
    services=create_services(AppConfig.load(tmp_path/'app'));library=LibraryService(services)
    q=services.questions.create(r'\begin{ex}Hình lăng trụ\end{ex}','essay');library.save_metadata(q.id,{'taxonomy_id':math7_lesson_id(37)})
    values=library.metadata(q.id);assert values['subject']=='Toán' and values['grade']=='7'
    assert values['chapter']=='Chương 10: Một số hình khối trong thực tiễn'
    window=MainWindow(services);qtbot.addWidget(window)
    chapters=[a.menu() for a in window.math7_menu.actions() if a.menu()]
    assert [m.title().split(':')[0] for m in chapters]==[f'Chương {i}' for i in range(1,11)]
    next(a for a in chapters[9].actions() if a.data()==math7_lesson_id(37)).trigger()
    assert [row.id for row in window.table_model.rows]==[q.id]
    window.close()


def test_grade8_schema11_upgrade_intro_and_menu(qtbot,tmp_path):
    from latex_question_studio.domain.curriculum import KHTN8_ROOT_ID,MATH8_ROOT_ID
    path=tmp_path/'schema11.db'
    with sqlite3.connect(path) as c:
        for version in range(1,12):
            for sql in MIGRATIONS[version]:c.execute(sql)
        c.execute('PRAGMA user_version=11')
        c.execute("UPDATE taxonomy_nodes SET name='Tên riêng' WHERE id=?",(lesson_id(1),))
    db=Database(path);db.initialize();assert db.last_backup.is_file()
    with db.connect() as c:
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(lesson_id(1),)).fetchone()[0]=='Tên riêng'
        for root,count,ranges in ((KHTN8_ROOT_ID,55,[range(2,8),range(8,13),range(13,18),range(18,20),range(20,26),range(26,30),range(30,41),range(41,47)]),(MATH8_ROOT_ID,50,[range(1,6),range(6,10),range(10,15),range(15,18),range(18,21),range(21,25),range(25,30),range(30,33),range(33,38),range(38,40)])):
            assert c.execute('SELECT count(*) FROM taxonomy_nodes WHERE id LIKE ?', (root+'%',)).fetchone()[0]==count
            for number,indices in enumerate(ranges,1):
                actual={r[0] for r in c.execute('SELECT id FROM taxonomy_nodes WHERE parent_id=?',(root+f':chapter:{number:02}',))}
                assert actual=={root+f':lesson:{i:02}' for i in indices}
    services=create_services(AppConfig.load(tmp_path/'app'));library=LibraryService(services)
    window=MainWindow(services);qtbot.addWidget(window)
    intro=KHTN8_ROOT_ID+':lesson:01'
    action=next(a for a in window.khtn8_menu.actions() if a.data()==intro)
    assert action.menu() is None
    action.trigger();window.new_question();q=window.editors[window.tabs.currentWidget()]
    values=library.metadata(q.id);assert values['subject']=='Khoa học tự nhiên' and values['grade']=='8' and values['chapter']==''
    assert values['lesson'].startswith('Bài 1: Sử dụng')
    chapters=[a.menu() for a in window.math8_menu.actions() if a.menu()]
    assert len(chapters)==10
    next(a for a in chapters[9].actions() if a.data()==MATH8_ROOT_ID+':lesson:39').trigger()
    window.new_question();q=window.editors[window.tabs.currentWidget()]
    values=library.metadata(q.id);assert values['subject']=='Toán' and values['grade']=='8'
    assert values['lesson']=='Bài 39: Hình chóp tứ giác đều'
    window.close()


def test_grade9_upgrade_structure_order_and_navigation(qtbot,tmp_path):
    from latex_question_studio.domain.curriculum import KHTN9_ROOT_ID,MATH9_ROOT_ID
    path=tmp_path/'schema12.db'
    with sqlite3.connect(path) as c:
        for version in range(1,13):
            for sql in MIGRATIONS[version]:c.execute(sql)
        c.execute('PRAGMA user_version=12')
        c.execute("UPDATE taxonomy_nodes SET name='Tên riêng' WHERE id=?",(lesson_id(1),))
    db=Database(path);db.initialize();assert db.last_backup.is_file()
    with db.connect() as c:
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(lesson_id(1),)).fetchone()[0]=='Tên riêng'
        for root,count,ranges in ((KHTN9_ROOT_ID,66,[range(2,5),range(5,11),range(11,14),range(14,16),range(16,18),range(18,22),range(22,26),range(26,28),range(28,33),range(33,36),range(36,42),range(42,47),range(47,49),range(49,52)]),(MATH9_ROOT_ID,43,[range(1,4),range(4,7),range(7,11),range(11,13),range(13,18),range(18,22),range(22,25),range(25,27),range(27,31),range(31,33)])):
            assert c.execute('SELECT count(*) FROM taxonomy_nodes WHERE id LIKE ?', (root+'%',)).fetchone()[0]==count
            for number,indices in enumerate(ranges,1):
                actual={r[0] for r in c.execute('SELECT id FROM taxonomy_nodes WHERE parent_id=?',(root+f':chapter:{number:02}',))}
                assert actual=={root+f':lesson:{i:02}' for i in indices}
    services=create_services(AppConfig.load(tmp_path/'app'));library=LibraryService(services)
    window=MainWindow(services);qtbot.addWidget(window)
    chapters=[a.menu() for a in window.khtn9_menu.actions() if a.menu()]
    assert [m.title().split(':')[0] for m in chapters]==[f'Chương {i}' for i in range(1,15)]
    next(a for a in window.khtn9_menu.actions() if a.data()==KHTN9_ROOT_ID+':lesson:01').trigger()
    window.new_question();q=window.editors[window.tabs.currentWidget()]
    values=library.metadata(q.id);assert values['grade']=='9' and values['chapter']==''
    chapters=[a.menu() for a in window.math9_menu.actions() if a.menu()]
    next(a for a in chapters[5].actions() if a.data()==MATH9_ROOT_ID+':lesson:18').trigger()
    window.new_question();q=window.editors[window.tabs.currentWidget()]
    values=library.metadata(q.id);assert values['subject']=='Toán' and values['grade']=='9'
    assert values['lesson']=='Bài 18: Hàm số y = ax² (a ≠ 0)'
    window.close()


def test_upper_curricula_upgrade_membership_and_navigation(qtbot,tmp_path):
    path=tmp_path/'schema13.db'
    with sqlite3.connect(path) as c:
        for version in range(1,14):
            for sql in MIGRATIONS[version]:c.execute(sql)
        c.execute('PRAGMA user_version=13')
        c.execute("UPDATE taxonomy_nodes SET name='Tên riêng' WHERE id=?",(lesson_id(1),))
    db=Database(path);db.initialize();assert db.last_backup.is_file()
    specs=[('math10','Toán','10',[2,2,2,5,3,4,4,3,2],27,'Thực hành tính xác suất theo định nghĩa cổ điển'),('physics10','Vật lí','10',[3,9,10,5,3,2,2],34,'Khối lượng riêng. Áp suất chất lỏng'),('math11','Toán','11',[4,3,2,5,3,4,6,3,3],33,'Đạo hàm cấp hai')]
    with db.connect() as c:
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(lesson_id(1),)).fetchone()[0]=='Tên riêng'
        for key,subject,grade,counts,total,last in specs:
            root='curriculum:'+key;index=0
            for number,count in enumerate(counts,1):
                actual={r[0] for r in c.execute('SELECT id FROM taxonomy_nodes WHERE parent_id=?',(root+f':chapter:{number:02}',))}
                assert actual=={root+f':lesson:{i:02}' for i in range(index+1,index+count+1)};index+=count
            assert index==total
            assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(root+f':lesson:{total:02}',)).fetchone()[0]==f'Bài {total}: {last}'
    services=create_services(AppConfig.load(tmp_path/'app'));library=LibraryService(services)
    window=MainWindow(services);qtbot.addWidget(window)
    for key,subject,grade,counts,total,last in specs:
        menu=getattr(window,key+'_menu');chapters=[a.menu() for a in menu.actions() if a.menu()]
        assert len(chapters)==len(counts)
        next(a for a in chapters[-1].actions() if a.data()=='curriculum:'+key+f':lesson:{total:02}').trigger()
        window.new_question();q=window.editors[window.tabs.currentWidget()];values=library.metadata(q.id)
        assert values['subject']==subject and values['grade']==grade
        assert values['lesson']==f'Bài {total}: {last}'
    window.close()


def test_senior_curricula_upgrade_navigation_and_tree_icons(qtbot,tmp_path):
    path=tmp_path/'schema14.db'
    with sqlite3.connect(path) as c:
        for version in range(1,15):
            for sql in MIGRATIONS[version]:c.execute(sql)
        c.execute('PRAGMA user_version=14')
        c.execute("UPDATE taxonomy_nodes SET name='Tên riêng' WHERE id=?",(lesson_id(1),))
    db=Database(path);db.initialize();assert db.last_backup.is_file()
    specs=[('physics11','Vật lí','11',[7,8,6,5],26),('math12','Toán','12',[5,3,2,3,4],17),('physics12','Vật lí','12',[7,6,7,5],25)]
    with db.connect() as c:
        assert c.execute('SELECT name FROM taxonomy_nodes WHERE id=?',(lesson_id(1),)).fetchone()[0]=='Tên riêng'
        for key,subject,grade,counts,total in specs:
            root='curriculum:'+key;index=0
            for number,count in enumerate(counts,1):
                actual={r[0] for r in c.execute('SELECT id FROM taxonomy_nodes WHERE parent_id=?',(root+f':chapter:{number:02}',))}
                assert actual=={root+f':lesson:{i:02}' for i in range(index+1,index+count+1)};index+=count
            assert index==total
    services=create_services(AppConfig.load(tmp_path/'app'));library=LibraryService(services)
    window=MainWindow(services);qtbot.addWidget(window)
    for key,subject,grade,counts,total in specs:
        root='curriculum:'+key;menu=getattr(window,key+'_menu');chapters=[a.menu() for a in menu.actions() if a.menu()]
        assert len(chapters)==len(counts)
        next(a for a in chapters[-1].actions() if a.data()==root+f':lesson:{total:02}').trigger()
        window.new_question();q=window.editors[window.tabs.currentWidget()];values=library.metadata(q.id)
        assert values['subject']==subject and values['grade']==grade
        icons=[window.taxonomy_items[node].icon(0) for node in (root,root+':chapter:01',root+':lesson:01')]
        assert all(not icon.isNull() for icon in icons)
        assert len({icon.cacheKey() for icon in icons})==3
    window.close()


def test_tree_mouse_double_click_expands_and_collapses_without_rebuild(qtbot,tmp_path):
    from PySide6.QtCore import Qt
    window=MainWindow(create_services(AppConfig.load(tmp_path)));qtbot.addWidget(window);window.show()
    item=window.taxonomy_items[ROOT_ID];item.setExpanded(False)
    window.explorer.scrollToItem(item);qtbot.wait(100)
    position=window.explorer.visualItemRect(item).center()
    qtbot.mouseClick(window.explorer.viewport(),Qt.MouseButton.LeftButton,pos=position)
    assert window.taxonomy_items[ROOT_ID] is item
    assert not item.isExpanded()
    qtbot.mouseDClick(window.explorer.viewport(),Qt.MouseButton.LeftButton,pos=position)
    assert item.isExpanded()
    qtbot.mouseDClick(window.explorer.viewport(),Qt.MouseButton.LeftButton,pos=position)
    assert not item.isExpanded()
    window.close()
