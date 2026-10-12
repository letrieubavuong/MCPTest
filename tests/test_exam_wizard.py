import pytest
from PySide6.QtCore import Qt
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


def test_exam_wizard_five_steps_navigation_and_flow(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    # Tạo vài câu mẫu
    for i, level in enumerate(('NB', 'TH', 'VD', 'VDC'), 1):
        services.questions.create(r'\begin{ex}Câu ' + str(i) + r'\choice{\True A}{B}{C}{D}\end{ex}', 'mcq', cognitive_level=level)

    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(2)  # Màn hình Ra đề thi

    exam = window.exam_page
    assert exam.bank_step_stack.count() == 5
    assert exam.exam_steps.count() == 5

    # 1. Ban đầu ở Bước 1: Thông tin đề
    assert exam.bank_step_stack.currentIndex() == 0
    assert exam.exam_steps.currentRow() == 0

    # Đặt tên và seed
    exam.title.setText('Đề thi thử Toán 10')
    exam.seed.setValue(123456)

    # 2. Click chuyển sang Bước 2: Chọn câu hỏi
    exam.exam_steps.setCurrentRow(1)
    assert exam.bank_step_stack.currentIndex() == 1

    # Thêm câu thủ công
    qids = [q.id for q in services.questions.list_page()]
    exam.set_manual_ids(qids[:2])
    assert len(exam.manual_ids) == 2

    # 3. Chuyển sang Bước 3: Cấu hình & Tạo đề
    exam.exam_steps.setCurrentRow(2)
    assert exam.bank_step_stack.currentIndex() == 2
    assert exam.sum_title_lbl.text() == 'Đề thi thử Toán 10'
    assert '2' in exam.sum_count_lbl.text()

    # Bấm nút tạo đề lớn
    qtbot.mouseClick(exam.big_generate_btn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: getattr(window, 'exam_job', None) is None, timeout=5000)

    # Sau khi tạo đề xong, hệ thống tự động đưa vào Bước 4: Xem trước đề thi
    assert exam.bank_step_stack.currentIndex() == 3
    assert exam.exam_steps.currentRow() == 3
    assert exam.snapshot is not None
    assert len(exam.snapshot['questions']) >= 2
    assert exam.snapshot_chosen.count() >= 2

    # 4. Chuyển sang Bước 5: Xuất đề
    exam.exam_steps.setCurrentRow(4)
    assert exam.bank_step_stack.currentIndex() == 4
    assert exam.export_info_title.text() == 'Đề thi thử Toán 10'
    assert 'câu hỏi' in exam.export_info_count.text()

    window.close()
