"""Tests for new lesson creation, pedagogical templates, method bundle and dialog."""
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.lessons import (
    LessonService, LESSON_TEMPLATES, build_template_blocks, block
)
from latex_question_studio.ui.lesson_dialog import NewLessonDialog, EditLessonInfoDialog
from latex_question_studio.ui.main_window import MainWindow


def setup(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    return services, LessonService(services)


def test_build_template_blocks():
    # Standard template
    std = build_template_blocks('standard', num_methods=2, include_warmup=True, include_homework=True)
    kinds = [b['kind'] for b in std]
    titles = [b['title'] for b in std]
    assert 'theory' in kinds and 'method' in kinds and 'example' in kinds and 'exercise' in kinds
    assert any('Mục tiêu' in t for t in titles)
    assert any('Khởi động' in t for t in titles)
    assert any('Hướng dẫn tự học' in t for t in titles)
    # Check parent linkages
    methods = [b for b in std if b['kind'] == 'method']
    assert len(methods) == 2
    for m in methods:
        children = [b for b in std if b.get('parent') == m['id']]
        assert any(c['kind'] == 'example' for c in children)
        assert any(c['kind'] == 'exercise' for c in children)

    # Methods template
    methods_b = build_template_blocks('methods', num_methods=3, include_homework=False)
    assert len([b for b in methods_b if b['kind'] == 'method']) == 3
    assert not any('C. Bài tập rèn luyện nâng cao' in b['title'] for b in methods_b)

    # Theory template
    theory_b = build_template_blocks('theory')
    assert any('Khám phá kiến thức' in b['title'] for b in theory_b)

    # Worksheet template
    ws = build_template_blocks('worksheet')
    assert len(ws) == 4
    assert any('Trắc nghiệm Đúng / Sai' in b['title'] for b in ws)

    # Blank template
    blank = build_template_blocks('blank')
    assert len(blank) == 1
    assert blank[0]['title'] == 'Nội dung bài giảng'

    # Legacy template (default)
    leg = build_template_blocks('legacy')
    assert len(leg) == 4


def test_lesson_service_create_with_template_and_metadata(tmp_path):
    services, lessons = setup(tmp_path)
    doc = lessons.create(
        title='Khảo sát hàm số nâng cao',
        subject='Toán',
        grade='12',
        template_key='standard',
        num_methods=3,
        include_warmup=True,
        include_homework=True
    )
    assert doc['title'] == 'Khảo sát hàm số nâng cao'
    assert doc['subject'] == 'Toán'
    assert doc['grade'] == '12'
    assert doc['template_key'] == 'standard'
    assert len(doc['blocks']) > 6
    assert len(doc['files']) >= 3

    # Ensure persistence
    retrieved = lessons.get(doc['id'])
    assert retrieved['title'] == doc['title']
    assert retrieved['subject'] == 'Toán'


def test_add_method_bundle_and_duplicate_block(tmp_path):
    services, lessons = setup(tmp_path)
    doc = lessons.create('Bài kiểm tra bundle')
    orig_count = len(doc['blocks'])
    doc, new_m_id = lessons.add_method_bundle(doc)
    assert len(doc['blocks']) == orig_count + 3
    method_block = next(b for b in doc['blocks'] if b['id'] == new_m_id)
    assert method_block['kind'] == 'method'
    assert 'Dạng' in method_block['title']
    children = [b for b in doc['blocks'] if b.get('parent') == new_m_id]
    assert len(children) == 2
    assert any(c['kind'] == 'example' for c in children)
    assert any(c['kind'] == 'exercise' for c in children)

    # Duplicate block
    doc, dup_id = lessons.duplicate_block(doc, new_m_id)
    assert dup_id is not None
    dup_block = next(b for b in doc['blocks'] if b['id'] == dup_id)
    assert '(bản sao)' in dup_block['title']
    dup_children = [b for b in doc['blocks'] if b.get('parent') == dup_id]
    assert len(dup_children) == 2


def test_new_lesson_dialog_ui(qtbot, tmp_path):
    services, lessons = setup(tmp_path)
    dlg = NewLessonDialog(services)
    qtbot.addWidget(dlg)

    # Test title input and chip button
    dlg.title_input.setText("Bài hàm số")
    dlg._apply_chip("Chuyên đề:")
    assert dlg.title_input.text() == "Chuyên đề: Bài hàm số"

    # Test template combo changes update preview
    dlg.template_combo.setCurrentIndex(dlg.template_combo.findData('methods'))
    assert dlg.tree_preview.topLevelItemCount() > 0

    # Test custom method count
    dlg.num_methods_spin.setValue(3)
    dlg.update_preview()
    methods_in_preview = [b for b in dlg.preview_blocks if b['kind'] == 'method']
    assert len(methods_in_preview) == 3

    # Test create_lesson helper
    created_doc = dlg.create_lesson(lessons)
    assert created_doc['id']
    assert created_doc['title'] == "Chuyên đề: Bài hàm số"
    assert created_doc['template_key'] == 'methods'


def test_edit_lesson_info_dialog(qtbot, tmp_path):
    services, lessons = setup(tmp_path)
    doc = lessons.create('Bài cũ', subject='Toán', grade='12')
    dlg = EditLessonInfoDialog(services, doc)
    qtbot.addWidget(dlg)

    dlg.title_input.setText("Bài mới đã sửa")
    idx = dlg.subject_combo.findText("Vật lý")
    if idx >= 0:
        dlg.subject_combo.setCurrentIndex(idx)
    g_idx = dlg.grade_combo.findData("10")
    if g_idx >= 0:
        dlg.grade_combo.setCurrentIndex(g_idx)

    updated = dlg.apply_to_doc(doc)
    assert updated['title'] == "Bài mới đã sửa"
    assert updated['subject'] == "Vật lý"
    assert updated['grade'] == "10"


def test_lesson_page_toolbar_and_helpers(qtbot, tmp_path):
    services, lessons = setup(tmp_path)
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(4)
    page = window.lesson_page

    # Verify badge exists
    assert hasattr(page, 'meta_badge')
    assert hasattr(page, 'revision_badge')

    # Add method bundle on page
    page.new_lesson(False)
    init_blocks = len(page.doc['blocks'])
    page.add_method_bundle()
    assert len(page.doc['blocks']) == init_blocks + 3

    # Duplicate current block on page
    page.current_id = page.doc['blocks'][0]['id']
    page.duplicate_current_block()
    assert '(bản sao)' in page.doc['blocks'][-1]['title']
    window.close()
