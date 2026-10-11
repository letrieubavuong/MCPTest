from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.tex_exams import TexExamService
from latex_question_studio.ui.main_window import MainWindow


def test_two_exam_modes_generate_without_import_and_preserve_bank_state(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(2)
    window.exam_page.title.setText('Bank draft retained')
    assert window.pages.currentWidget() is window.exam_page
    assert window.exam_page.modes.count() == 2
    window.exam_page.modes.setCurrentIndex(1)
    page = window.exam_page.tex_page
    assert window.exam_page.mode_stack.currentWidget() is page and page.isVisible()
    path = tmp_path / 'exam.tex'
    path.write_text(r'\begin{ex}Question\choice{a}{\True b}{c}{d}\end{ex}', encoding='utf-8')
    page.load_path(path)
    qtbot.waitUntil(lambda: page.document is not None, timeout=5000)
    page.codes.setText('101, 102')
    page.generate_action.trigger()
    qtbot.waitUntil(lambda: page.batch is not None, timeout=5000)
    page.preview.cancel()
    assert page.variants.count() == 2 and page.mapping.rowCount() == 1
    assert page.export_action.isEnabled()
    page.variants.setCurrentRow(1)
    page.preview.cancel()
    assert '102' in page.preview.code.toPlainText()
    assert page.preview.preamble_override is not None
    with services.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM questions').fetchone()[0] == 0
    window.exam_page.modes.setCurrentIndex(0)
    assert window.exam_page.title.text() == 'Bank draft retained'
    window.use_exam_selection()
    assert window.exam_page.modes.currentIndex() == 0
    window.close()


def test_file_mode_handles_invalid_code_and_restores_selected_mode(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    path = tmp_path / 'exam.tex'
    path.write_text(r'\begin{ex}Question\end{ex}', encoding='utf-8')
    page = window.exam_page.tex_page
    page.set_document(TexExamService(services).load(path))
    page.codes.setText('101, 101')
    page.generate_variants()
    qtbot.waitUntil(lambda: page.job is None, timeout=5000)
    assert 'không trùng' in page.status.text() and page.batch is None
    window.exam_page.modes.setCurrentIndex(1)
    window.close()
    restored = MainWindow(services)
    qtbot.addWidget(restored)
    assert restored.exam_page.modes.currentIndex() == 1
    restored.close()
