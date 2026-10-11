"""Capture the working visual lesson editor with synthetic data and real TeX."""
from pathlib import Path
import time
import uuid

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


root=Path(__file__).resolve().parents[1]
out=root/'artifacts/wysiwyg';out.mkdir(parents=True,exist_ok=True)
data=root/'.runtime'/('wysiwyg-visual-'+uuid.uuid4().hex[:8])
app=QApplication([]);services=create_services(AppConfig.load(data))
window=MainWindow(services);window.setWindowFlag(Qt.WindowType.FramelessWindowHint)
window.show();window.show_page(4)
page=window.lesson_page;page.new_lesson();page.title.setText('Bài giảng: Phân thức đại số')
source=r"""\subsection*{Phương pháp rút gọn}
Rút gọn phân thức bằng cách \textbf{phân tích thành nhân tử}.
Với điều kiện $x\ne 2$, ta có:
\[\frac{x^2-4}{x-2}=x+2.\]
\begin{ex}
Tính giá trị của biểu thức khi $x=3$.
\choice{3}{4}{\True 5}{6}
\loigiai{Thay vào biểu thức đã rút gọn, ta được $3+2=5$.}
\end{ex}
"""
page.editor.setPlainText(source)
deadline=time.monotonic()+55
while (len(page.visual_editor.images)<4 or page.visual_editor.source()!=source) and time.monotonic()<deadline:
    app.processEvents();time.sleep(.025)
assert len(page.visual_editor.images)>=4, 'Formulas did not render'
assert page.save()
for theme in ('light','dark'):
    window.theme=theme;window.apply_theme()
    for width,height in ((1366,768),(1024,768),(1600,900)):
        window.resize(width,height)
        for _ in range(8):app.processEvents();time.sleep(.02)
        assert window.width()==width and window.height()==height
        assert window.grab().save(str(out/f'{theme}-{width}x{height}.png'))
        print(f'{theme} {width}x{height}',flush=True)
page.preview_scope.setCurrentIndex(1);page.start_preview()
deadline=time.monotonic()+30
while not page.pdf and time.monotonic()<deadline:app.processEvents();time.sleep(.025)
assert page.pdf, page.status.text()
window.resize(1366,768);app.processEvents()
assert window.grab().save(str(out/'pdf-1366x768.png'))
window.close();app.processEvents()
