r"""Tests for Phase K3: Serializer and MAPClass 4-Part Exam Structure.

Validates that:
- Header has \def\subject{...} before \TieudeT{...}.
- 4 parts appear in exact required order:
    \PhanI -> \begin{cauhoiTN}{DeXX} ... \end{cauhoiTN}
    \PhanII -> \begin{cauhoiDS}{DeXX} ... \end{cauhoiDS}
    \PhanIII -> \begin{cauhoiTLN}{DeXX} ... \end{cauhoiTLN}
    \PhanTL -> \begin{cauhoiTL}{DeXX} ... \end{cauhoiTL}
- Empty parts are omitted.
- Student vs Teacher vs Answer Key generation.
- Real compilation via pdfLaTeX using MAPClass.cls and ex_test.sty with automatic Loigiai creation.
"""
import shutil
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.preview.compiler import Compiler, MAPCLASS_PREAMBLE


def test_serializer_four_parts_structure_contract(tmp_path):
    s = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(s)

    q1 = s.questions.create(r'\begin{ex}Câu 1 MCQ?\choice{A}{\True B}{C}{D}\loigiai{LG 1}\end{ex}', 'mcq')
    q2 = s.questions.create(r'\begin{ex}Câu 2 TF?\choiceTF{\True A}{B}{\True C}{D}\loigiai{LG 2}\end{ex}', 'true_false')
    q3 = s.questions.create(r'\begin{ex}Câu 3 SA?\shortans{42}\loigiai{LG 3}\end{ex}', 'short_answer')
    q4 = s.questions.create(r'\begin{ex}Câu 4 Essay?\loigiai{LG 4}\end{ex}', 'essay')

    _, snapshot = exam.generate(
        'KIỂM TRA HỌC KỲ I',
        manual_ids=[q1.id, q2.id, q3.id, q4.id],
        seed=1,
        exam_code='01'
    )

    body = exam.content(snapshot, solutions=False)

    # 1. Verify header
    assert r"\def\subject{TOÁN}" in body
    assert r"\TieudeT{KIỂM TRA HỌC KỲ I}" in body

    # 2. Verify all 4 parts and environments with tag De01
    assert r"\PhanI" in body
    assert r"\begin{cauhoiTN}{De01}" in body
    assert r"\end{cauhoiTN}" in body

    assert r"\PhanII" in body
    assert r"\begin{cauhoiDS}{De01}" in body
    assert r"\end{cauhoiDS}" in body

    assert r"\PhanIII" in body
    assert r"\begin{cauhoiTLN}{De01}" in body
    assert r"\end{cauhoiTLN}" in body

    assert r"\PhanTL" in body
    assert r"\begin{cauhoiTL}{De01}" in body
    assert r"\end{cauhoiTL}" in body

    # 3. Verify ordering of sections
    idx_p1 = body.find(r"\PhanI")
    idx_p2 = body.find(r"\PhanII")
    idx_p3 = body.find(r"\PhanIII")
    idx_p4 = body.find(r"\PhanTL")
    assert 0 < idx_p1 < idx_p2 < idx_p3 < idx_p4

    # 4. In student body, \True and \loigiai must not be present
    assert r"\True" not in body
    assert "LG 1" not in body
    assert "LG 2" not in body


def test_serializer_omits_empty_parts(tmp_path):
    s = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(s)

    # Exam with only MCQ and Short Answer (no TF, no Essay)
    q1 = s.questions.create(r'\begin{ex}Câu 1 MCQ?\choice{A}{\True B}{C}{D}\end{ex}', 'mcq')
    q2 = s.questions.create(r'\begin{ex}Câu 2 SA?\shortans{100}\end{ex}', 'short_answer')

    _, snapshot = exam.generate('Đề thi rút gọn', manual_ids=[q1.id, q2.id], seed=1, exam_code='De02')
    body = exam.content(snapshot)

    assert r"\PhanI" in body
    assert r"\begin{cauhoiTN}{De02}" in body
    assert r"\PhanIII" in body
    assert r"\begin{cauhoiTLN}{De02}" in body

    # Parts II and IV must be omitted
    assert r"\begin{cauhoiDS}" not in body
    assert (r"\PhanII" + "\n") not in body
    assert r"\PhanTL" not in body
    assert r"\begin{cauhoiTL}" not in body


def test_serializer_answer_key_format(tmp_path):
    s = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(s)

    q1 = s.questions.create(r'\begin{ex}MCQ?\choice{A}{\True B}{C}{D}\end{ex}', 'mcq')
    q2 = s.questions.create(r'\begin{ex}TF?\choiceTF{\True A}{B}{\True C}{D}\end{ex}', 'true_false')
    q3 = s.questions.create(r'\begin{ex}SA?\shortans{99}\end{ex}', 'short_answer')

    _, snapshot = exam.generate('Đáp án mẫu', manual_ids=[q1.id, q2.id, q3.id], seed=7)
    ans_tex = exam.content(snapshot, answer_only=True)

    assert "PHẦN I" in ans_tex
    assert "PHẦN II" in ans_tex
    assert "PHẦN III" in ans_tex
    assert "Đ" in ans_tex and "S" in ans_tex
    assert "99" in ans_tex


@pytest.mark.skipif(not shutil.which('pdflatex'), reason='pdfLaTeX missing')
def test_real_pdflatex_compile_mapclass_4parts(tmp_path):
    s = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(s)

    q1 = s.questions.create(r'\begin{ex}Cho tam giác đều $ABC$. Góc giữa $AB$ và $BC$ bằng:\choice{$60^\circ$}{\True $120^\circ$}{$30^\circ$}{$90^\circ$}\loigiai{Góc bằng $120^\circ$.}\end{ex}', 'mcq')
    q2 = s.questions.create(r'\begin{ex}Cho hình hộp $ABCD.A^\prime B^\prime C^\prime D^\prime$. Xét tính đúng sai:\choiceTF{\True $AA^\prime \parallel CC^\prime$}{$AB \perp CC^\prime$}{\True $A^\prime C \cap BD^\prime \ne \emptyset$}{$AD \parallel A^\prime B^\prime$}\loigiai{Mệnh đề a và c đúng.}\end{ex}', 'true_false')
    q3 = s.questions.create(r'\begin{ex}Giá trị nhỏ nhất của $y=x^2-4x+5$ là:\shortans{1}\loigiai{$(x-2)^2+1 \ge 1$.}\end{ex}', 'short_answer')
    q4 = s.questions.create(r'\begin{ex}Giải phương trình: $\sqrt{x-1} = 2$.\loigiai{Điều kiện $x \ge 1$. $x-1 = 4 \iff x = 5$.}\end{ex}', 'essay')

    _, snapshot = exam.generate('Đề thi thử 4 phần', manual_ids=[q1.id, q2.id, q3.id, q4.id], seed=10, exam_code='De01')

    # 1. Compile student PDF
    student_pdf = tmp_path / 'student.pdf'
    res_student = exam.export_pdf(snapshot, student_pdf, solutions=False, preamble_file=None)
    assert res_student.ok, res_student.log
    assert student_pdf.is_file() and student_pdf.stat().st_size > 1000

    # 2. Compile teacher PDF
    teacher_pdf = tmp_path / 'teacher.pdf'
    res_teacher = exam.export_pdf(snapshot, teacher_pdf, solutions=True, preamble_file=None)
    assert res_teacher.ok, res_teacher.log
    assert teacher_pdf.is_file() and teacher_pdf.stat().st_size > 1000
