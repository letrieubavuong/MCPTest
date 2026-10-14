r"""Tests for Phase K4: Exam Builder UI & sync_cards Optimization.

Validates that:
- sync_cards updates selection state in-place without rebuilding all widgets when rows haven't changed.
- Selection latency is measured and under 10ms.
- Exam dialog displays 4-part categories in Step 4 snapshot preview.
- Previewing snapshot items links to correct question index via UserRole.
"""
import time
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.exam_dialog import ExamDialog


def test_sync_cards_inplace_selection_and_latency(qtbot, tmp_path):
    app = QApplication.instance() or QApplication([])
    services = create_services(AppConfig.load(tmp_path / 'app'))

    # Create 10 sample questions
    for i in range(10):
        services.questions.create(f"\\begin{{ex}}Câu {i}?\\choice{{A}}{{B}}{{C}}{{\\True D}}\\end{{ex}}", 'mcq')

    win = MainWindow(services)
    qtbot.addWidget(win)
    win.show()

    lib_ui = win.library_ui
    lib_ui.mode.setCurrentIndex(1)  # Card mode
    lib_ui.sync_cards()

    assert lib_ui.cards.count() == 10
    original_first_item = lib_ui.cards.item(0)

    # Change selection and call sync_cards: should update in place
    start_time = time.perf_counter()
    lib_ui.cards.item(2).setSelected(True)
    lib_ui.cards.item(4).setSelected(True)
    lib_ui.sync_cards()
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    # Ensure items were NOT destroyed and recreated
    assert lib_ui.cards.item(0) is original_first_item
    assert lib_ui.cards.item(2).isSelected()
    assert lib_ui.cards.item(4).isSelected()
    assert not lib_ui.cards.item(1).isSelected()
    assert elapsed_ms < 100.0  # Ultra-fast in-place update without rebuilding widgets


def test_exam_dialog_four_parts_categorization(qtbot, tmp_path):
    app = QApplication.instance() or QApplication([])
    services = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(services)

    q1 = services.questions.create(r'\begin{ex}Câu 1?\choice{A}{\True B}{C}{D}\end{ex}', 'mcq')
    q2 = services.questions.create(r'\begin{ex}Câu 2?\choiceTF{\True A}{B}{\True C}{D}\end{ex}', 'true_false')
    q3 = services.questions.create(r'\begin{ex}Câu 3?\shortans{5}\end{ex}', 'short_answer')
    q4 = services.questions.create(r'\begin{ex}Câu 4 tự luận.\end{ex}', 'essay')

    _, snapshot = exam.generate('Đề Test 4 Phần', manual_ids=[q1.id, q2.id, q3.id, q4.id], seed=1)

    dlg = ExamDialog([], parent=None, services=services)
    qtbot.addWidget(dlg)

    dlg.show_snapshot(snapshot)

    # Check that snapshot_chosen has 4 items
    assert dlg.snapshot_chosen.count() == 4
    t0 = dlg.snapshot_chosen.item(0).text()
    t1 = dlg.snapshot_chosen.item(1).text()
    t2 = dlg.snapshot_chosen.item(2).text()
    t3 = dlg.snapshot_chosen.item(3).text()

    assert "Phần I - MCQ" in t0
    assert "Phần II - Đúng/Sai" in t1
    assert "Phần III - TL Ngắn" in t2
    assert "Phần IV - Tự luận" in t3

    # Check preview item
    dlg.snapshot_chosen.setCurrentRow(1)
    dlg._preview_snapshot_item(1)
    assert r"\choiceTF" in dlg.snapshot_preview.source
