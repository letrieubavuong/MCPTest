import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.exams import ExamService
from latex_question_studio.ui.exam_dialog import ExamDialog, TieudeTPreviewCard


def populate_bank(tmp_path):
    services = create_services(AppConfig.load(tmp_path))
    library = LibraryService(services)
    created = {}

    types = ('mcq', 'true_false', 'short_answer', 'essay')
    levels = ('NB', 'TH', 'VD', 'VDC')

    # Tạo mỗi loại và mỗi mức độ ít nhất 2 câu
    for qtype in types:
        for level in levels:
            key = (qtype, level)
            created[key] = []
            for i in range(2):
                if qtype == 'mcq':
                    src = rf'\begin{{ex}}Câu {qtype} {level} {i}\choice{{\True A}}{{B}}{{C}}{{D}}\loigiai{{G}}\end{{ex}}'
                elif qtype == 'true_false':
                    src = rf'\begin{{ex}}Câu {qtype} {level} {i}\choiceTF{{\True a}}{{b}}{{c}}{{d}}\loigiai{{G}}\end{{ex}}'
                elif qtype == 'short_answer':
                    src = rf'\begin{{ex}}Câu {qtype} {level} {i}\shortans{{42}}\loigiai{{G}}\end{{ex}}'
                else:
                    src = rf'\begin{{ex}}Câu {qtype} {level} {i}\loigiai{{G}}\end{{ex}}'

                q = services.questions.create(src, qtype, cognitive_level=level)
                library.save_metadata(q.id, {
                    'taxonomy_id': 'curriculum:math10:lesson:01',
                    'subject': 'TOÁN',
                    'grade': 'Lớp 10',
                    'cognitive_level': level
                })
                created[key].append(q.id)

    return services, created


def test_tieudet_header_generation_and_preview(tmp_path):
    services, created = populate_bank(tmp_path)
    exam = ExamService(services)

    # Sinh đề với metadata đầy đủ chuẩn \TieudeT
    v, snap = exam.generate(
        title='Đề kiểm tra giữa kỳ 1',
        subject='TOÁN 12',
        grade='Lớp 12',
        duration='90 phút',
        school='TRƯỜNG THPT CHUYÊN HÀ NỘI - AMSTERDAM',
        exam_code='101',
        matrix=[{
            'taxonomy_id': 'curriculum:math10:lesson:01',
            'filters': {'question_type': 'mcq', 'cognitive_level': 'NB'},
            'count': 1
        }],
        seed=12345
    )

    assert snap['title'] == 'Đề kiểm tra giữa kỳ 1'
    assert snap['subject'] == 'TOÁN 12'
    assert snap['school'] == 'TRƯỜNG THPT CHUYÊN HÀ NỘI - AMSTERDAM'
    assert snap['exam_code'] == '101'
    assert snap['duration'] == '90 phút'

    tex = exam.content(snap)
    assert r'\TieudeT{Đề kiểm tra giữa kỳ 1}' in tex
    assert r'\def\subject{TOÁN 12}' in tex
    assert r'\ifcsname TieudeT\endcsname' in tex
    assert 'TRƯỜNG THPT CHUYÊN HÀ NỘI - AMSTERDAM' in tex
    assert 'MÃ ĐỀ: 101' in tex


def test_tieudet_preview_card_reactive_update(qtbot):
    card = TieudeTPreviewCard()
    qtbot.addWidget(card)

    card.update_header(
        title='Thi thử tốt nghiệp THPT',
        subject='VẬT LÍ',
        grade='Lớp 12',
        duration='50 phút',
        school='SỞ GD&ĐT HÀ NỘI',
        exam_code='204'
    )

    assert card.lbl_title.text() == 'THI THỬ TỐT NGHIỆP THPT'
    assert 'VẬT LÍ' in card.lbl_subject.text()
    assert '50 phút' in card.lbl_duration.text()
    assert card.lbl_school.text() == 'SỞ GD&ĐT HÀ NỘI'
    assert '204' in card.lbl_code.text()


def test_matrix_statistics_full_distribution(tmp_path):
    services, created = populate_bank(tmp_path)
    exam = ExamService(services)

    stats = exam.matrix_statistics('curriculum:math10:lesson:01')
    mat = stats['matrix']

    for qtype in ('mcq', 'true_false', 'short_answer', 'essay'):
        for lvl in ('NB', 'TH', 'VD', 'VDC'):
            assert mat[qtype][lvl] == 2, f"Failed for {qtype} {lvl}"
        assert mat[qtype]['total'] == 8

    assert stats['total'] == 32
    assert stats['invalid'] == 0


def test_exam_dialog_save_grid_to_matrix_and_random_selection(qtbot, tmp_path):
    services, created = populate_bank(tmp_path)
    page = ExamDialog([], services=services)
    qtbot.addWidget(page)

    page.title.setText('Đề thi toán')
    page.subject_input.setCurrentText('TOÁN')
    page.school_input.setText('TRƯỜNG THPT XYZ')
    page.exam_code_input.setText('105')

    # Chọn node bài trong cây
    node = page.tree_items['curriculum:math10:lesson:01']
    page.select_scope(node)

    # Đặt số lượng trong lưới 4x4
    page.grid_spins[('mcq', 'NB')].setValue(2)
    page.grid_spins[('true_false', 'TH')].setValue(1)
    page.grid_spins[('short_answer', 'VD')].setValue(1)

    # Lưu vào ma trận
    page.save_grid_to_matrix()

    assert page.matrix.rowCount() == 3
    assert 'Ma trận: 4 câu' in page.matrix_summary.text()

    values = page.values()
    assert values['title'] == 'Đề thi toán'
    assert values['school'] == 'TRƯỜNG THPT XYZ'
    assert values['exam_code'] == '105'
    assert len(values['matrix']) == 3

    # Dựa vào ma trận để rút ngẫu nhiên số câu hỏi tương ứng
    exam = ExamService(services)
    v, snap = exam.generate(**values)

    assert len(snap['questions']) == 4
    # Kiểm tra không có câu nào bị trùng ID
    qids = [q['question_id'] for q in snap['questions']]
    assert len(set(qids)) == 4


def test_tree_subject_filtering_and_search(qtbot, tmp_path):
    services, created = populate_bank(tmp_path)
    page = ExamDialog([], services=services)
    qtbot.addWidget(page)

    # Lọc môn
    page.subject_filter.setCurrentIndex(1)  # TOÁN
    all_item = page.tree.topLevelItem(0)
    assert all_item is not None

    # Tìm kiếm
    page.tree_search.setText('Bài 1')
    # Kiểm tra tree_search chạy mượt không raise lỗi
    page.tree_search.setText('')
