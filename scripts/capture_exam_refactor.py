from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.library import LibraryService
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.themes.design import apply

root = Path(__file__).resolve().parents[1]
data = root / '.runtime/exam-refactor-data'
data.mkdir(parents=True, exist_ok=True)
out = root / 'artifacts/exam-refactor'
out.mkdir(parents=True, exist_ok=True)

app = QApplication([])
apply('dark')
services = create_services(AppConfig.load(data))
library = LibraryService(services)

# Tạo một số câu hỏi mẫu với đầy đủ 4 loại và 4 mức độ
types = ('mcq', 'true_false', 'short_answer', 'essay')
levels = ('NB', 'TH', 'VD', 'VDC')

for qtype in types:
    for level in levels:
        for i in range(3):
            if qtype == 'mcq':
                src = rf'\begin{{ex}}Câu {qtype} {level} {i}\choice{{\True A}}{{B}}{{C}}{{D}}\loigiai{{Giải}}\end{{ex}}'
            elif qtype == 'true_false':
                src = rf'\begin{{ex}}Câu {qtype} {level} {i}\choiceTF{{\True a}}{{b}}{{c}}{{d}}\loigiai{{Giải}}\end{{ex}}'
            elif qtype == 'short_answer':
                src = rf'\begin{{ex}}Câu {qtype} {level} {i}\shortans{{42}}\loigiai{{Giải}}\end{{ex}}'
            else:
                src = rf'\begin{{ex}}Câu {qtype} {level} {i}\loigiai{{Giải}}\end{{ex}}'
            q = services.questions.create(src, qtype, cognitive_level=level)
            library.save_metadata(q.id, {
                'taxonomy_id': 'curriculum:math6:lesson:01',
                'subject': 'TOÁN',
                'grade': 'Lớp 6',
                'cognitive_level': level
            })

window = MainWindow(services)
window.resize(1280, 800)
window.show()
window.show_page(2) # Trang Ra đề thi
app.processEvents()
time.sleep(0.3)

exam = window.exam_page

# 1. Chụp Bước 1: Thông tin đề thi & Khung tiêu đề \TieudeT
exam.set_exam_step(0)
exam.title.setText('KIỂM TRA GIỮA HỌC KỲ I')
exam.school_input.setText('TRƯỜNG THPT CHUYÊN HÀ NỘI - AMSTERDAM')
exam.subject_input.setCurrentText('TOÁN')
exam.grade_input.setCurrentText('Lớp 12')
exam.duration_input.setCurrentText('90 phút')
exam.exam_code_input.setText('101')
app.processEvents()
time.sleep(0.3)
window.grab().save(str(out / '1-step1-tieudet-header.png'))

# 2. Chụp Bước 2: Cây CSDL, Khung thống kê 4x4 và Ma trận đề thi
exam.set_exam_step(1)
if 'curriculum:math6:lesson:01' in exam.tree_items:
    exam.select_scope(exam.tree_items['curriculum:math6:lesson:01'])
exam.grid_spins[('mcq', 'NB')].setValue(2)
exam.grid_spins[('mcq', 'TH')].setValue(2)
exam.grid_spins[('true_false', 'NB')].setValue(1)
exam.grid_spins[('true_false', 'TH')].setValue(1)
exam.grid_spins[('short_answer', 'VD')].setValue(1)
exam.save_grid_to_matrix()
app.processEvents()
time.sleep(0.3)
window.grab().save(str(out / '2-step2-tree-and-matrix.png'))

# 3. Chụp Bước 3: Cấu hình xáo trộn và Tóm tắt ma trận
exam.set_exam_step(2)
app.processEvents()
time.sleep(0.3)
window.grab().save(str(out / '3-step3-config-and-summary.png'))

window.close()
app.processEvents()
print('Exam refactor screenshots captured successfully!')
