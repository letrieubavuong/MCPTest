r"""Tests for Phase K1: Enhanced Question Parser and Classification.

Validates that:
- MCQ (\choice) inside top-level and inside wrappers like \immini are parsed.
- True/False (\choiceTF, \choiceTFt) inside top-level and \immini are parsed.
- Short answer (\shortans, \dapsoTL, \dapso) are parsed.
- Essay (questions without choices/short answers) are parsed.
- Macros inside solutions (\loigiai, \hdan) do NOT corrupt question type.
- Nested braces, comments, TikZ code, and UTF-8 Vietnamese are handled cleanly.
"""
import pytest
from latex_question_studio.parsing.latex import parse_questions


def test_parser_mcq_standard():
    src = r"""\begin{ex}
Trong không gian $Oxyz$, cho mặt cầu $(S): x^2+y^2+z^2-2x+4y-6z-11=0$. Bán kính của $(S)$ bằng
\choice
{\True $5$}
{$6$}
{$7$}
{$8$}
\loigiai{Tâm $I(1;-2;3)$, bán kính $R=\sqrt{1+4+9+11}=5$.}
\end{ex}"""
    items = parse_questions(src)
    assert len(items) == 1
    q = items[0]
    assert q.question_type == "mcq"
    assert len(q.answer["options"]) == 4
    assert q.answer["options"][0]["correct"] is True
    assert q.answer["options"][1]["correct"] is False
    assert not q.diagnostics


def test_parser_mcq_inside_immini_with_comments():
    src = r"""\begin{ex}
Cho hàm số $y=f(x)$ có đồ thị như hình vẽ.
\immini{
Hàm số đã cho đồng biến trên khoảng nào dưới đây?
\choice
{$(-\infty; -1)$}
{\True $(-1; 1)$} % Đáp án đúng
{$(1; +\infty)$}
{$(0; 2)$}
}{
\begin{tikzpicture}
\draw[->] (-2,0) -- (2,0);
\end{tikzpicture}
}
\loigiai{
Đồ thị đi lên trên $(-1; 1)$.
\choice % fake choice inside loigiai should not affect outer question
{$A$} {$B$} {$C$} {$D$}
}
\end{ex}"""
    items = parse_questions(src)
    assert len(items) == 1
    q = items[0]
    assert q.question_type == "mcq"
    assert q.answer["options"][1]["correct"] is True
    assert not q.diagnostics


def test_parser_true_false_choiceTF():
    src = r"""\begin{ex}
Cho hàm số $y = \frac{ax+b}{cx+d}$. Xét tính đúng sai của các mệnh đề sau:
\choiceTF
{\True Hàm số có tiệm cận đứng $x = -d/c$}
{Hàm số luôn đồng biến trên $\mathbb{R}$}
{\True Đồ thị cắt trục tung tại điểm $(0; b/d)$}
{Tâm đối xứng là gốc tọa độ $O$}
\loigiai{Lời giải chi tiết.}
\end{ex}"""
    items = parse_questions(src)
    assert len(items) == 1
    q = items[0]
    assert q.question_type == "true_false"
    assert len(q.answer["options"]) == 4
    assert [opt["correct"] for opt in q.answer["options"]] == [True, False, True, False]
    assert not q.diagnostics


def test_parser_true_false_choiceTFt_inside_immini():
    src = r"""\begin{ex}
\immini{
Cho hình lăng trụ đứng $ABC.A'B'C'$. Các mệnh đề sau đúng hay sai?
\choiceTFt
{\True $AA' \perp (ABC)$}
{$BB' \parallel (A'B'C')$}
{\True Thể tích khối lăng trụ là $V = B \cdot h$}
{\True $AB \perp A'C'$}
}{
\begin{tikzpicture}
\node {Hình vẽ};
\end{tikzpicture}
}
\end{ex}"""
    items = parse_questions(src)
    assert len(items) == 1
    q = items[0]
    assert q.question_type == "true_false"
    assert [opt["correct"] for opt in q.answer["options"]] == [True, False, True, True]
    assert not q.diagnostics


