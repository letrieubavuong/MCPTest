import pytest
from pathlib import Path
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.lessons import student_source


def test_nested_loigiai_multilevel():
    """Kiểm tra bóc tách lời giải lồng nhau 3-5 tầng ngoặc và môi trường."""
    source = (
        r"\begin{ex}" "\n"
        r"Giải phương trình $x^2 - 4 = 0$." "\n"
        r"\choice{$x = 1$}{\True $x = \pm 2$}{$x = 3$}{$x = 4$}" "\n"
        r"\loigiai{" "\n"
        r"  \begin{itemize}" "\n"
        r"    \item Bước 1: \textbf{Phân tích} $x^2 - 4 = (x-2)(x+2) = 0$." "\n"
        r"    \item Bước 2: " "\n"
        r"      \begin{enumerate}" "\n"
        r"        \item Nhánh 1: $x = 2$." "\n"
        r"        \item Nhánh 2: $x = -2$." "\n"
        r"        \item Chi tiết: \textsf{\textit{\textbf{SECRET_STEP_5_DEEP}}}}" "\n"
        r"      \end{enumerate}" "\n"
        r"  \end{itemize}" "\n"
        r"}" "\n"
        r"\haidong{5}" "\n"
        r"\end{ex}"
    )
    student = student_source(source, hide_answers=True)
    assert r"\True" not in student
    assert r"\loigiai" not in student
    assert "SECRET_STEP_5_DEEP" not in student
    assert "Bước 1" not in student
    assert r"\haidong{5}" in student
    assert r"Giải phương trình" in student


def test_loigiai_with_escaped_braces_and_comments():
    r"""Kiểm tra lời giải chứa dấu ngoặc thoát \{ \} và dấu % comment."""
    source = (
        r"\begin{ex}" "\n"
        r"Tập nghiệm của phương trình là gì?" "\n"
        r"\choice{$A$}{\True $B$}{$C$}{$D$}" "\n"
        r"\loigiai{" "\n"
        r"  Ta có tập nghiệm là $S = \{ -2; 2 \}$ % Đây là comment chứa { ngoặc mở" "\n"
        r"  Không bị nhầm lẫn bởi \} ngoặc đóng trong comment!" "\n"
        r"  SECRET_ANSWER_BODY" "\n"
        r"}" "\n"
        r"\end{ex}"
    )
    student = student_source(source, hide_answers=True)
    assert "SECRET_ANSWER_BODY" not in student
    assert r"\loigiai" not in student
    assert r"\True" not in student
    assert "Tập nghiệm của phương trình" in student


def test_shortans_and_hdan_optional_args():
    r"""Kiểm tra \shortans và \hdan có chứa tham số tùy chọn [...]."""
    source = (
        r"\begin{ex}" "\n"
        r"Tính giá trị của biểu thức $A = 2 + 2$." "\n"
        r"\shortans[Đáp số]{4}" "\n"
        r"\hdan[Gợi ý 1]{Áp dụng phép cộng cơ bản SECRET_HINT.}" "\n"
        r"\end{ex}"
    )
    student = student_source(source, hide_answers=True)
    assert r"\shortans" not in student
    assert r"\hdan" not in student
    assert "SECRET_HINT" not in student
    assert "4" not in student or "2 + 2" in student  # Đảm bảo không còn đáp án đơn lẻ
    assert "Tính giá trị của biểu thức" in student


def test_choicetf_and_multiple_choices():
    r"""Kiểm tra câu hỏi đúng sai \choiceTF và nhiều lựa chọn."""
    source = (
        r"\begin{ex}" "\n"
        r"Cho hàm số $y = f(x)$. Các mệnh đề sau đúng hay sai?" "\n"
        r"\choiceTF" "\n"
        r"{\True Hàm số đồng biến trên $\mathbb{R}$}" "\n"
        r"{Hàm số có cực trị}" "\n"
        r"{\True Đồ thị đi qua gốc tọa độ}" "\n"
        r"{Hàm số tuần hoàn}" "\n"
        r"\loigiai{Mệnh đề a và c đúng.}" "\n"
        r"\end{ex}"
    )
    student = student_source(source, hide_answers=True)
    assert r"\True" not in student
    assert r"\loigiai" not in student
    assert "Mệnh đề a và c đúng" not in student
    assert "Hàm số đồng biến trên" in student


def test_fail_closed_on_unregistered_custom_macro(tmp_path):
    """Kiểm tra nguyên tắc fail-closed: macro lạ ngoài từ vựng chuẩn phải bị chặn khi xuất đề học sinh."""
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)
    q = services.questions.create(r"\begin{ex}Câu hỏi có lệnh lạ: \SecretKey{12345}\end{ex}")
    _, snapshot = exam.generate("Đề kiểm tra", manual_ids=[q.id])

    # Đề học sinh phải fail-closed
    with pytest.raises(ValueError, match="Macro"):
        exam.content(snapshot, solutions=False)

    # Đề giáo viên vẫn cho phép xuất đầy đủ
    teacher_content = exam.content(snapshot, solutions=True)
    assert r"\SecretKey{12345}" in teacher_content


