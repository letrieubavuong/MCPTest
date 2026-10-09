import json,time
from PySide6.QtCore import QTimer,QThreadPool
from PySide6.QtWidgets import QLabel,QToolBar
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.import_dialog import ImportReview


def test_statistics_worker_cancel_stale_scope_and_timer(qtbot,tmp_path,monkeypatch):
    from latex_question_studio.application.exams import ExamService
    def statistics(self,taxonomy_id=None,question_type='',exclude_ids=None,cancelled=lambda:False):
        if taxonomy_id is None:
            while not cancelled():time.sleep(.005)
            raise InterruptedError('Đã hủy')
        return {'counts':{'NB':7,'TH':0,'VD':0,'VDC':0,'unclassified':0},'invalid':0,'total':7}
    monkeypatch.setattr(ExamService,'statistics',statistics)
    w=MainWindow(create_services(AppConfig.load(tmp_path)));qtbot.addWidget(w);w.show();w.show_page(2)
    ticks=[];timer=QTimer();timer.timeout.connect(lambda:ticks.append(1));timer.start(5)
    page=w.exam_page;page.scope='curriculum:math6';page.refresh_statistics()
    qtbot.waitUntil(lambda:page.available is not None,timeout=5000);qtbot.wait(30);timer.stop()
    assert page.available['total']==7 and page.stats.item(0,1).text()=='7' and ticks
    assert page.scope_action.isEnabled();w.close()


def test_review_pagination_assignment_and_replacement_cancel(qtbot,tmp_path):
    from latex_question_studio.application.importing import ImportService
    s=create_services(AppConfig.load(tmp_path/'data'));path=tmp_path/'batch.tex'
    path.write_text('\n'.join(r"\begin{ex}Q"+str(i)+r"\end{ex}" for i in range(401)),encoding='utf-8')
    _,rows=ImportService(s).stage([path]);w=MainWindow(s);qtbot.addWidget(w);review=ImportReview(rows,services=s)
    w.replace_import_content(review);review.cancel_preview();assert review.table.rowCount()==200
    review.change_page(1);review.cancel_preview();assert review.visible_indices[0]==200
    review.tree.setCurrentItem(review.items['curriculum:math6:lesson:01']);review.level.setCurrentIndex(review.level.findData('VD'))
    review.table.selectRow(0);review.assign_selected();review.cancel_preview()
    assert rows[200]['parsed']['classification']['cognitive_level']=='VD' and 'classification' not in rows[0]['parsed']
    review.change_page(1);review.cancel_preview();assert review.table.rowCount()==1 and review.visible_indices==[400]
    generation=review.preview_generation;w.replace_import_content(QLabel('Khác'))
    assert review.preview_generation>generation and not review.preview_timer.isActive();w.close()


def test_toolbar_layout_all_pages_at_three_sizes(qtbot,tmp_path):
    w=MainWindow(create_services(AppConfig.load(tmp_path)));qtbot.addWidget(w);w.show()
    for width,height in [(1024,768),(1366,768),(1920,1080)]:
        w.resize(width,height)
        for index in range(w.pages.count()):
            w.show_page(index);qtbot.wait(30)
            page=w.pages.currentWidget();assert page.width()>0 and page.height()>0
            for toolbar in page.findChildren(QToolBar):
                if toolbar.isVisible():
                    assert toolbar.width()<=page.width() and toolbar.height()<100
                    assert toolbar.geometry().top()>=0
    w.close()


def test_import_preview_ignores_old_result_after_switch_and_cancel(qtbot,tmp_path):
    from latex_question_studio.preview.compiler import CompileResult
    from PySide6.QtGui import QImage,QColor
    from PySide6.QtCore import QBuffer,QIODevice
    rows=[{'id':str(i),'path':'synthetic.tex','source':r"\begin{ex}Q"+str(i)+r"\end{ex}",'errors':[],'parsed':{'type':'essay','assets':[]}} for i in range(2)]
    review=ImportReview(rows,services=create_services(AppConfig.load(tmp_path)));qtbot.addWidget(review);review.cancel_preview()
    old=review.preview_generation;review.table.setCurrentCell(1,0);review.cancel_preview();current=review.preview_generation
    image=QImage(20,20,QImage.Format.Format_RGB32);image.fill(QColor('blue'));buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly);image.save(buffer,'PNG');png=bytes(buffer.data())
    result=CompileResult(True,tmp_path/'synthetic.pdf','')
    review.preview_ready((old,result,[png]));assert review.preview_pages==[]
    review.preview_ready((current,result,[png]));assert len(review.preview_pages)==1
    review.cancel_preview();review.preview_ready((current,result,[png]));assert review.preview_generation!=current
    review.close()


def test_library_pagination_does_not_rebuild_tree(qtbot,tmp_path,monkeypatch):
    s=create_services(AppConfig.load(tmp_path));w=MainWindow(s);qtbot.addWidget(w)
    monkeypatch.setattr(w,'filtered_count',lambda:250);calls=[]
    monkeypatch.setattr(w,'refresh_taxonomy',lambda:calls.append(1))
    w.next_page();assert w.offset==100 and not calls
    w.previous_page();assert w.offset==0 and not calls
    w.close()
