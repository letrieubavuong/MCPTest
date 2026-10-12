from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


def test_library_asset_filters_and_inspector_report(qtbot, tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'))
    image=tmp_path/'image.png';image.write_bytes(b'asset')
    source=tmp_path/'q.tex';source.write_text(r'\begin{ex}A\includegraphics{image.png}\end{ex}',encoding='utf-8')
    batch,_=ImportService(services).stage([source]);assert ImportService(services).commit(batch)==1
    q=services.questions.list_page()[0]
    window=MainWindow(services);qtbot.addWidget(window);window.show()
    page=window.library_ui
    assert page.asset_summary(q.id).startswith('1 file')
    page.state.setCurrentIndex(page.state.findData('has_asset'));assert page.search(count_only=True)==1
    page.state.setCurrentIndex(page.state.findData('asset_problem'));assert page.search(count_only=True)==0
    with services.database.transaction() as connection:
        connection.execute("UPDATE question_assets SET resolution_status='MISSING_ASSET' WHERE question_id=?",(q.id,))
    page.state.setCurrentIndex(page.state.findData('asset_problem'));assert page.search(count_only=True)==1
    page.load_metadata(q);assert 'MISSING_ASSET' in page.asset_status.text();window.close()