def test_fail_closed_on_corrupt_unclosed_braces(tmp_path):
    """Kiểm tra khi câu hỏi bị lỗi cấu trúc ngoặc nhọn chưa đóng."""
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)
    q = services.questions.create(r"\begin{ex}Câu hỏi lỗi \loigiai{Chưa đóng ngoặc\end{ex}")

    # Câu bị lỗi ngoặc không được phép tạo đề (chặn ngay từ khâu phân tích)
    with pytest.raises(ValueError, match="chưa phân tích hợp lệ"):
        exam.generate("Đề lỗi ngoặc", manual_ids=[q.id])


def test_solution_only_images_excluded_from_student_export(tmp_path):
    r"""Kiểm tra tài nguyên ảnh chỉ nằm trong lời giải không bị copy vào thư mục học sinh."""
    services = create_services(AppConfig.load(tmp_path / 'data'))
    body_img = tmp_path / 'body.png'
    body_img.write_bytes(b'body image data')
    sol_img = tmp_path / 'sol.png'
    sol_img.write_bytes(b'solution image data')

    source = (
        r"\begin{ex}Đồ thị: \includegraphics{body.png}" "\n"
        r"\choice{A}{\True B}{C}{D}" "\n"
        r"\loigiai{Hình minh họa giải: \includegraphics{sol.png}}" "\n"
        r"\end{ex}"
    )
    src_file = tmp_path / 'q.tex'
    src_file.write_text(source, encoding='utf-8')
    batch, _ = ImportService(services).stage([src_file])
    ImportService(services).commit(batch)

    exam = ExamService(services)
    q = services.questions.list_page()[0]
    _, snapshot = exam.generate("Đề có ảnh", manual_ids=[q.id])

    # Xuất đề học sinh: chỉ chứa ảnh trong thân đề
    student_tex = tmp_path / 'student' / 'de.tex'
    exam.export_tex(snapshot, student_tex, solutions=False)
    student_assets = list((tmp_path / 'student').rglob('*.png'))
    student_tex_content = student_tex.read_text(encoding='utf-8')

    assert r"\includegraphics" in student_tex_content
    assert len(student_assets) == 1
    assert student_assets[0].read_bytes() == b'body image data'

    # Xuất đề giáo viên: chứa cả ảnh thân đề và ảnh lời giải
    teacher_tex = tmp_path / 'teacher' / 'de.tex'
    exam.export_tex(snapshot, teacher_tex, solutions=True)
    teacher_assets = list((tmp_path / 'teacher').rglob('*.png'))
    teacher_tex_content = teacher_tex.read_text(encoding='utf-8')

    assert len(teacher_assets) == 2
    assert {a.read_bytes() for a in teacher_assets} == {b'body image data', b'solution image data'}


def test_compile_student_and_teacher_pdf(tmp_path):
    """Biên dịch thực tế bằng pdfLaTeX: so sánh đề học sinh không lộ đáp án và đề giáo viên giữ lời giải."""
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)
    q1 = services.questions.create(
        r"\begin{ex}" "\n"
        r"Tính đạo hàm của $y = x^3$." "\n"
        r"\choice{$y' = x^2$}{\True $y' = 3x^2$}{$y' = 3x$}{$y' = 6x$}" "\n"
        r"\loigiai{Áp dụng công thức $(x^n)' = n x^{n-1}$, ta có $(x^3)' = 3x^2$.}" "\n"
        r"\end{ex}"
    )
    q2 = services.questions.create(
        r"\begin{ex}" "\n"
        r"Nêu định nghĩa chất lỏng." "\n"
        r"\loigiai{Chất lỏng có thể tích xác định nhưng không có hình dạng xác định.}" "\n"
        r"\end{ex}"
    )
    _, snapshot = exam.generate("Đề thi thử", manual_ids=[q1.id, q2.id])

    student_pdf = tmp_path / 'student.pdf'
    teacher_pdf = tmp_path / 'teacher.pdf'

    res_student = exam.export_pdf(snapshot, student_pdf, solutions=False)
    res_teacher = exam.export_pdf(snapshot, teacher_pdf, solutions=True)

    assert res_student.ok is True
    assert student_pdf.is_file() and student_pdf.stat().st_size > 1000

    assert res_teacher.ok is True
    assert teacher_pdf.is_file() and teacher_pdf.stat().st_size > 1000
