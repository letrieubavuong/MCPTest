import argparse
from pathlib import Path
import sys
from latex_question_studio.app.config import AppConfig
from latex_question_studio.app.logging_config import configure_logging
from latex_question_studio.application.services import create_services


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="LaTeX Question Studio")
    parser.add_argument("--data-dir", type=Path, help="Use a separate application data directory")
    parser.add_argument("--smoke-test", action="store_true", help="Show the window, then close automatically")
    parser.add_argument("--screenshot", type=Path, help="Save the application window during smoke test")
    parser.add_argument("--smoke-delay-ms", type=int, default=600)
    args = parser.parse_args(argv)
    if args.screenshot and not args.smoke_test:
        parser.error("--screenshot requires --smoke-test")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    from latex_question_studio.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName("LaTeX Question Studio")
    app.setOrganizationName("LaTeXQuestionStudio")
    try:
        config = AppConfig.load(args.data_dir)
        logger = configure_logging(config.log_dir)
        services = create_services(config)
        config.save()
        window = MainWindow(services)
    except Exception:
        if args.smoke_test:
            print("Application initialization failed; check configuration and database.", file=sys.stderr)
            return 1
        QMessageBox.critical(None, "Không thể khởi động", "Kiểm tra cấu hình và cơ sở dữ liệu. Dữ liệu chưa bị xóa.")
        return 1
    logger.info("Application started; schema initialized")
    window.show()
    if args.smoke_test:
        def finish():
            result = 0
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                if not window.screen().grabWindow(window.winId()).save(str(args.screenshot)):
                    result = 1
            window.close()
            app.exit(result)
        QTimer.singleShot(max(100,min(args.smoke_delay_ms,30000)), finish)
    return app.exec()
