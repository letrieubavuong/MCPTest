import json
import pytest
from PySide6.QtCore import Qt
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService
from latex_question_studio.ui.import_dialog import ImportReview
from latex_question_studio.ui.main_window import MainWindow


def test_autodetect_cognitive_levels_from_tags_and_comments(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    importer = ImportService(services)
    tex_file = tmp_path / 'cognitive.tex'
    tex_file.write_text(r"""\begin{ex}%[NB]
Câu nhận biết
\choice{\True A}{B}{C}{D}
\end{ex}
\begin{ex}[TH]
Câu thông hiểu
\choice{A}{\True B}{C}{D}
\end{ex}
\begin{ex}%[VD]
Câu vận dụng
\choice{A}{B}{\True C}{D}
\end{ex}
\begin{ex}[VDC]
Câu vận dụng cao
\choice{A}{B}{C}{\True D}
\end{ex}
""", encoding='utf-8')
    batch, results = importer.stage([tex_file])
    assert len(results) == 4
    levels = [r['parsed']['classification']['cognitive_level'] for r in results]
    assert levels == ['NB', 'TH', 'VD', 'VDC']


def test_import_review_inline_repair_and_filter_actions(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    importer = ImportService(services)
    tex_file = tmp_path / 'repair_test.tex'
    tex_file.write_text(r"""\begin{ex}%[NB]
Câu hợp lệ ban đầu
\choice{\True A}{B}{C}{D}
\end{ex}
\begin{ex}
Câu có lỗi cú pháp \choice{A}{B
\end{ex}
""", encoding='utf-8')
    batch, results = importer.stage([tex_file])
    assert len(results) == 2
    assert len(results[1]['errors']) > 0

    review = ImportReview(results, services=services)
    qtbot.addWidget(review)
    review.show()

    # Kiểm tra các filter mới:
    # 4: Chỉ câu hợp lệ
    review.only_missing.setCurrentIndex(4)
    assert len(review.visible_indices) == 1 and review.visible_indices[0] == 0

    # 5: Chỉ câu có lỗi
    review.only_missing.setCurrentIndex(5)
    assert len(review.visible_indices) == 1 and review.visible_indices[0] == 1

    # Thử sửa câu lỗi số 1 thông qua repair_current_question
    review.show_source(1)
    repaired_source = r"""\begin{ex}%[TH]
Câu đã sửa lỗi
\choice{\True A}{B}{C}{D}
\loigiai{Lời giải chi tiết}
\end{ex}"""
    review.source.setPlainText(repaired_source)
    review.repair_current_question()

    # Sau khi sửa, câu 1 không còn lỗi và nhận mức TH
    assert len(review.results[1]['errors']) == 0
    assert review.results[1]['parsed']['classification']['cognitive_level'] == 'TH'

    # Filter câu hợp lệ lúc này chứa cả 2 câu
    review.only_missing.setCurrentIndex(4)
    assert len(review.visible_indices) == 2

    # Thử batch selection helpers
    review.deselect_all_rows()
    assert len(review.selected_ids()) == 0
    review.select_all_rows()
    assert len(review.selected_ids()) == 2
    review.select_valid_only()
    assert len(review.selected_ids()) == 2

    review.close()


def test_direct_text_import_flow(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(1)

    flow = window.import_workflow
    latex_text = r"""\begin{ex}%[NB]
Câu trực tiếp một
\choice{\True A}{B}{C}{D}
\end{ex}
\begin{ex}%[VD]
Câu trực tiếp hai
\choice{A}{\True B}{C}{D}
\end{ex}
"""
    flow.direct_text.setPlainText(latex_text)
    qtbot.mouseClick(flow.paste_button, Qt.MouseButton.LeftButton)

    # Chờ import job hoàn thành
    qtbot.waitUntil(lambda: getattr(window, 'import_job', None) is None, timeout=5000)
    assert flow.pages.currentIndex() == 3
    assert hasattr(window, 'import_review') and len(window.import_review.results) == 2
    assert window.import_review.results[0]['parsed']['classification']['cognitive_level'] == 'NB'
    assert window.import_review.results[1]['parsed']['classification']['cognitive_level'] == 'VD'

    window.close()
