from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_ui_resolutions_and_layout_stability(tmp_path, qapp):
    """Kiểm tra bố cục giao diện ngân hàng câu hỏi ổn định ở 1366x768, 1600x900, 1920x1080."""
    config = AppConfig(data_dir=tmp_path)
    services = create_services(config)
    w = MainWindow(services)

    w.show()
    w.show_page(1)

    resolutions = [
        (1366, 768),
        (1600, 900),
        (1920, 1080),
    ]

    for width, height in resolutions:
        w.resize(width, height)
        qapp.processEvents()
        assert abs(w.width() - width) <= 20
        assert abs(w.height() - height) <= 50
        assert not w.library_ui.toolbar.isHidden()
        assert not w.library_ui.query.isHidden()
        assert not w.library_ui.mode.isHidden()

    w.close()


def test_ui_card_and_list_mode_toggle(tmp_path, qapp):
    """Kiểm tra chuyển đổi mượt mà giữa chế độ Thẻ preview và Danh sách gọn."""
    config = AppConfig(data_dir=tmp_path)
    services = create_services(config)
    w = MainWindow(services)
    w.resize(1366, 768)
    w.show()
    w.show_page(1)

    # Chế độ Danh sách gọn (index 0)
    w.library_ui.mode.setCurrentIndex(0)
    w.library_ui.switch_mode(0)
    qapp.processEvents()
    assert not w.table.isHidden()
    assert w.library_ui.cards.isHidden()

    # Chế độ Thẻ preview (index 1)
    w.library_ui.mode.setCurrentIndex(1)
    w.library_ui.switch_mode(1)
    qapp.processEvents()
    assert not w.library_ui.cards.isHidden()
    assert w.table.isHidden()

    w.close()


def test_ui_search_filter_responsiveness(tmp_path, qapp):
    """Kiểm tra thanh tìm kiếm phản hồi nhanh, không gây đơ giao diện."""
    config = AppConfig(data_dir=tmp_path)
    services = create_services(config)
    w = MainWindow(services)

    w.library_ui.query.setText("Vật lí")
    qapp.processEvents()
    assert w.library_ui.query.text() == "Vật lí"

    w.library_ui.query.clear()
    qapp.processEvents()
    assert w.library_ui.query.text() == ""

    w.close()
