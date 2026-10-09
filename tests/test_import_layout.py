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
