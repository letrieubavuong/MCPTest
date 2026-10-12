from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.lesson_dialog import NewLessonDialog
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.themes.design import apply

root = Path(__file__).resolve().parents[1]
data = root / '.runtime/lesson-creation-data'
data.mkdir(parents=True, exist_ok=True)
out = root / 'artifacts/lesson-creation'
out.mkdir(parents=True, exist_ok=True)

app = QApplication([])
apply('dark')
services = create_services(AppConfig.load(data))

# 1. State 1: Default standard template
dlg1 = NewLessonDialog(services)
dlg1.resize(880, 640)
dlg1.show()
app.processEvents()
time.sleep(0.2)
dlg1.grab().save(str(out / '1-standard-template.png'))
dlg1.close()
app.processEvents()

# 2. State 2: Curriculum selection
dlg2 = NewLessonDialog(services)
dlg2.resize(880, 640)
dlg2.curriculum_check.setChecked(True)
if dlg2.curriculum_combo.count() > 1:
    dlg2.curriculum_combo.setCurrentIndex(1)
dlg2.show()
app.processEvents()
time.sleep(0.2)
dlg2.grab().save(str(out / '2-curriculum-linked.png'))
dlg2.close()
app.processEvents()

# 3. State 3: Methods template
dlg3 = NewLessonDialog(services)
dlg3.resize(880, 640)
dlg3.template_combo.setCurrentIndex(dlg3.template_combo.findData('methods'))
dlg3.num_methods_spin.setValue(3)
dlg3.show()
app.processEvents()
time.sleep(0.2)
dlg3.grab().save(str(out / '3-methods-template.png'))
dlg3.close()
app.processEvents()

# 4. State 4: Lesson page workspace
window = MainWindow(services)
window.resize(1366, 768)
window.show()
window.show_page(4)
page = window.lesson_page
doc = page.service.create(
    title='Bài 1: Sự đồng biến và nghịch biến của hàm số',
    subject='Toán',
    grade='12',
    template_key='standard',
    num_methods=2,
    include_warmup=True,
    include_homework=True
)
page.reload_list(doc['id'])
page.load(doc)
app.processEvents()
time.sleep(0.2)
window.grab().save(str(out / '4-lesson-workspace.png'))
window.close()
app.processEvents()

print("All screenshots generated successfully!")
