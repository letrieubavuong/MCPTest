from PySide6.QtCore import Qt

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.import_dialog import ImportReview


def test_review_shows_resource_status_and_keeps_selection(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    path = tmp_path / 'question.tex'
    path.write_text(r'\begin{ex}A\includegraphics{missing.png}\end{ex}', encoding='utf-8')
    _, rows = ImportService(services).stage([path])
    review = ImportReview(rows, services=services)
    qtbot.addWidget(review)
    review.show()
    assert review.table.columnCount() == 6
    assert review.table.item(0, 4).text() == 'MISSING_ASSET'
    assert review.resource_list.count() >= 2
    assert review.selected_ids() == [rows[0]['id']]
    review.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    assert review.selected_ids() == []
    review.close()
