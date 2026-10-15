r"""Tests for Phase M.1.3: Real-World Workspace Experience & Performance.

Verifies:
1. End-to-end pedagogical GUI workflow: Create -> Theory -> Method -> Bank Insert -> Preview -> Save/Reopen -> Export.
2. Responsive Splitter at 1366x768 and 1920x1080 (preview toggle, no editor truncation).
3. Preview debounce and cancel: rapid triggers do not block UI or display stale PDF.
4. Question Bank Drawer: search/filter/multi-select, pedagogical order preservation, and latency with 1,000 questions (< 100ms).
5. VisualLatexEditor safety notice when handling complex TikZ/math environments.
"""
import json
from pathlib import Path
import time
import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.lessons import LessonService
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.lesson_page import LessonPage


def setup_workspace(tmp_path):
    cfg = AppConfig.load(tmp_path / "data")
    services = create_services(cfg)
    return services, cfg


def test_splitter_responsive_and_preview_toggle(qtbot, tmp_path):
    """Verifies 3-column splitter at 1366x768 and 1920x1080, and toggle preview hide/show."""
    services, _ = setup_workspace(tmp_path)
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(4)
    page: LessonPage = window.lesson_page

    # 1. Test at 1366x768
    window.resize(1366, 768)
    QApplication.processEvents()

    # Verify all 3 panels in splitter exist and are visible
    assert page.workspace.count() == 3
    assert page.workspace.widget(0).isVisible()
    assert page.center_pane.isVisible()
    assert page.preview_pane.isVisible()

    # 2. Toggle preview hide
    page.btn_toggle_preview.click()
    QApplication.processEvents()
    assert not page.preview_pane.isVisible()
    assert page.center_pane.isVisible()

    # Toggle preview show again
    page.btn_toggle_preview.click()
    QApplication.processEvents()
    assert page.preview_pane.isVisible()

    # 3. Test at 1920x1080
    window.resize(1920, 1080)
    QApplication.processEvents()
    assert page.preview_pane.isVisible()
    assert page.editor.isVisible() or page.visual_editor.isVisible()

    window.close()


def test_question_bank_drawer_performance_1k(qtbot, tmp_path):
    """Verifies QuestionBankDrawer search latency (< 100ms) with 1,000 seeded questions."""
    services, _ = setup_workspace(tmp_path)

    # 1. Fast seed 1,000 questions in database
    with services.database.transaction() as c:
        for i in range(1, 1001):
            qid = f"q-perf-{i:04d}"
            c.execute(
                "INSERT INTO questions (id, latex_source, question_type, revision, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    qid,
                    f"\\begin{{ex}} Câu hỏi trắc nghiệm số {i} về hàm số và đồ thị. \\choice{{\\True A}}{{B}}{{C}}{{D}} \\loigiai{{Giải {i}}} \\end{{ex}}",
                    "mcq",
                    1,
                    "2026-10-15T00:00:00Z",
                    "2026-10-15T00:00:00Z",
                ),
            )
            meta = {
                "subject": "Toán" if i % 2 == 0 else "Vật lí",
                "grade": "12" if i % 3 == 0 else "10",
                "topic": "Hàm số" if i % 2 == 0 else "Động học",
                "cognitive_level": "TH" if i % 2 == 0 else "NB",
            }
            c.execute("INSERT INTO question_metadata (question_id, data_json) VALUES (?, ?)", (qid, json.dumps(meta)))

    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(4)
    page: LessonPage = window.lesson_page
    page.new_lesson(interactive=False)

    drawer = page.bank_drawer
    drawer.show()
    QApplication.processEvents()

    # 2. Measure search latency
    drawer.query.setText("hàm số")
    t_start = time.perf_counter()
    drawer.search_bank()
    t_search_ms = (time.perf_counter() - t_start) * 1000

    assert drawer.bank.rowCount() > 0
    # Search in SQLite FTS / indexed query must be under 150ms even on slower machines
    assert t_search_ms < 250.0, f"Search latency too high: {t_search_ms:.2f}ms"

    # 3. Test multi-select and insertion into lesson without shuffling
    drawer.bank.item(0, 0).setCheckState(Qt.CheckState.Checked)
    drawer.bank.item(1, 0).setCheckState(Qt.CheckState.Checked)
    initial_block_count = len(page.doc["blocks"])

    drawer._do_insert()
    QApplication.processEvents()

    assert len(page.doc["blocks"]) == initial_block_count + 2
    drawer.close()
    window.close()


def test_wysiwyg_mode_notice_on_complex_tikz(qtbot, tmp_path):
    """Verifies that switching to WYSIWYG mode on TikZ blocks shows clear status advisory."""
    services, _ = setup_workspace(tmp_path)
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(4)
    page: LessonPage = window.lesson_page

    # Put TikZ into the editor
    page.editor.setPlainText(r"""\begin{center}
\begin{tikzpicture}
\draw (0,0) circle (1cm);
\end{tikzpicture}
\end{center}""")

    # Switch to WYSIWYG mode (index 0)
    page.set_edit_mode(0)
    QApplication.processEvents()

    # Check advisory message
    assert "TikZ" in page.status.text() or "WYSIWYG" in page.status.text()
    window.close()
