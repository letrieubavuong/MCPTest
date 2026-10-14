import pytest
from pathlib import Path

from latex_question_studio.application.lessons import student_source, STUDENT_COMMANDS
from latex_question_studio.preview.compiler import Compiler


def test_dapso_and_dapsotl_stripped_cleanly():
    r"""Kiểm tra \dapso (với arg tùy chọn [A] và {B}) và \dapsoTL bị loại bỏ hoàn toàn trong đề học sinh."""
    source = (
        r"\begin{ex}" "\n"
        r"Một vật rơi tự do từ độ cao $h$. Tính thời gian rơi." "\n"
        r"\dapso[A]{$t = \sqrt{2h/g}$}" "\n"
        r"\choice" "\n"
        r"{\True $t = \sqrt{2h/g}$}" "\n"
        r"{$t = \sqrt{h/g}$}" "\n"
        r"{$t = 2h/g$}" "\n"
        r"{$t = \sqrt{h/2g}$}" "\n"
        r"\loigiai{Áp dụng công thức $h = \frac{1}{2}gt^2 \Rightarrow t = \sqrt{\frac{2h}{g}}$}" "\n"
        r"\end{ex}"
    )

    # 1. Đề học sinh: Không được chứa \True, \dapso, \loigiai, hoặc nội dung lời giải
    student = student_source(source, hide_answers=True)
    assert r"\True" not in student
    assert r"\dapso" not in student
    assert r"\loigiai" not in student
    assert "Áp dụng công thức" not in student
    # Nội dung câu hỏi và các lựa chọn vẫn giữ nguyên
    assert "Một vật rơi tự do" in student
    assert r"$t = \sqrt{2h/g}$" in student

    # 2. Đề giáo viên: Giữ nguyên \dapso và \loigiai
    teacher = student_source(source, hide_answers=False)
    assert r"\dapso" in teacher
    assert r"\loigiai" in teacher


def test_dapsotl_short_answer():
    source = (
        r"\begin{ex}" "\n"
        r"Một con lắc lò xo có $k = 100$ N/m, $m = 100$ g. Chu kì dao động là bao nhiêu?" "\n"
        r"\dapsoTL{0.2}" "\n"
        r"\shortans{0.2}" "\n"
        r"\loigiai{Ta có $T = 2\pi\sqrt{m/k} = 0.2$ s.}" "\n"
        r"\end{ex}"
    )
    student = student_source(source, hide_answers=True)
    assert r"\dapsoTL" not in student
    assert r"\shortans" not in student
    assert r"\loigiai" not in student
    assert "0.2" not in student
    assert "Một con lắc lò xo" in student


def test_immini_with_tkz_euclide_and_nested_answers():
    r"""Kiểm tra \immini kết hợp hình vẽ tkz-euclide và lời giải nằm lồng bên trong."""
    source = (
        r"\begin{ex}" "\n"
        r"\immini{" "\n"
        r"  Cho tam giác $ABC$ vuông tại $A$. Biết $AB = 3$, $AC = 4$. Tính $BC$." "\n"
        r"  \dapso[B]{$5$}" "\n"
        r"}{" "\n"
        r"  \begin{tikzpicture}" "\n"
        r"    \tkzDefPoints{0/0/A, 3/0/B, 0/4/C}" "\n"
        r"    \tkzDrawPolygon(A,B,C)" "\n"
        r"    \tkzLabelPoint[below left](A){$A$}" "\n"
        r"    \tkzLabelPoint[below right](B){$B$}" "\n"
        r"    \tkzLabelPoint[above left](C){$C$}" "\n"
        r"    \tkzMarkRightAngle(B,A,C)" "\n"
        r"  \end{tikzpicture}" "\n"
        r"}" "\n"
        r"\choice" "\n"
        r"{$3$}" "\n"
        r"{\True $5$}" "\n"
        r"{$7$}" "\n"
        r"{$12$}" "\n"
        r"\loigiai{" "\n"
        r"  Theo định lí Pythagoras: $BC = \sqrt{AB^2 + AC^2} = \sqrt{9 + 16} = 5$." "\n"
        r"}" "\n"
        r"\end{ex}"
    )
    student = student_source(source, hide_answers=True)
    assert r"\True" not in student
    assert r"\dapso" not in student
    assert r"\loigiai" not in student
    assert "Pythagoras" not in student
    assert r"\immini" in student
    assert r"\tkzDrawPolygon" in student
    assert r"\tkzMarkRightAngle" in student
    assert "Cho tam giác $ABC$" in student


