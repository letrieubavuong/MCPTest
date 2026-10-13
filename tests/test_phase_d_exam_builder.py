import random
import shutil
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.application.library import LibraryService
from latex_question_studio.parsing.latex import parse_questions


def create_sample_questions(services):
    """Tạo bộ câu hỏi mẫu gồm đủ 4 dạng thức và các mức độ nhận thức."""
    q_ids = {}

    # 1. Trắc nghiệm 4 lựa chọn có TikZ bên trong option
    mcq_tikz = (
        r'\begin{ex}' "\n"
        r'Cho hàm số $y=f(x)$. Điểm cực đại của đồ thị hàm số là:' "\n"
        r'\choice{'
        r'\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}'
        r'}{'
        r'\True \begin{tikzpicture}\draw (0,0) circle (0.5);\end{tikzpicture}'
        r'}{'
        r'\begin{tikzpicture}\draw (0,0) rectangle (1,1);\end{tikzpicture}'
        r'}{'
        r'\begin{tikzpicture}\draw (0,0) grid (1,1);\end{tikzpicture}'
        r'}' "\n"
        r'\loigiai{Hình tròn là đáp án đúng.}' "\n"
        r'\end{ex}'
    )
    q1 = services.questions.create(mcq_tikz, 'mcq', cognitive_level='NB')
    q_ids['mcq'] = q1.id

    # 2. Đúng / Sai
    tf_source = (
        r'\begin{ex}' "\n"
        r'Xét tính đúng sai của các mệnh đề sau:' "\n"
        r'\choiceTF{'
        r'\True Mệnh đề A đúng'
        r'}{'
        r'Mệnh đề B sai'
        r'}{'
        r'\True Mệnh đề C đúng'
        r'}{'
        r'Mệnh đề D sai'
        r'}' "\n"
        r'\loigiai{A và C đúng, B và D sai.}' "\n"
        r'\end{ex}'
    )
    q2 = services.questions.create(tf_source, 'true_false', cognitive_level='TH')
    q_ids['tf'] = q2.id

    # 3. Trả lời ngắn
    sa_source = (
        r'\begin{ex}' "\n"
        r'Phương trình $\log_3(x) = 2$ có nghiệm là bao nhiêu?' "\n"
        r'\shortans{9}' "\n"
        r'\loigiai{$x = 3^2 = 9$.}' "\n"
        r'\end{ex}'
    )
    q3 = services.questions.create(sa_source, 'short_answer', cognitive_level='VD')
    q_ids['sa'] = q3.id

    # 4. Tự luận
    essay_source = (
        r'\begin{ex}' "\n"
        r'Giải bất phương trình $2^{2x} - 3 \cdot 2^x + 2 \le 0$.' "\n"
        r'\loigiai{Đặt $t = 2^x > 0$, ta có $t^2 - 3t + 2 \le 0 \Leftrightarrow 1 \le t \le 2 \Leftrightarrow 0 \le x \le 1$.}' "\n"
        r'\end{ex}'
    )
    q4 = services.questions.create(essay_source, 'essay', cognitive_level='VDC')
    q_ids['essay'] = q4.id

    return q_ids


def test_snapshot_reproducibility_and_uniqueness(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)
    library = LibraryService(services)

    # Tạo 10 câu trắc nghiệm
    ids = []
    for i in range(10):
        src = f"\\begin{{ex}}Câu hỏi số {i}?\\choice{{A {i}}}{{\\True B {i}}}{{C {i}}}{{D {i}}}\\loigiai{{Giải {i}}}\\end{{ex}}"
        q = services.questions.create(src, 'mcq', cognitive_level='NB')
        library.save_metadata(q.id, {'subject': 'TOÁN', 'grade': '12'})
        ids.append(q.id)

    matrix = [{'filters': {'cognitive_level': 'NB'}, 'count': 5}]

    # Sinh 2 lần cùng seed=42
    _, snap1 = exam.generate('Đề 1', matrix=matrix, seed=42)
    _, snap2 = exam.generate('Đề 1', matrix=matrix, seed=42)

    assert snap1 == snap2
    q_ids_selected = [q['question_id'] for q in snap1['questions']]
    assert len(q_ids_selected) == 5
    assert len(set(q_ids_selected)) == 5  # Uniqueness không trùng lặp


