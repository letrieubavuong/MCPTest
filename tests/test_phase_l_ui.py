"""UI tests for Phase L: DedupPage, WebScraperPage, and MainWindow integration."""
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.web_import import QuestionDraft
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.pages.dedup_page import DedupPage
from latex_question_studio.ui.pages.web_scraper_page import WebScraperPage


@pytest.fixture
def test_services(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    return create_services(config)


def test_dedup_page_initialization_and_scope(qtbot, test_services):
    page = DedupPage(test_services)
    qtbot.addWidget(page)
    page.show()

    assert page.scope_combo.currentText() == "Trong Cơ sở dữ liệu hiện hành"
    assert page.scope_combo.currentData() == "database"
    assert page.scan_btn.isEnabled()
    assert not page.cancel_btn.isEnabled()

    # Switch scope to files
    page.scope_combo.setCurrentIndex(1)
    assert page.scope_combo.currentData() == "files"
    assert page.db_filter_widget.isHidden()
    assert not page.file_control_widget.isHidden()

    # Switch back to database
    page.scope_combo.setCurrentIndex(0)
    assert page.scope_combo.currentData() == "database"
    assert not page.db_filter_widget.isHidden()
    assert page.file_control_widget.isHidden()


def test_web_scraper_page_staging_and_moderation(qtbot, test_services):
    page = WebScraperPage(test_services)
    qtbot.addWidget(page)
    page.show()

    # Initial state
    assert page.combo_mode.currentIndex() == 0  # URL mode
    assert not page.url_input.isHidden()
    assert page.html_paste_edit.isHidden()

    # Switch to Paste HTML mode
    page.combo_mode.setCurrentIndex(1)
    assert page.url_input.isHidden()
    assert not page.html_paste_edit.isHidden()

    # Simulate extracted drafts loaded into page
    draft1 = QuestionDraft(
        id="d1", source_url="http://test/1", title="Câu 1", question_type="mcq",
        prompt_latex="Cho $x > 0$.", options_latex=["A", "B", "C", "D"],
        correct_choice=0, status="needs_review"
    )
    draft2 = QuestionDraft(
        id="d2", source_url="http://test/2", title="Câu 2", question_type="essay",
        prompt_latex="Giải phương trình $x^2 = 4$.", solution_latex="$x = \\pm 2$.",
        status="needs_review"
    )

    page.drafts = [draft1, draft2]
    page._refresh_question_list()

    assert page.list_questions.count() == 2
    assert "[?]" in page.list_questions.item(0).text()

    # Select first question
    page.list_questions.setCurrentRow(0)
    assert page.draft_title_edit.text() == "Câu 1"
    assert page.edit_prompt.toPlainText() == "Cho $x > 0$."
    assert page.mcq_radios[0].isChecked()

    # Verify first question
    page._set_current_status("verified")
    assert page.drafts[0].status == "verified"
    assert "[✓]" in page.list_questions.item(0).text()

    # Reject second question
    page.list_questions.setCurrentRow(1)
    page._set_current_status("rejected")
    assert page.drafts[1].status == "rejected"
    assert "[✕]" in page.list_questions.item(1).text()


def test_main_window_has_both_phase_l_tabs(qtbot, test_services):
    window = MainWindow(test_services)
    qtbot.addWidget(window)

    # Check total navigation items
    # 0: CSDL, 1: Nhập, 2: Ra đề, 3: Cài đặt, 4: Bài giảng, 5: Câu hỏi trùng, 6: Thu thập từ Web
    assert window.navigation.count() >= 7

    # Verify tab titles in accessibility / tooltips
    dedup_item = window.navigation.item(5)
    assert "Câu hỏi trùng" in dedup_item.toolTip()

    web_item = window.navigation.item(6)
    assert "Thu thập từ Web" in web_item.toolTip()

    # Test navigating to Dedup Page (index 5)
    window.show_page(5)
    assert window.pages.currentIndex() == 5
    assert isinstance(window.pages.currentWidget(), DedupPage)
    assert "Câu hỏi trùng" in window.statusBar().currentMessage()

    # Test navigating to Web Scraper Page (index 6)
    window.show_page(6)
    assert window.pages.currentIndex() == 6
    assert isinstance(window.pages.currentWidget(), WebScraperPage)
    assert "Thu thập từ Web" in window.statusBar().currentMessage()

    # Test backward compatibility: index 0 is CSDL, index 4 is Lesson
    window.show_page(0)
    assert window.pages.currentIndex() == 0

    window.show_page(4)
    assert window.pages.currentIndex() == 4