def test_physics_macros_siunitx_preserved():
    r"""Kiểm tra các macro vật lý (\SI, \ang, \SIrange, \unit) được giữ nguyên định dạng, không cắt nhầm."""
    source = (
        r"\begin{ex}" "\n"
        r"Một vật chuyển động với tốc độ ban đầu $v_0 = \SI{10}{\meter\per\second}$ " "\n"
        r"và góc ném $\alpha = \ang{45}$ trong phạm vi nhiệt độ $\SIrange{20}{30}{\celsius}$." "\n"
        r"\choice" "\n"
        r"{\True $\SI{10}{\meter\per\second}$}" "\n"
        r"{$\SI{20}{\meter\per\second}$}" "\n"
        r"{$\SI{30}{\meter\per\second}$}" "\n"
        r"{$\SI{40}{\meter\per\second}$}" "\n"
        r"\loigiai{Lời giải chi tiết với đơn vị $\SI{10}{\meter\per\second}$.}" "\n"
        r"\end{ex}"
    )
    student = student_source(source, hide_answers=True)
    assert r"\True" not in student
    assert r"\loigiai" not in student
    assert "Lời giải chi tiết" not in student
    assert r"\SI{10}{\meter\per\second}" in student
    assert r"\ang{45}" in student
    assert r"\SIrange{20}{30}{\celsius}" in student


def test_fail_closed_unapproved_macro():
    """Kiểm tra cơ chế fail-closed: Macro lạ hoặc chưa kiểm định sẽ bị chặn thay vì rò rỉ đáp án."""
    unapproved_source = (
        r"\begin{ex}" "\n"
        r"Câu hỏi trắc nghiệm." "\n"
        r"\unapprovedCustomMacro{DapAnA}" "\n"
        r"\end{ex}"
    )
    with pytest.raises(ValueError, match="Macro chưa được chứng nhận cho source học sinh"):
        student_source(unapproved_source, hide_answers=True)


def test_student_source_real_pdflatex_compilation(tmp_path):
    r"""Biên dịch thực tế đề học sinh chứa \immini, tkz-euclide, và \SI qua pdfLaTeX."""
    source = (
        r"\begin{ex}" "\n"
        r"\immini{" "\n"
        r"  Một vật có vận tốc $v = \SI{10}{\meter\per\second}$ chuyển động trên đoạn thẳng $AB$." "\n"
        r"  \dapso[A]{$10$}" "\n"
        r"}{" "\n"
        r"  \begin{tikzpicture}" "\n"
        r"    \tkzDefPoints{0/0/A, 2/0/B}" "\n"
        r"    \tkzDrawSegment(A,B)" "\n"
        r"    \tkzLabelPoint[below](A){$A$}" "\n"
        r"    \tkzLabelPoint[below](B){$B$}" "\n"
        r"  \end{tikzpicture}" "\n"
        r"}" "\n"
        r"\choice" "\n"
        r"{\True $\SI{10}{\meter\per\second}$}" "\n"
        r"{$\SI{20}{\meter\per\second}$}" "\n"
        r"{$\SI{30}{\meter\per\second}$}" "\n"
        r"{$\SI{40}{\meter\per\second}$}" "\n"
        r"\loigiai{Vận tốc là $\SI{10}{\meter\per\second}$.}" "\n"
        r"\end{ex}"
    )
    student = student_source(source, hide_answers=True)
    assert r"\True" not in student
    assert r"\dapso" not in student
    assert r"\loigiai" not in student

    compiler = Compiler(tmp_path)
    # Extra preamble to include tkz-euclide and siunitx if not already loaded
    compiler.preamble_extra = (
        r"\usepackage{tkz-euclide}" "\n"
        r"\usepackage{siunitx}" "\n"
        r"\sisetup{locale=FR}" "\n"
    )
    res = compiler.compile(student, {})
    assert res.ok, f"Compile PDF đề học sinh thất bại: {res.log}"
    assert res.pdf is not None and res.pdf.exists()
    assert res.pdf.stat().st_size > 1000