def test_parser_short_answer_shortans():
    src = r"""\begin{ex}
Tìm giá trị lớn nhất của hàm số $f(x) = -x^2 + 4x + 1$.
\shortans{5}
\loigiai{Ta có $f(x) = -(x-2)^2 + 5 \le 5$.}
\end{ex}"""
    items = parse_questions(src)
    assert len(items) == 1
    q = items[0]
    assert q.question_type == "short_answer"
    assert q.answer["value"].strip() == "5"
    assert not q.diagnostics


def test_parser_short_answer_shortans_bracket_syntax():
    src = r"""\begin{ex}
Nghiệm nguyên dương nhỏ nhất của phương trình $\log_2(x-1) = 3$ là bao nhiêu?
\shortans[0.5]{9}
\end{ex}"""
    items = parse_questions(src)
    assert len(items) == 1
    q = items[0]
    assert q.question_type == "short_answer"
    assert q.answer["value"].strip() == "9"
    assert not q.diagnostics


def test_parser_short_answer_dapsoTL():
    src = r"""\begin{ex}
Một vật chuyển động với phương trình $s(t) = t^3 - 3t^2 + 5t$. Vận tốc tức thời tại $t = 2$ bằng
\dapsoTL{5}
\end{ex}"""
    items = parse_questions(src)
    assert len(items) == 1
    q = items[0]
    assert q.question_type == "short_answer"
    assert q.answer["value"].strip() == "5"
    assert not q.diagnostics


def test_parser_essay():
    src = r"""\begin{ex}
Giải hệ phương trình sau trên tập số thực $\mathbb{R}$:
\[
\begin{cases}
x^2 + y^2 = 5 \\
x + y = 3
\end{cases}
\]
\loigiai{
Từ phương trình thứ hai ta có $y = 3 - x$.
Thay vào phương trình thứ nhất:
$x^2 + (3-x)^2 = 5 \iff 2x^2 - 6x + 4 = 0 \iff x = 1$ hoặc $x = 2$.
Vậy nghiệm của hệ là $(1; 2)$ và $(2; 1)$.
}
\end{ex}"""
    items = parse_questions(src)
    assert len(items) == 1
    q = items[0]
    assert q.question_type == "essay"
    assert q.answer == {"essay": True}
    assert not q.diagnostics


def test_parser_solution_macro_exclusion():
    # If a question has no choices in statement, but loigiai contains \choice or \shortans,
    # it must remain an essay question.
    src = r"""\begin{ex}
Chứng minh rằng đồ thị hàm số luôn đi qua điểm cố định $M(1; 2)$.
\loigiai{
Ta có thể dùng phương pháp loại trừ như câu trắc nghiệm:
\choice
{Đáp án 1}
{Đáp án 2}
{Đáp án 3}
{Đáp án 4}
\shortans{123}
}
\end{ex}"""
    items = parse_questions(src)
    assert len(items) == 1
    assert items[0].question_type == "essay"
    assert items[0].answer == {"essay": True}
    assert not items[0].diagnostics


def test_parser_multiple_questions_mixed():
    src = r"""
\begin{ex}
Câu 1 trắc nghiệm
\choice
{$A$}
{\True $B$}
{$C$}
{$D$}
\end{ex}

\begin{ex}
Câu 2 đúng sai
\choiceTF
{\True $a$}
{$b$}
{$c$}
{\True $d$}
\end{ex}

\begin{ex}
Câu 3 điền số
\shortans{42}
\end{ex}

\begin{ex}
Câu 4 tự luận
Chứng minh đẳng thức.
\end{ex}
"""
    items = parse_questions(src)
    assert len(items) == 4
    assert items[0].question_type == "mcq"
    assert items[1].question_type == "true_false"
    assert items[2].question_type == "short_answer"
    assert items[3].question_type == "essay"
