import os
from pathlib import Path
import sys
import time

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow

def capture_phase_i5():
    app = QApplication.instance() or QApplication([])
    config = AppConfig.load()
    services = create_services(config)

    out_dir = Path(r"C:\Users\Admin\.gemini\antigravity-ide\brain\52e7ae05-be69-446a-b16d-863b72d92fe5")
    out_dir.mkdir(parents=True, exist_ok=True)

    def pump(duration=0.5):
        end = time.time() + duration
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    w = MainWindow(services)

    # 1. Capture at 1366 x 768 - Chế độ Thẻ Preview
    w.resize(1366, 768)
    w.show()
    w.show_page(1) # Library Page
    w.library_ui.mode.setCurrentIndex(1) # Thẻ preview
    w.library_ui.switch_mode(1)
    pump(0.8)
    w.grab().save(str(out_dir / "phase_i5_library_1366x768_cards.png"))
    print("Saved phase_i5_library_1366x768_cards.png")

    # 2. Capture at 1366 x 768 - Chế độ Danh sách gọn
    w.library_ui.mode.setCurrentIndex(0) # Danh sách gọn
    w.library_ui.switch_mode(0)
    pump(0.5)
    w.grab().save(str(out_dir / "phase_i5_library_1366x768_list.png"))
    print("Saved phase_i5_library_1366x768_list.png")

    # 3. Capture at 1600 x 900 - Tìm kiếm và Bộ lọc
    w.resize(1600, 900)
    w.library_ui.mode.setCurrentIndex(1)
    w.library_ui.switch_mode(1)
    w.library_ui.query.setText("Toán")
    pump(0.8)
    w.grab().save(str(out_dir / "phase_i5_library_1600x900_search_filter.png"))
    print("Saved phase_i5_library_1600x900_search_filter.png")

    # 4. Capture at 1920 x 1080 - Toàn cảnh ngân hàng 1080p
    w.library_ui.query.clear()
    w.resize(1920, 1080)
    pump(0.8)
    w.grab().save(str(out_dir / "phase_i5_library_1920x1080_full_overview.png"))
    print("Saved phase_i5_library_1920x1080_full_overview.png")

    w.close()
    print("All Phase I.5 UI screenshots captured successfully!")

if __name__ == "__main__":
    capture_phase_i5()
