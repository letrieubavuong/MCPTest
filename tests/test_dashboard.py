from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


def test_dashboard_is_data_backed_home_and_routes_actions(qtbot, tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'))
    window=MainWindow(services);qtbot.addWidget(window);window.show()
    assert window.dashboard_index == window.pages.indexOf(window.dashboard_page) and window.pages.currentWidget() is window.dashboard_page
    assert window.dashboard_page.cards[0].value.text()=='0'
    services.questions.create(r'\begin{ex}Dashboard question\end{ex}')
    window.refresh_status();assert window.dashboard_page.cards[0].value.text()=='1'
    window.dashboard_page.callbacks['library']();assert window.pages.currentIndex()==0
    window.open_dashboard();assert window.shell.home.isChecked()
    assert window.dashboard_page.chart.width()>0 and window.dashboard_page.donut.width()>0
    assert window.dashboard_page.chart.data == []
    window.close()


def test_dashboard_groups_levels_by_subject_and_refreshes_activity(qtbot, tmp_path):
    from latex_question_studio.application.library import LibraryService
    services=create_services(AppConfig.load(tmp_path/'data'))
    question=services.questions.create(r'\begin{ex}A\end{ex}', cognitive_level='VD')
    LibraryService(services).save_metadata(question.id, {'subject':'Toán'})
    window=MainWindow(services);qtbot.addWidget(window);window.open_dashboard()
    assert window.dashboard_page.chart.data == [('Toán', [0, 0, 1, 0])]
    assert window.dashboard_page.activity_body.count() >= 1
    window.close()
