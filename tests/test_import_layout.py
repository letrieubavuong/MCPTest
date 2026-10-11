from PySide6.QtWidgets import QLabel
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


def test_import_header_stays_at_top_when_content_empty_or_loaded(qtbot,tmp_path):
    window=MainWindow(create_services(AppConfig.load(tmp_path)));qtbot.addWidget(window);window.resize(1400,900);window.show();window.show_page(1);qtbot.wait(100)
    layout=window.import_page.layout();title=layout.itemAt(0).widget()
    top=title.geometry().top();assert top<30
    assert window.import_status.geometry().top()<150
    assert window.import_content_host.height()>window.import_page.height()/2
    window.replace_import_content(QLabel('Nội dung kiểm thử'));qtbot.wait(50)
    assert abs(title.geometry().top()-top)<=2
    window.close()


def test_import_review_actions_share_page_toolbar_and_are_removed(qtbot,tmp_path):
    from latex_question_studio.ui.import_dialog import ImportReview
    services=create_services(AppConfig.load(tmp_path));window=MainWindow(services);qtbot.addWidget(window);window.show();window.show_page(1)
    base=len(window.import_toolbar.actions());review=ImportReview([],services=services)
    window.replace_import_content(review);qtbot.wait(50)
    assert review.toolbar.isHidden()
    assert len(window.import_toolbar.actions())>base
    assert window.import_toolbar.widgetForAction(next(a for a in window.import_toolbar.actions() if a.toolTip()==review.level.toolTip())) is review.level
    window.replace_import_content(QLabel('Khác'));assert len(window.import_toolbar.actions())==base
    window.close()


def test_source_commands_have_one_location_and_context_toolbar_follows_step(qtbot,tmp_path,monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFileDialog, QPushButton
    services=create_services(AppConfig.load(tmp_path/'data'));window=MainWindow(services);qtbot.addWidget(window);window.show();window.show_page(1)
    flow=window.import_workflow
    assert not window.import_toolbar.isVisible() and not window.import_cancel.isVisible()
    assert [button.text() for button in flow.pages.widget(0).findChildren(QPushButton)]==['Chọn file TeX','Chọn thư mục','Hàng chờ / Sửa lỗi']
    assert not flow.pages.widget(2).findChildren(QPushButton)
    chosen=[]
    monkeypatch.setattr(window,'start_import',lambda paths:chosen.append(paths))
    monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *args:([str(tmp_path/'input.tex')],''))
    monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *args:str(tmp_path))
    (tmp_path/'input.tex').write_text(r'\begin{ex}A\end{ex}')
    qtbot.mouseClick(flow.file_button,Qt.MouseButton.LeftButton)
    qtbot.mouseClick(flow.folder_button,Qt.MouseButton.LeftButton)
    assert len(chosen)==2 and all(str(paths[0])==str(tmp_path/'input.tex') for paths in chosen)
    from latex_question_studio.ui.import_dialog import ImportReview
    review=ImportReview([],services=services);review.rejected.connect(window.leave_import_review)
    window.replace_import_content(review)
    assert flow.pages.currentIndex()==3 and window.import_toolbar.isVisible() and review.toolbar.isHidden()
    assert window.import_toolbar.actions().count(review.confirm_action)==1
    assert not any(action.text()=='Bỏ / chọn lại các câu đang chọn' for action in window.import_toolbar.actions())
    flow.set_step(0)
    assert not window.import_toolbar.isVisible()
    flow.set_step(3);review.rejected.emit()
    assert flow.pages.currentIndex()==0 and not window.import_toolbar.isVisible()
    assert services.questions.count()==0
    window.close()


def test_import_busy_cancel_and_pending_stay_available_in_their_context(qtbot,tmp_path):
    from PySide6.QtCore import Qt
    from latex_question_studio.ui.pending_dialog import PendingDialog
    from latex_question_studio.ui.jobs import Job
    services=create_services(AppConfig.load(tmp_path/'data'));window=MainWindow(services);qtbot.addWidget(window);window.show();window.show_page(1)
    flow=window.import_workflow
    window.import_job=Job(lambda cancelled,progress:None)
    window.import_cancel.setEnabled(True);flow.set_step(1)
    assert window.import_toolbar.isVisible() and window.import_cancel.isVisible()
    assert not flow.file_button.isEnabled() and not flow.folder_button.isEnabled() and not flow.pending_button.isEnabled()
    window.import_job=None;window.import_cancel.setEnabled(False);flow.set_step(0)
    assert not window.import_toolbar.isVisible() and flow.pending_button.isEnabled()
    qtbot.mouseClick(flow.pending_button,Qt.MouseButton.LeftButton)
    assert isinstance(window.import_review,PendingDialog) and flow.pages.currentIndex()==3
    assert window.import_review.isVisible() and services.questions.count()==0
    window.close()
