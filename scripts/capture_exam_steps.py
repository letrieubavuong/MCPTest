from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow

root = Path(__file__).resolve().parents[1]
data = root / '.runtime/exam-steps-data'
data.mkdir(parents=True, exist_ok=True)
out = root / 'artifacts/exam-steps'
out.mkdir(parents=True, exist_ok=True)

app = QApplication([])
services = create_services(AppConfig.load(data))
library = LibraryService(services)

for index, level in enumerate(('NB', 'TH', 'VD', 'VDC', 'NB', 'TH'), 1):
    q = services.questions.create(r'\begin{ex}Câu ' + str(index) + r' tính $x^2+1$.\end{ex}', 'essay', cognitive_level=level)
    library.save_metadata(q.id, {'taxonomy_id': 'curriculum:math6:lesson:01'})

window = MainWindow(services)
window.resize(1366, 768)
window.show()
window.show_page(2)
exam = window.exam_page

# Bước 0: Thông tin đề
exam.set_exam_step(0)
app.processEvents(); time.sleep(0.1)
window.grab().save(str(out / 'step-1-info.png'))

# Bước 1: Chọn câu hỏi & ma trận
exam.set_exam_step(1)
exam.set_manual_ids([q.id for q in services.questions.list_page()[:3]])
exam.add_row()
row = exam.matrix.rowCount() - 1
exam.matrix.item(row, 3).setText('NB')
exam.matrix.item(row, 4).setText('1')
exam.update_matrix_summary()
app.processEvents(); time.sleep(0.1)
window.grab().save(str(out / 'step-2-select.png'))

# Bước 2: Cấu hình xáo trộn
exam.set_exam_step(2)
app.processEvents(); time.sleep(0.1)
window.grab().save(str(out / 'step-3-config.png'))

# Tạo đề để chuyển sang Bước 3 (Xem trước)
window.generate_exam()
deadline = time.time() + 5
while getattr(window, 'exam_job', None) is not None and time.time() < deadline:
    app.processEvents(); time.sleep(0.05)

app.processEvents(); time.sleep(0.2)
window.grab().save(str(out / 'step-4-preview.png'))

# Bước 4: Xuất đề
exam.set_exam_step(4)
app.processEvents(); time.sleep(0.1)
window.grab().save(str(out / 'step-5-export.png'))

window.close()
app.processEvents()
print('Successfully captured all 5 steps of the exam wizard!')
