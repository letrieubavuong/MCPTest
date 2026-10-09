from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


def test_drawer_routes_embedded_controls_and_preserves_edits(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path))
    question = services.questions.create(r'\begin{ex}A\end{ex}')
    window = MainWindow(services); qtbot.addWidget(window); window.show()
    editor = window.open_question(question.id)
    editor.insertPlainText('unsaved ')
    window.exam_page.title.setText('Đề giữ trạng thái')
    for index in (1, 2, 3, 0, 2):
        item = window.navigation.item(index)
        qtbot.mouseClick(window.navigation.viewport(), Qt.MouseButton.LeftButton,
                         pos=window.navigation.visualItemRect(item).center())
        assert window.pages.currentIndex() == index
        assert window.pages.currentWidget().window() is window
    assert editor.toPlainText().startswith('unsaved ')
    assert editor.document().isModified()
    assert window.exam_page.title.text() == 'Đề giữ trạng thái'
    assert not any(isinstance(w, QDialog) and w.isVisible() for w in QApplication.topLevelWidgets())
    assert not window.findChildren(type(window.explorer_dock))[0].isFloating()
    window.toggle_drawer(); assert window.drawer.width() == 64
    editor.document().setModified(False)
    window.save_workspace()
    restored = MainWindow(services); qtbot.addWidget(restored)
    assert restored.pages.currentIndex() == 2
    assert restored.drawer.width() == 64
    window.close(); restored.close()


def test_import_review_commit_and_exam_stay_in_main_window(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path/'data'))
    source = tmp_path/'Câu hỏi mẫu.tex'
    source.write_text(r'\begin{ex}Tính $1+1$.\choice{1}{\True 2}{3}{4}\loigiai{2}\end{ex}', encoding='utf-8')
    window = MainWindow(services); qtbot.addWidget(window); window.show()
    window.start_import([source])
    # A background result must not pull the user away from the current page.
    window.show_page(2)
    qtbot.waitUntil(lambda: hasattr(window, 'import_review'), timeout=15000)
    assert window.pages.currentIndex() == 2
    review = window.import_review
    assert review.window() is window and not isinstance(review, QDialog)
    window.show_page(1)
    review.accepted.emit()
    qtbot.waitUntil(lambda: getattr(window, 'commit_job', None) is None, timeout=15000)
    assert len(services.questions.list_page()) == 1
    window.show_page(0); window.tabs.setCurrentIndex(0); window.table.selectRow(0)
    window.create_exam(); window.use_exam_selection()
    window.generate_exam()
    assert window.pages.currentWidget() is window.exam_page
    qtbot.waitUntil(lambda: getattr(window,'exam_job',None) is None,timeout=15000)
    assert len(window.exam_snapshot['questions']) == 1
    assert window.exam_export.isEnabled()
    assert not any(isinstance(w, QDialog) and w.isVisible() for w in QApplication.topLevelWidgets())
    window.show_pending(); assert window.import_review.window() is window
    assert window.pages.currentIndex() == 1
    window.close()
