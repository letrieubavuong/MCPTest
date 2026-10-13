import pytest
from PySide6.QtCore import Qt
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


def test_default_light_theme(tmp_path):
    config = AppConfig.load(tmp_path / 'new_dir')
    assert config.theme == 'light'


def test_library_modes_and_batch_bar(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    # Tạo 3 câu hỏi mẫu
    q1 = services.questions.create(r'\begin{ex}Câu 1\choice{A}{\True B}{C}{D}\end{ex}', 'mcq', cognitive_level='NB')
    q2 = services.questions.create(r'\begin{ex}Câu 2\shortans{5}\end{ex}', 'short_answer', cognitive_level='TH')
    q3 = services.questions.create(r'\begin{ex}Câu 3 tự luận\end{ex}', 'essay', cognitive_level='VD')

    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(0)

    lib = window.library_ui
    assert lib.mode.count() == 2

    # Chế độ thẻ preview (index 1)
    lib.mode.setCurrentIndex(1)
    assert lib.stack.currentIndex() == 1
    assert lib.cards.count() == 3

    # Chuyển sang chế độ danh sách gọn (index 0)
    lib.mode.setCurrentIndex(0)
    assert lib.stack.currentIndex() == 0
    assert window.table_model.rowCount() == 3

    # Kiểm tra Batch Action Bar khi chọn nhiều câu
    lib.mode.setCurrentIndex(1)
    lib.cards.clearSelection()
    assert not lib.batch_bar.isVisible()

    # Chọn câu 1 và câu 2
    lib.cards.item(0).setSelected(True)
    lib.cards.item(1).setSelected(True)
    assert lib.batch_bar.isVisible()
    assert "2" in lib.batch_count_lbl.text() and "câu" in lib.batch_count_lbl.text()

    # Bỏ chọn -> ẩn bar
    lib.cards.clearSelection()
    assert not lib.batch_bar.isVisible()

    window.close()


def test_filter_combinations(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    services.questions.create(r'\begin{ex}Hàm số lượng giác\choice{a}{\True b}{c}{d}\end{ex}', 'mcq', cognitive_level='NB')
    services.questions.create(r'\begin{ex}Hình học không gian\choice{a}{\True b}{c}{d}\end{ex}', 'mcq', cognitive_level='VD')
    services.questions.create(r'\begin{ex}Số phức nâng cao\shortans{2}\end{ex}', 'short_answer', cognitive_level='VDC')

    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(0)
    lib = window.library_ui

    # 1. Lọc theo dạng thức MCQ
    lib.kind.setCurrentIndex(lib.kind.findData('mcq'))
    qtbot.waitUntil(lambda: window.table_model.rowCount() == 2)

    # 2. Lọc tiếp theo mức độ VD
    lib.level.setCurrentIndex(lib.level.findData('VD'))
    qtbot.waitUntil(lambda: window.table_model.rowCount() == 1)
    assert 'Hình học không gian' in window.table_model.rows[0].latex_source

    # 3. Reset filters
    lib.reset_filters()
    qtbot.waitUntil(lambda: window.table_model.rowCount() == 3)

    window.close()
