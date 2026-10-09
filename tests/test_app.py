import json
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.app.logging_config import configure_logging
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


def test_settings_round_trip_and_reject_invalid(tmp_path):
    config = AppConfig.load(tmp_path / "data dir")
    config.save()
    assert AppConfig.load(config.data_dir) == config
    (config.data_dir / "settings.json").write_text('{"version":99}', encoding="utf-8")
    with pytest.raises(ValueError):
        AppConfig.load(config.data_dir)


def test_logging_does_not_duplicate_handlers(tmp_path):
    logger = configure_logging(tmp_path)
    logger = configure_logging(tmp_path)
    logger.info("Application ready")
    assert len(logger.handlers) == 1
    assert (tmp_path / "studio.log").read_text(encoding="utf-8").count("Application ready") == 1
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def test_window_smoke_and_database_refresh(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path))
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(window.isVisible)
    assert "0 câu hỏi" in window.database_status.text()
    services.questions.create("sample")
    window.refresh_button.click()
    assert "1 câu hỏi" in window.database_status.text()
    window.close()
