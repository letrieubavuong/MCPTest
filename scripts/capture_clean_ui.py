import os
from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow

def capture_ui():
    app = QApplication.instance() or QApplication([])
    config = AppConfig.load()
    services = create_services(config)
    
    w = MainWindow(services)
    w.resize(1366, 768)
    w.show()
    
    def pump(duration=0.5):
        end = time.time() + duration
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    pump(1.0)
    
    out_dir = Path(r"C:\Users\Admin\.gemini\antigravity-ide\brain\52e7ae05-be69-446a-b16d-863b72d92fe5")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Go to Exam Page Step 2
    w.show_page(2)
    w.exam_page.set_exam_step(1)
    
    # Select root item on tree
    if hasattr(w.exam_page, 'tree') and w.exam_page.tree.topLevelItemCount() > 0:
        item = w.exam_page.tree.topLevelItem(0)
        w.exam_page.tree.setCurrentItem(item)
        w.exam_page.select_scope(item)
    
    pump(2.0)
    
    # Full exam page
    w.grab().save(str(out_dir / "clean_ui_exam_step2.png"))
    
    # Also grab close-up of matrix_grid
    if hasattr(w.exam_page, 'matrix_grid'):
        w.exam_page.matrix_grid.grab().save(str(out_dir / "matrix_grid_closeup.png"))
        
    w.close()
    print("Captures completed successfully!")

if __name__ == "__main__":
    capture_ui()