def test_four_question_types_shuffling_and_answers(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)
    q_ids = create_sample_questions(services)

    all_ids = list(q_ids.values())
    _, snapshot = exam.generate(
        'Đề Đủ 4 Loại',
        manual_ids=all_ids,
        seed=123,
        shuffle_questions=False,
        shuffle_options=True
    )

    questions = snapshot['questions']
    assert len(questions) == 4

    # 1. MCQ: Kiểm tra lựa chọn được xáo và đúng ký tự đáp án
    mcq_item = questions[0]
    parsed_mcq = parse_questions(mcq_item['source'])[0]
    correct_letter = mcq_item['answer']['correct_letter']
    correct_idx = ord(correct_letter) - ord('A')
    assert parsed_mcq.answer['options'][correct_idx]['correct']
    assert 'circle' in parsed_mcq.answer['options'][correct_idx]['source']

    # 2. True/False: Giữ đúng mảng truth
    tf_item = questions[1]
    assert tf_item['answer']['truth'] == [True, False, True, False]

    # 3. Short answer: Giữ đúng value
    sa_item = questions[2]
    assert sa_item['answer']['value'] == '9'

    # 4. Essay: Giữ essay True
    essay_item = questions[3]
    assert essay_item['answer']['essay'] is True


def test_generate_multiple_variants(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)
    q_ids = create_sample_questions(services)

    codes = ['101', '102', '103', '104']
    multi_results = exam.generate_multiple(
        title='Đề Thi Thử Tốt Nghiệp',
        manual_ids=list(q_ids.values()),
        base_seed=2026,
        exam_codes=codes,
        shuffle_questions=True,
        shuffle_options=True
    )

    assert len(multi_results) == 4
    snapshots = [snap for _, snap in multi_results]

    for i, snap in enumerate(snapshots):
        assert snap['exam_code'] == codes[i]
        assert len(snap['questions']) == 4

    # Khác mã đề sẽ có hoán vị ngẫu nhiên khác nhau giữa các mã
    perms = [tuple(q['question_id'] for q in s['questions']) for s in snapshots]
    # Không phải tất cả đều giống nhau
    assert len(set(perms)) > 1 or len(codes) <= 1


def test_check_matrix_availability(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)

    services.questions.create(r'\begin{ex}Q1\choice{a}{\True b}{c}{d}\end{ex}', 'mcq', cognitive_level='NB')
    services.questions.create(r'\begin{ex}Q2\choice{a}{\True b}{c}{d}\end{ex}', 'mcq', cognitive_level='NB')

    # Ma trận yêu cầu 5 câu NB (chỉ có 2 câu)
    matrix = [{'filters': {'cognitive_level': 'NB'}, 'count': 5, 'scope_name': 'Chương 1'}]
    res = exam.check_matrix_availability(matrix)
    assert not res['ok']
    assert len(res['warnings']) == 1
    assert res['warnings'][0]['required'] == 5
    assert res['warnings'][0]['available'] == 2

    # Ma trận yêu cầu 2 câu NB (vừa đủ)
    matrix_ok = [{'filters': {'cognitive_level': 'NB'}, 'count': 2, 'scope_name': 'Chương 1'}]
    res_ok = exam.check_matrix_availability(matrix_ok)
    assert res_ok['ok']
    assert len(res_ok['warnings']) == 0


def test_cancellation_during_export(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)
    q_ids = create_sample_questions(services)
    _, snapshot = exam.generate('Test Cancel', manual_ids=list(q_ids.values()))

    # Hủy ngay lập tức
    with pytest.raises(InterruptedError, match="Đã hủy xuất đề thi"):
        exam.export_bundle(
            snapshot,
            tmp_path / 'bundle_cancel',
            compile_pdf=False,
            cancelled=lambda: True
        )
