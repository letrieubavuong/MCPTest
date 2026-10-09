from PySide6.QtWidgets import QMessageBox
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


def test_tabs_dirty_cancel_save_and_restore(qtbot, tmp_path, monkeypatch):
    services = create_services(AppConfig.load(tmp_path))
    q = services.questions.create("\\begin{ex}original\\end{ex}")
    window = MainWindow(services)
    qtbot.addWidget(window)
    editor = window.open_question(q.id)
    assert window.open_question(q.id) is editor
    assert window.tabs.count() == 2
    editor.insertPlainText("changed ")
    assert editor.document().isModified()
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.Cancel)
    assert not window.close_tab(1)
    assert window.tabs.count() == 2
    assert window.save_current()
    window.preview_dock.hide()
    window.save_workspace()
    restored = MainWindow(services)
    qtbot.addWidget(restored)
    assert restored.tabs.count() == 2
    assert restored.editors[next(iter(restored.editors))].latex_source == "changed \\begin{ex}original\\end{ex}"
    restored.toggle_theme()
    assert AppConfig.load(tmp_path).theme == "light"
    window.close()
    restored.close()
