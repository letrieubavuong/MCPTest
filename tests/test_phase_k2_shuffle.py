r"""Tests for Phase K2: Shuffle Engine and Invariant Enforcement.

Validates that:
- MCQ: Questions and options are shuffled; answer letter matches shifted \True option.
- True/False: Questions are shuffled, but statements a, b, c, d NEVER shuffle (permutation == [0, 1, 2, 3]).
- Short Answer: Questions are shuffled; answer values preserved.
- Essay: Questions NEVER shuffle; original order preserved.
- Questions NEVER cross between parts (Part I: MCQ, Part II: TF, Part III: SA, Part IV: Essay).
- 100+ seeds deterministic reproduction.
"""
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.parsing.latex import parse_questions


def create_sample_bank(services):
    q_map = {}
    # 3 MCQ questions
    mcqs = []
    for i in range(3):
        src = f"""\\begin{{ex}}
Câu hỏi MCQ {i}?
\\choice
{{Sai 1 {i}}}
{{\\True Dung 2 {i}}}
{{Sai 3 {i}}}
{{Sai 4 {i}}}
\\loigiai{{Giai {i}}}
\\end{{ex}}"""
        q = services.questions.create(src, 'mcq')
        mcqs.append(q.id)
    q_map['mcq'] = mcqs

    # 3 True/False questions
    tfs = []
    for i in range(3):
        src = f"""\\begin{{ex}}
Câu hỏi TF {i}?
\\choiceTF
{{\\True Menh de a {i}}}
{{Menh de b {i}}}
{{\\True Menh de c {i}}}
{{Menh de d {i}}}
\\loigiai{{Giai {i}}}
\\end{{ex}}"""
        q = services.questions.create(src, 'true_false')
        tfs.append(q.id)
    q_map['true_false'] = tfs

    # 2 Short answer questions
    sas = []
    for i in range(2):
        src = f"""\\begin{{ex}}
Câu hỏi SA {i}?
\\shortans{{{10 + i}}}
\\loigiai{{Giai {i}}}
\\end{{ex}}"""
        q = services.questions.create(src, 'short_answer')
        sas.append(q.id)
    q_map['short_answer'] = sas

    # 2 Essay questions
    essays = []
    for i in range(2):
        src = f"""\\begin{{ex}}
Câu hỏi Essay {i}?
Chứng minh định lý {i}.
\\loigiai{{Giai {i}}}
\\end{{ex}}"""
        q = services.questions.create(src, 'essay')
        essays.append(q.id)
    q_map['essay'] = essays

    return q_map


def test_phase_k2_partition_and_section_invariants(tmp_path):
    s = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(s)
    q_map = create_sample_bank(s)

    # Intentionally shuffle order of candidate IDs passed manually
    mixed_ids = (
        [q_map['essay'][1]] +
        [q_map['short_answer'][0]] +
        [q_map['mcq'][2]] +
        [q_map['true_false'][1]] +
        [q_map['essay'][0]] +
        [q_map['mcq'][0]] +
        [q_map['true_false'][0]] +
        [q_map['short_answer'][1]] +
        [q_map['mcq'][1]] +
        [q_map['true_false'][2]]
    )

    _, snap = exam.generate('De K2 Invariant', manual_ids=mixed_ids, seed=42, shuffle_questions=True, shuffle_options=True)
    questions = snap['questions']
    assert len(questions) == 10

    # Section 1: Questions 0..2 MUST be MCQ
    for i in range(0, 3):
        assert questions[i]['question_type'] == 'mcq'
        assert questions[i]['question_id'] in q_map['mcq']
        # MCQ options were shuffled and correct_letter matches \True
        ans = questions[i]['answer']
        assert 'correct_letter' in ans
        target_idx = ord(ans['correct_letter']) - 65
        opts = parse_questions(questions[i]['source'])[0].answer['options']
        assert opts[target_idx]['correct'] is True

    # Section 2: Questions 3..5 MUST be True/False
    for i in range(3, 6):
        assert questions[i]['question_type'] == 'true_false'
        assert questions[i]['question_id'] in q_map['true_false']
        # Invariant Phase K2: statements a, b, c, d MUST NOT BE SHUFFLED
        assert questions[i]['permutation'] == [0, 1, 2, 3]
        ans = questions[i]['answer']
        assert ans['truth'] == [True, False, True, False]
        # Check source text preserves order
        assert "Menh de a" in questions[i]['source']
        assert "Menh de b" in questions[i]['source']
        assert "Menh de c" in questions[i]['source']
        assert "Menh de d" in questions[i]['source']

    # Section 3: Questions 6..7 MUST be Short Answer
    for i in range(6, 8):
        assert questions[i]['question_type'] == 'short_answer'
        assert questions[i]['question_id'] in q_map['short_answer']
        assert questions[i]['permutation'] == []
        ans = questions[i]['answer']
        assert ans['value'] in ('10', '11')

    # Section 4: Questions 8..9 MUST be Essay
    for i in range(8, 10):
        assert questions[i]['question_type'] == 'essay'
        assert questions[i]['question_id'] in q_map['essay']
        assert questions[i]['permutation'] == []
        assert questions[i]['answer'] == {'essay': True}

    # Invariant Phase K2: Essay order MUST be preserved as chosen (essay[1] then essay[0] from mixed_ids)
    assert questions[8]['question_id'] == q_map['essay'][1]
    assert questions[9]['question_id'] == q_map['essay'][0]


def test_phase_k2_100_seeds_deterministic_reproducibility(tmp_path):
    s = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(s)
    q_map = create_sample_bank(s)
    all_ids = q_map['mcq'] + q_map['true_false'] + q_map['short_answer'] + q_map['essay']

    for seed in range(100):
        _, snap1 = exam.generate('Seed Test', manual_ids=all_ids, seed=seed)
        _, snap2 = exam.generate('Seed Test', manual_ids=all_ids, seed=seed)
        assert snap1 == snap2

        # Verify True/False invariants on EVERY seed
        for q in snap1['questions']:
            if q['question_type'] == 'true_false':
                assert q['permutation'] == [0, 1, 2, 3]
                assert q['answer']['truth'] == [True, False, True, False]
            elif q['question_type'] == 'essay':
                assert q['permutation'] == []
                assert q['answer'] == {'essay': True}
            elif q['question_type'] == 'mcq':
                # Verify correct letter points to true option
                letter = q['answer']['correct_letter']
                idx = ord(letter) - 65
                opts = parse_questions(q['source'])[0].answer['options']
                assert opts[idx]['correct'] is True
